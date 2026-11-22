#include <charconv>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#endif

namespace fs = std::filesystem;

namespace {
bool valid_utf8(const std::string& input) {
    for (std::size_t i = 0; i < input.size();) {
        const auto first = static_cast<unsigned char>(input[i++]);
        if (first < 0x80) continue;
        if (first < 0xc2 || first > 0xf4) return false;
        const std::size_t remaining = first < 0xe0 ? 1 : (first < 0xf0 ? 2 : 3);
        if (input.size() - i < remaining) return false;
        const auto second = static_cast<unsigned char>(input[i]);
        if ((first == 0xe0 && second < 0xa0) || (first == 0xed && second >= 0xa0) ||
            (first == 0xf0 && second < 0x90) || (first == 0xf4 && second >= 0x90)) return false;
        for (std::size_t k = 0; k < remaining; ++k)
            if ((static_cast<unsigned char>(input[i++]) & 0xc0U) != 0x80U) return false;
    }
    return true;
}

std::string read_text(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot read " + path.u8string());
    std::ostringstream data;
    data << file.rdbuf();
    if (file.bad()) throw std::runtime_error("read failed: " + path.u8string());
    auto out = data.str();
    if (!valid_utf8(out)) throw std::runtime_error("invalid UTF-8 in " + path.u8string());
    std::size_t dest = 0;
    for (std::size_t pos = 0; pos < out.size(); ++pos) {
        if (out[pos] == '\r') {
            if (pos+1 < out.size() && out[pos+1] == '\n') ++pos;
            out[dest++] = '\n';
        } else out[dest++] = out[pos];
    }
    out.resize(dest);
    return out;
}

void install_page(const fs::path& path, const std::string& data, const std::string& original) {
    auto temporary = path;
    temporary += ".nav-" + std::to_string(std::random_device{}()) + ".tmp";
#ifdef _WIN32
    FILE* file = nullptr;
    _wfopen_s(&file, temporary.c_str(), L"wx");
#else
    FILE* file = std::fopen(temporary.c_str(), "wx");
#endif
    if (!file) throw std::runtime_error("cannot create temporary page");
    try {
        const bool written = std::fwrite(data.data(), 1, data.size(), file) == data.size();
        const bool closed = std::fclose(file) == 0;
        if (!written || !closed) throw std::runtime_error("cannot finish temporary page");
        fs::permissions(temporary, fs::status(path).permissions());
        if (read_text(path) != original) throw std::runtime_error("page changed during rendering");
#ifdef _WIN32
        if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
            throw std::runtime_error("cannot replace page");
#else
        fs::rename(temporary, path);
#endif
    } catch (...) {
        std::error_code ec;
        fs::remove(temporary, ec);
        throw;
    }
}

struct Policy {
    std::string script, superseded;
    std::map<std::string, std::string> styles{{"none", ""}}, pages;
    explicit Policy(const fs::path& root) {
        const auto dir = root / "scripts/nav_scrollspy";
        script = read_text(dir / "script.html");
        std::istringstream lines(read_text(dir / "policy.tsv"));
        for (std::string line; std::getline(lines, line);) {
            const auto tab = line.find('\t');
            if (tab == line.npos) throw std::runtime_error("invalid scrollspy policy");
            const auto key = line.substr(0, tab), value = line.substr(tab+1);
            if (key == "page") {
                const auto split = value.find('\t');
                if (split == value.npos || !pages.emplace(value.substr(0,split),value.substr(split+1)).second)
                    throw std::runtime_error("invalid page inventory");
            } else if (key == "superseded") superseded = value;
            else if (key == "paper" || key == "dark") styles.emplace(key, value+"\n");
            else throw std::runtime_error("unknown policy entry");
        }
        if (superseded.empty() || script.empty() || pages.empty()) throw std::runtime_error("incomplete scrollspy policy");
    }
};

void strip(std::string& page) {
    for (const std::string tag : {"script", "style"}) {
        const auto open = "<"+tag+" data-nav-scrollspy>", close = "</"+tag+">";
        for (auto start = page.find(open); start != page.npos; start = page.find(open)) {
            auto end = page.find(close, start);
            if (end == page.npos) throw std::runtime_error("unterminated scrollspy block");
            end += close.size();
            while (end < page.size() && page[end]=='\n') ++end;
            page.erase(start, end-start);
        }
    }
}

void insert_before(std::string& page, const std::string& anchor, const std::string& value, const std::string& name) {
    const auto pos = page.find(anchor);
    if (pos == page.npos) throw std::runtime_error(name + ": missing " + anchor);
    page.insert(pos, value);
}

void render(std::string& page, const Policy& policy, const std::string& css, const std::string& name) {
    strip(page);
    for (auto at = page.find(policy.superseded); at != page.npos; at = page.find(policy.superseded, at))
        page.erase(at, policy.superseded.size());
    if (page.find("</body>") == page.npos) throw std::runtime_error(name + ": no </body> to anchor the script");
    if (!css.empty()) {
        if (page.find("</head>") == page.npos) throw std::runtime_error(name + ": no </head> to anchor the style");
        insert_before(page, "</head>", css, name);
    }
    insert_before(page, "</body>", policy.script, name);
}
}

int main(int argc, char** argv) {
    try {
        fs::path root = fs::current_path();
        const std::string mode = argc > 1 ? argv[1] : "--apply";
        if (mode == "--strip" || mode == "--render" || mode == "--patch-file") {
#ifdef _WIN32
            _setmode(_fileno(stdin), _O_BINARY);
            _setmode(_fileno(stdout), _O_BINARY);
#endif
            std::string css;
            if (mode != "--strip") {
                if (argc != (mode == "--render" ? 4 : 3)) throw std::runtime_error("invalid transform arguments");
                const std::string length = argv[2];
                std::size_t size = 0;
                const auto end = length.data()+length.size();
                const auto result = std::from_chars(length.data(),end,size);
                if (result.ec != std::errc{} || result.ptr != end) throw std::runtime_error("invalid CSS length");
                css.resize(size);
                if (!std::cin.read(css.data(),static_cast<std::streamsize>(size))) throw std::runtime_error("truncated CSS");
            }
            std::ostringstream input;
            input << std::cin.rdbuf();
            auto page = input.str();
            if (mode == "--patch-file") {
                const auto path = fs::u8path(page);
                const auto original = read_text(path);
                auto updated = original;
                render(updated, Policy(root), css, path.filename().u8string());
                if (updated != original) install_page(path,updated,original);
                std::cout << (updated == original ? "ok" : "patched");
                return 0;
            }
            if (mode == "--strip") strip(page);
            else render(page, Policy(root), css, argv[3]);
            std::cout << page;
            return std::cout ? 0 : 2;
        }
        if (argc > 2 || (mode != "--apply" && mode != "--check"))
            throw std::runtime_error("usage: nav_scrollspy [--check|--apply]");
        Policy policy(root);
        int stale = 0;
        for (const auto& [name,style] : policy.pages) {
            const auto path = root / "content/daily" / name;
            std::string state = "missing";
            if (fs::exists(path)) {
                const auto original = read_text(path);
                auto updated = original;
                render(updated,policy,policy.styles.at(style),name);
                if (updated == original) state = "ok";
                else if (mode == "--check") { state = "STALE"; ++stale; }
                else { install_page(path,updated,original); state = "patched"; }
            }
            std::cout << std::left << std::setw(26) << name << ' ' << state << '\n';
        }
        if (stale) std::cout << '\n' << stale << " page(s) need `npm run nav:apply`\n";
        return stale ? 1 : 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 2;
    }
}
