#include "workspace_inventory.hpp"
#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs = std::filesystem;

Strings untracked_paths() {
    constexpr char command[] = "git ls-files --others --exclude-standard -z";
#ifdef _WIN32
    FILE* git = _popen(command, "rb");
#else
    FILE* git = popen(command, "r");
#endif
    if (!git) throw std::runtime_error("cannot start git ls-files");
    std::array<char, 65536> buffer;
    std::string bytes;
    while (auto n = std::fread(buffer.data(), 1, buffer.size(), git)) bytes.append(buffer.data(), n);
    bool read_error = std::ferror(git) != 0;
#ifdef _WIN32
    int status = _pclose(git);
#else
    int status = pclose(git);
#endif
    if (read_error || status || (!bytes.empty() && bytes.back() != '\0'))
        throw std::runtime_error("incomplete git ls-files result");
    Strings paths;
    for (size_t i = 0; i < bytes.size();) {
        size_t end = bytes.find('\0', i);
        if (i != end) paths.emplace_back(bytes.substr(i, end-i));
        i = end + 1;
    }
    return paths;
}

void string_json(const std::string& value) {
    constexpr char hex[] = "0123456789abcdef";
    std::cout << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') std::cout << '\\' << char(c);
        else if (c < 0x20) std::cout << "\\u00" << hex[c >> 4] << hex[c & 15];
        else std::cout << char(c);
    }
    std::cout << '"';
}
void array_json(const Strings& values) {
    std::cout << '[';
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) std::cout << ',';
        string_json(values[i]);
    }
    std::cout << ']';
}

int main(int argc, char** argv) {
    bool json = false, check = false;
    std::uintmax_t limit_mib = 1024;
    constexpr std::uintmax_t mib = 1024 * 1024;
    try {
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--json") json = true;
            else if (arg == "--check") check = true;
            else if ((arg == "--max-local-mib" && i+1 < argc) || arg.rfind("--max-local-mib=",0)==0) {
                std::string value = arg == "--max-local-mib" ? argv[++i] : arg.substr(arg.find('=')+1);
                if (!value.empty() && value.front()=='+') value.erase(0,1);
                auto end = value.data() + value.size();
                auto parsed = std::from_chars(value.data(), end, limit_mib);
                if (parsed.ec != std::errc{} || parsed.ptr != end ||
                    limit_mib > std::numeric_limits<std::uintmax_t>::max() / mib)
                    throw std::invalid_argument("--max-local-mib requires a nonnegative integer MiB limit");
            } else if (arg == "--help" || arg == "-h") {
                std::cout << "workspace_inventory [--json] [--check] [--max-local-mib N]\n";
                return 0;
            } else throw std::invalid_argument("unknown or incomplete option: " + arg);
        }
        auto paths = untracked_paths();
        Strings errors;
        auto groups = group_paths(fs::current_path(),paths,errors);
        Scan local = scan_runs(fs::current_path()/".local"/"runs");
        bool ok = paths.empty() && errors.empty() && local.errors.empty() &&
                  local.links.empty() && local.bytes <= limit_mib * mib;
        if (json) {
            std::cout << "{\"untracked_entries\":" << paths.size() << ",\"untracked\":";
            array_json(paths);
            std::cout << ",\"groups\":[";
            bool first = true;
            for (const auto& [name, group] : groups) {
                if (!first) std::cout << ',';
                first = false;
                std::cout << "{\"path\":";
                string_json(name);
                std::cout << ",\"entries\":" << group.entries << ",\"bytes\":" << group.bytes << '}';
            }
            std::cout << "],\"local_runs\":{\"bytes\":" << local.bytes << ",\"files\":" << local.files << ",\"links\":";
            array_json(local.links);
            std::cout << ",\"errors\":";
            array_json(local.errors);
            std::cout << "},\"errors\":";
            array_json(errors);
            std::cout << ",\"local_limit_bytes\":" << limit_mib*mib << ",\"ok\":" << (ok?"true":"false") << "}\n";
        } else {
            std::cout << "未跟踪条目：" << paths.size() << "\n临时输出：" << local.files << " 个文件，"
                      << std::fixed << std::setprecision(2) << double(local.bytes)/mib << " MiB\n";
            for (const auto& [name,g] : groups)
                std::cout << "  " << name << ": " << g.entries << " 项，" << double(g.bytes)/mib << " MiB\n";
            if (!errors.empty() || !local.errors.empty() || !local.links.empty())
                std::cout << "存在读取错误或链接，请使用 --json 查看。\n";
        }
        return check && !ok ? 1 : 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 2;
    }
}
