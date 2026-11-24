#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>

namespace {
namespace fs = std::filesystem;
using Files = std::map<fs::path, std::uintmax_t>;

Files inventory(const fs::path& root) {
    Files files;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink()) throw std::runtime_error("unexpected link in build output");
        if (entry.is_regular_file()) files.emplace(entry.path().lexically_relative(root), entry.file_size());
    }
    return files;
}

bool equal_bytes(const fs::path& left, const fs::path& right) {
    std::ifstream a(left, std::ios::binary), b(right, std::ios::binary);
    if (!a || !b) throw std::runtime_error("could not read both files: " + left.generic_u8string());
    std::array<char, 65536> x{}, y{};
    while (a && b) {
        a.read(x.data(), x.size());
        b.read(y.data(), y.size());
        if (a.gcount() != b.gcount() || !std::equal(x.begin(), x.begin() + a.gcount(), y.begin())) return false;
    }
    if (a.bad() || b.bad()) throw std::runtime_error("error reading file: " + left.generic_u8string());
    return a.eof() && b.eof();
}

int compare(const fs::path& reference, const fs::path& candidate) {
    try {
        const auto baseline = inventory(reference);
        auto outputs = inventory(candidate);
        std::size_t missing = 0, changed = 0, identical = 0;
        unsigned long long total_bytes = 0;
        for (const auto& [file, size] : baseline) {
            const auto other = outputs.find(file);
            const auto name = file.generic_u8string();
            if (other == outputs.end()) {
                std::cout << "missing\t" << name << '\n';
                ++missing;
                continue;
            }
            if (other->second == size && equal_bytes(reference / file, candidate / file)) {
                ++identical;
                total_bytes += size;
            } else {
                std::cout << "different\t" << name << '\n';
                ++changed;
            }
            outputs.erase(other);
        }
        for (const auto& item : outputs) std::cout << "extra\t" << item.first.generic_u8string() << '\n';
        std::cout << "reference=" << baseline.size() << " identical=" << identical << " identical_bytes=" << total_bytes
                  << " different=" << changed << " missing=" << missing << " extra=" << outputs.size() << '\n';
        return missing || changed || !outputs.empty() ? 1 : 0;
    } catch (const std::exception& error) {
        std::cerr << "dashboard_compare: " << error.what() << '\n';
        return 2;
    }
}

template<class Char>
int run(int argc, Char** argv) {
    if (argc == 3) return compare(fs::path(argv[1]), fs::path(argv[2]));
    std::cerr << "Usage: dashboard_compare REFERENCE CANDIDATE\n";
    return 2;
}
}

#ifdef _WIN32
int wmain(int argc, wchar_t** argv) { return run(argc, argv); }
#else
int main(int argc, char** argv) { return run(argc, argv); }
#endif
