#include "dashboard_build.hpp"
#include "native_process.hpp"
#include "workspace_inventory.hpp"

#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <sys/stat.h>
#endif

namespace dashboard {
namespace {
bool below(const fs::path& path, const fs::path& parent) {
    const auto relative = path.lexically_relative(parent);
    return !relative.empty() && relative != "." && *relative.begin() != "..";
}

std::string signature(const fs::path& path) {
#ifdef _WIN32
    const auto file = CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                  nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (file == INVALID_HANDLE_VALUE) return {};
    BY_HANDLE_FILE_INFORMATION info{};
    FILE_BASIC_INFO basic{};
    const bool ok = GetFileInformationByHandle(file, &info) &&
                    GetFileInformationByHandleEx(file, FileBasicInfo, &basic, sizeof(basic));
    CloseHandle(file);
    if (!ok || (info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) return {};
    constexpr auto epoch = 116444736000000000LL;
    const auto file_id = (static_cast<std::uint64_t>(info.nFileIndexHigh) << 32) | info.nFileIndexLow;
    const auto size = (static_cast<std::uint64_t>(info.nFileSizeHigh) << 32) | info.nFileSizeLow;
    return std::to_string(info.dwVolumeSerialNumber) + ":" + std::to_string(file_id) + ":" +
           std::to_string(size) + ":" + std::to_string((basic.LastWriteTime.QuadPart - epoch) * 100) + ":" +
           std::to_string((basic.ChangeTime.QuadPart - epoch) * 100);
#else
    struct stat info{};
    if (lstat(path.c_str(), &info) != 0 || !S_ISREG(info.st_mode)) return {};
#ifdef __APPLE__
    const auto& updated = info.st_mtimespec;
    const auto& changed = info.st_ctimespec;
#else
    const auto& updated = info.st_mtim;
    const auto& changed = info.st_ctim;
#endif
    return std::to_string(info.st_dev) + ":" + std::to_string(info.st_ino) + ":" + std::to_string(info.st_size) +
           ":" + std::to_string(updated.tv_sec * 1000000000LL + updated.tv_nsec) +
           ":" + std::to_string(changed.tv_sec * 1000000000LL + changed.tv_nsec);
#endif
}

void copy_file(const fs::path& input, const fs::path& output, bool preserve_time, fs::path& last_directory) {
    if (const auto dir = output.parent_path(); dir != last_directory) {
        fs::create_directories(dir);
        last_directory = dir;
    }
    fs::copy_file(input, output, fs::copy_options::overwrite_existing);
#ifdef _WIN32
    // The Windows copy operation preserves the source write time.
    (void)preserve_time;
#else
    if (preserve_time) fs::last_write_time(output, fs::last_write_time(input));
#endif
}

void prune(const fs::path& dir, const fs::path& asset_dir,
           const std::map<fs::path, fs::path>& sources) {
    for (const auto& entry : fs::directory_iterator(dir)) {
        const auto relative = entry.path().lexically_relative(asset_dir);
        if (entry.is_directory()) {
            prune(entry.path(), asset_dir, sources);
            if (fs::is_empty(entry.path())) fs::remove(entry.path());
        } else if (!sources.count(relative)) fs::remove(entry.path());
    }
}
}

void safe_output(const BuildOptions& options) {
    const auto dist = options.root / "dist";
    const auto runs = options.root / ".local/runs";
    if (options.output != dist && !below(options.output, runs) && !below(options.output, options.root / ".local-build"))
        throw std::runtime_error("output must be dist or a subdirectory of .local/runs or .local-build");
    for (auto current = options.output; current != options.root; current = current.parent_path())
        if (fs::symlink_status(current).type() != fs::file_type::not_found && ::is_link(current))
            throw std::runtime_error("output ancestor is a link: " + path_text(current));
    for (const auto* input : {&options.asset_manifest, &options.daily_cache, &options.tags, &options.pagefind})
        if (*input == options.output || (!input->empty() && below(*input, options.output)))
            throw std::runtime_error("build input or cache is inside output: " + path_text(*input));
    if (fs::exists(options.output) && !fs::is_directory(options.output))
        throw std::runtime_error("output must be a directory: " + path_text(options.output));
    if (!fs::exists(options.output)) return;
    const auto scan = scan_runs(options.output);
    if (!scan.links.empty()) throw std::runtime_error("link in output: " + scan.links.front());
    if (!scan.errors.empty()) throw std::runtime_error("cannot verify output directory: " + scan.errors.front());

    for (const auto& item : fs::directory_iterator(options.output))
        if (options.asset_manifest.empty() || item.path().filename() != "assets") fs::remove_all(item.path());
}

void copy_assets(const BuildOptions& options) {
    const auto bytes = run_process("git", {"ls-files", "-z", "--cached", "--", "site", "content/assets"});
    if (!bytes.empty() && bytes.back() != '\0') throw std::runtime_error("incomplete git ls-files output");
    std::map<fs::path, fs::path> assets;
    fs::path last_directory;
    const auto files = split(bytes, '\0');
    for (const auto& name : files) {
        if (name.compare(0, 5, "site/") != 0 || name.size() == 5) continue;
        const auto relative = fs::u8path(name.substr(5));
        const auto input = options.root / fs::u8path(name);
        if (*relative.begin() == "assets") assets[relative.lexically_relative("assets")] = input;
        else if (fs::is_regular_file(input)) copy_file(input, options.output / relative, true, last_directory);
    }
    for (const auto& name : files)
        if (name.compare(0, 15, "content/assets/") == 0 && name.size() > 15)
            assets[fs::u8path(name.substr(15))] = options.root / fs::u8path(name);

    const auto dir = options.output / "assets";
    auto previous = Json::object();
    const bool incremental = !options.asset_manifest.empty();
    if (incremental) {
        try { previous = read_json(options.asset_manifest); }
        catch (const std::exception&) {}
        if (fs::exists(dir)) {
            if (!fs::is_directory(dir)) throw std::runtime_error("invalid output assets directory");
            prune(dir, dir, assets);
        }
    }

    auto manifest = Json::object();
    std::size_t reused = 0, copied = 0;
    for (const auto& [relative, input] : assets) {
        const auto destination = dir / relative;
        if (!incremental) {
            if (fs::is_regular_file(input)) copy_file(input, destination, true, last_directory);
            continue;
        }
        const auto name = path_text(relative);
        const auto before = signature(input);
        const auto old = json_or(previous, name, nullptr);
        if (!before.empty() && old.is_array() && old.size() == 2 && old[1] == before &&
            old[0].is_string() && !old[0].get_ref<const std::string&>().empty() &&
            old[0] == signature(destination)) {
            manifest[name] = old;
            ++reused;
            continue;
        }
        copy_file(input, destination, false, last_directory);
        ++copied;
        if (!before.empty() && signature(input) == before) manifest[name] = Json::array({signature(destination), before});
    }
    if (incremental) {
        write_atomic(options.asset_manifest, manifest.dump());
        std::cout << "Assets reused " << reused << ", copied " << copied << '\n';
    }
}
}
