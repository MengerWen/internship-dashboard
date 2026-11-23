#include <json.hpp>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace {
namespace fs = std::filesystem;
using Json = nlohmann::json;
using Arguments = std::vector<std::string>;

std::string utf8_path(const fs::path& path) {
    const auto value = path.u8string();
    return {value.begin(), value.end()};
}

#ifdef _WIN32
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

std::string git_output(const Arguments& args) {
    std::wstring command = L"git.exe";
    for (const auto& arg : args) command += L' ' + quoted(fs::u8path(arg).wstring());
    SECURITY_ATTRIBUTES attributes{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE reader = nullptr, writer = nullptr;
    if (!CreatePipe(&reader, &writer, &attributes, 0)) throw std::runtime_error("cannot open Git pipe");
    Handle read_end(reader), write_end(writer);
    if (!SetHandleInformation(read_end.get(), HANDLE_FLAG_INHERIT, 0))
        throw std::runtime_error("cannot configure Git pipe");
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = write_end.get();
    startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    PROCESS_INFORMATION child{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
            nullptr, nullptr, &startup, &child)) throw std::runtime_error("cannot start Git");
    Handle process(child.hProcess), thread(child.hThread);
    write_end.close();
    std::string output;
    char bytes[8192];
    DWORD count = 0;
    while (ReadFile(read_end.get(), bytes, sizeof(bytes), &count, nullptr) && count)
        output.append(bytes, count);
    if (GetLastError() != ERROR_BROKEN_PIPE) throw std::runtime_error("cannot read Git output");
    DWORD status = 1;
    if (WaitForSingleObject(process.get(), INFINITE) != WAIT_OBJECT_0
            || !GetExitCodeProcess(process.get(), &status) || status)
        throw std::runtime_error("Git check failed: " + args.at(2));
    return output;
}
#else
std::string git_output(const Arguments& args) {
    char program[] = "git";
    std::vector<char*> argv{program};
    for (const auto& arg : args) argv.push_back(const_cast<char*>(arg.c_str()));
    argv.push_back(nullptr);
    int pipes[2];
    if (pipe(pipes) != 0) throw std::runtime_error("cannot open Git pipe");
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
    if (status) { close(pipes[0]); throw std::runtime_error("cannot start Git"); }
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
        throw std::runtime_error("Git check failed: " + args.at(2));
    return output;
}
#endif

Json json_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open " + utf8_path(path));
    return Json::parse(input);
}

std::size_t git_line_count(std::string_view text) {
    // The audit counts Git blob lines, including a final line with no newline.
    constexpr std::string_view ascii_breaks = "\n\v\f\x1c\x1d\x1e";
    std::size_t lines = 0, width = 0;
    for (std::size_t i = 0; i < text.size(); i += width ? width : 1) {
        const auto rest = text.substr(i);
        if (rest.substr(0, 2) == "\r\n" || rest.substr(0, 2) == "\xc2\x85") width = 2;
        else if (rest.substr(0, 3) == "\xe2\x80\xa8" || rest.substr(0, 3) == "\xe2\x80\xa9") width = 3;
        else width = rest.front() == '\r' || ascii_breaks.find(rest.front()) != std::string_view::npos ? 1 : 0;
        lines += width != 0;
    }
    return lines + (!text.empty() && width == 0);
}

Json verify(const fs::path& root) {
    const auto manifest = json_file(root / "docs/journal-review/audit-2026-10-21/remediation-actions.json");
    const auto config = json_file(root / "scripts/journal_repos.json");
    std::map<std::string, Json> repos;
    Json revisions = Json::object();
    for (const auto& repo : config.at("repos")) {
        const auto name = repo.at("name").get<std::string>();
        repos[name] = repo;
        revisions[name] = repo.at("revision");
    }
    std::set<std::pair<std::string, std::string>> verified;
    std::map<std::string, std::size_t> file_lengths;
    Json checked = Json::array();
    for (const auto& [key, ref] : manifest.at("source_catalog").items()) {
        const auto repo = ref.at("repo").get<std::string>();
        const auto revision = ref.at("revision").get<std::string>();
        const auto& spec = repos.at(repo);
        const auto folder = utf8_path(fs::weakly_canonical(root / fs::u8path(spec.at("path").get<std::string>())));
        if (verified.emplace(repo, revision).second)
            git_output({"-C", folder, "merge-base", "--is-ancestor", revision, spec.at("revision").get<std::string>()});
        if (ref.at("kind") == "file") {
            const auto relative = ref.at("path").get<std::string>();
            const auto allowed = spec.value("only_under", std::string{});
            if (relative.compare(0, allowed.size(), allowed) != 0) throw std::runtime_error(key + ": 超出父仓白名单");
            const auto object = revision + ':' + relative;
            const auto [length, fresh] = file_lengths.try_emplace(repo + '\n' + object, 0);
            if (fresh) length->second = git_line_count(git_output({"-C", folder, "show", object}));
            const auto low = ref.at("lines").at(0).get<std::int64_t>();
            const auto high = ref.at("lines").at(1).get<std::int64_t>();
            if (low < 1 || high < low || static_cast<std::uint64_t>(high) > length->second)
                throw std::runtime_error(key + ": 行号超出文件范围");
        } else {
            git_output({"-C", folder, "cat-file", "-e", revision + "^{commit}"});
        }
        checked.push_back(key);
    }
    const auto utc = std::time(nullptr);
    std::tm time{};
#ifdef _WIN32
    if (gmtime_s(&time, &utc) != 0) throw std::runtime_error("cannot format audit time");
#else
    if (!gmtime_r(&utc, &time)) throw std::runtime_error("cannot format audit time");
#endif
    char timestamp[32];
    std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S+00:00", &time);
    return {{"checked_at_utc", timestamp}, {"passed", true}, {"source_count", checked.size()},
        {"source_ids", checked}, {"revisions", revisions},
        {"scope", "Git对象、祖先关系、文件行号、父仓白名单；不表示服务器现场运行验收。"}};
}

int audit(const std::vector<fs::path>& args) {
    try {
        if (args.size() != 2 && args.size() != 4) throw std::invalid_argument("journal_sources --root ROOT [--output FILE]");
        if (args[0] != "--root" || (args.size() == 4 && args[2] != "--output"))
            throw std::invalid_argument("journal_sources --root ROOT [--output FILE]");
        const auto result = verify(args[1]);
        if (args.size() == 4) {
            std::ofstream output(args[3], std::ios::binary);
            output.exceptions(std::ios::badbit | std::ios::failbit);
            output << result.dump(2) << '\n';
            output.close();
        }
        std::cout << "固定原始引用 " << result.at("source_count") << " 项：Git对象、行号及版本包含关系全部通过。\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
}

#ifdef _WIN32
int wmain(int argc, wchar_t** argv) { return audit({argv + 1, argv + argc}); }
#else
int main(int argc, char** argv) { return audit({argv + 1, argv + argc}); }
#endif
