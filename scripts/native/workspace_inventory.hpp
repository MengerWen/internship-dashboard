#pragma once
#include <cstdint>
#include <filesystem>
#include <map>
#include <string>
#include <vector>

using Strings = std::vector<std::string>;
struct Scan {
    std::uintmax_t files = 0, bytes = 0;
    Strings links, errors;
};
struct Group {
    std::uintmax_t entries = 0, bytes = 0;
};
bool is_link(const std::filesystem::path& path);
Scan scan_runs(const std::filesystem::path& root);
std::map<std::string, Group> group_paths(const std::filesystem::path& root, const Strings& paths, Strings& errors);
