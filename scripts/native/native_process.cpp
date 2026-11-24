#include "native_process.hpp"

#include <cerrno>
#include <filesystem>
#include <mutex>
#include <stdexcept>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace dashboard {
namespace fs = std::filesystem;
namespace {
// A process must not inherit the write end of another worker's output pipe.
std::mutex spawn_mutex;
}
#ifdef _WIN32
namespace {
class Handle {
public:
    explicit Handle(HANDLE value) : value_(value) {}
    Handle(const Handle&) = delete;
    ~Handle() { close(); }
    HANDLE get() const { return value_; }
    void close() {
        if (value_) CloseHandle(value_);
        value_ = nullptr;
    }
private:
    HANDLE value_;
};

std::wstring quoted(const std::wstring& value) {
    std::wstring result = L"\"";
    std::size_t slashes = 0;
    for (auto character : value) {
        if (character == L'\\') { ++slashes; continue; }
        result.append(character == L'\"' ? slashes * 2 + 1 : slashes, L'\\');
        result += character;
        slashes = 0;
    }
    result.append(slashes * 2, L'\\');
    return result + L'\"';
}
}

std::string run_process(const std::string& executable, const Strings& args) {
    std::wstring command = quoted(fs::u8path(executable).wstring());
    for (const auto& arg : args) command += L' ' + quoted(fs::u8path(arg).wstring());
    std::unique_lock<std::mutex> spawning(spawn_mutex);
    SECURITY_ATTRIBUTES attributes{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE reader = nullptr, writer = nullptr;
    if (!CreatePipe(&reader, &writer, &attributes, 0)) throw std::runtime_error("cannot open child process pipe");
    Handle read_end(reader), write_end(writer);
    if (!SetHandleInformation(read_end.get(), HANDLE_FLAG_INHERIT, 0))
        throw std::runtime_error("cannot configure child process pipe");
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = write_end.get();
    startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    PROCESS_INFORMATION child{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
            nullptr, nullptr, &startup, &child)) throw std::runtime_error("cannot start " + executable);
    Handle process(child.hProcess), thread(child.hThread);
    write_end.close();
    spawning.unlock();
    std::string output;
    char bytes[8192];
    DWORD count = 0;
    while (ReadFile(read_end.get(), bytes, sizeof(bytes), &count, nullptr) && count)
        output.append(bytes, count);
    if (GetLastError() != ERROR_BROKEN_PIPE) throw std::runtime_error("cannot read child process output");
    DWORD status = 1;
    if (WaitForSingleObject(process.get(), INFINITE) != WAIT_OBJECT_0
            || !GetExitCodeProcess(process.get(), &status) || status)
        throw std::runtime_error("child process failed: " + executable);
    return output;
}
#else
std::string run_process(const std::string& executable, const Strings& args) {
    const auto* program = executable.c_str();
    std::vector<char*> argv{const_cast<char*>(program)};
    for (const auto& arg : args) argv.push_back(const_cast<char*>(arg.c_str()));
    argv.push_back(nullptr);
    std::unique_lock<std::mutex> spawning(spawn_mutex);
    int pipes[2];
    if (pipe(pipes) != 0) throw std::runtime_error("cannot open child process pipe");
    posix_spawn_file_actions_t actions;
    int status = posix_spawn_file_actions_init(&actions);
    pid_t child = -1;
    if (!status) {
        status = posix_spawn_file_actions_addclose(&actions, pipes[0]);
        if (!status) status = posix_spawn_file_actions_adddup2(&actions, pipes[1], STDOUT_FILENO);
        if (!status) status = posix_spawn_file_actions_addclose(&actions, pipes[1]);
        if (!status) status = posix_spawnp(&child, program, &actions, nullptr, argv.data(), environ);
        posix_spawn_file_actions_destroy(&actions);
    }
    close(pipes[1]);
    spawning.unlock();
    if (status) { close(pipes[0]); throw std::runtime_error("cannot start " + executable); }
    std::string output;
    char bytes[8192];
    ssize_t count;
    do {
        count = read(pipes[0], bytes, sizeof(bytes));
        if (count > 0) output.append(bytes, static_cast<std::size_t>(count));
    } while (count > 0 || (count < 0 && errno == EINTR));
    close(pipes[0]);
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    if (count < 0 || waited < 0 || !WIFEXITED(status) || WEXITSTATUS(status))
        throw std::runtime_error("child process failed: " + executable);
    return output;
}
#endif
}
