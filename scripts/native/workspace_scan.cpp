#include "workspace_inventory.hpp"
#include <cerrno>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <sys/stat.h>
#endif

namespace fs = std::filesystem;

bool is_link(const fs::path& path) {
#ifdef _WIN32
    DWORD attributes = GetFileAttributesW(path.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES)
        throw fs::filesystem_error("attributes", path, std::error_code(GetLastError(), std::system_category()));
    return (attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
#else
    return fs::is_symlink(fs::symlink_status(path));
#endif
}

Scan scan_runs(const fs::path& root) {
    Scan result;
    if (fs::symlink_status(root).type() == fs::file_type::not_found) return result;
    if (is_link(root)) {
        result.links.push_back(root.u8string());
        return result;
    }
    std::vector<fs::path> pending{root};
    while (!pending.empty()) {
        fs::path directory = pending.back();
        pending.pop_back();
        try {
            for (const auto& entry : fs::directory_iterator(directory)) {
                const fs::path& path = entry.path();
                try {
                    if (is_link(path)) result.links.push_back(path.lexically_relative(root).u8string());
                    else if (entry.is_directory()) pending.push_back(path);
                    else {
                        ++result.files;
#ifdef _WIN32
                        result.bytes += entry.file_size();
#else
                        struct stat info{};
                        if (::lstat(path.c_str(), &info) != 0)
                            throw fs::filesystem_error("lstat", path, std::error_code(errno,std::generic_category()));
                        result.bytes += info.st_size;
#endif
                    }
                } catch (const fs::filesystem_error& e) { result.errors.push_back(e.what()); }
            }
        } catch (const fs::filesystem_error& e) { result.errors.push_back(e.what()); }
    }
    return result;
}

std::map<std::string, Group> group_paths(const fs::path& root, const Strings& paths, Strings& errors) {
    std::map<std::string, Group> groups;
    for (const auto& relative : paths) {
        auto name = relative.substr(0,relative.find_last_not_of('/')+1);
        size_t first = name.find('/');
        size_t second = first == std::string::npos ? first : name.find('/', first+1);
        auto& group = groups[name.substr(0,second)];
        ++group.entries;
        auto path = root/fs::u8path(relative);
        try {
            if (fs::is_regular_file(path) && !is_link(path)) group.bytes += fs::file_size(path);
        } catch (const fs::filesystem_error& e) { errors.push_back(e.what()); }
    }
    return groups;
}
