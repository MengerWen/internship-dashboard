#include "page_renderer.hpp"
#include "compiled_pages.hpp"
#include <array>
#include <cstddef>
#include <filesystem>
#include <stdexcept>
#include <string_view>
#ifdef _WIN32
#include <windows.h>
#endif

namespace dashboard {
namespace {
namespace fs = std::filesystem;

bool missing_path(const std::error_code& error) {
    return error == std::errc::no_such_file_or_directory || error == std::errc::not_a_directory;
}

fs::path resolve_source_path(const fs::path& path, unsigned links = 0) {
    std::error_code error;
    const auto canonical = fs::canonical(path, error);
    if (!error) return canonical;
    if (!missing_path(error) || !path.has_relative_path())
        throw fs::filesystem_error("cannot resolve daily source", path, error);
    const auto status = fs::symlink_status(path, error);
    if (error && !missing_path(error))
        throw fs::filesystem_error("cannot inspect daily source", path, error);
    if (fs::is_symlink(status)) {
        if (links == 40) throw std::runtime_error("daily source has too many symlinks");
        // 目标尚不存在时仍应检查链接实际指向的目录。
        return resolve_source_path(path.parent_path() / fs::read_symlink(path), links + 1);
    }
    return (resolve_source_path(path.parent_path(), links) / path.filename()).lexically_normal();
}

bool same_component(const fs::path& first, const fs::path& second) {
#ifdef _WIN32
    return CompareStringOrdinal(first.c_str(), -1, second.c_str(), -1, TRUE) == CSTR_EQUAL;
#else
    return first == second;
#endif
}

std::string_view strip_python_whitespace(std::string_view text) {
    constexpr std::array<std::string_view, 29> whitespace{
        "\t", "\n", "\v", "\f", "\r", "\x1c", "\x1d", "\x1e", "\x1f", " ",
        "\u0085", "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003", "\u2004",
        "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u2028", "\u2029",
        "\u202f", "\u205f", "\u3000",
    };
    auto trim_edge = [&](bool leading) {
        while (!text.empty()) {
            bool found = false;
            for (auto space : whitespace) {
                if (space.size() > text.size()) continue;
                const auto offset = leading ? 0 : text.size() - space.size();
                if (text.substr(offset, space.size()) != space) continue;
                if (leading) text.remove_prefix(space.size());
                else text.remove_suffix(space.size());
                found = true;
                break;
            }
            if (!found) break;
        }
    };
    trim_edge(true);
    trim_edge(false);
    return text;
}

std::size_t line_break_width(std::string_view text) {
    if (text.substr(0, 2) == "\r\n" || text.substr(0, 2) == "\u0085") return 2;
    if (text.substr(0, 3) == "\u2028" || text.substr(0, 3) == "\u2029") return 3;
    return text.front() == '\xc2' || text.front() == '\xe2' ? 0 : 1;
}

std::string escape(const std::string& text) {
    std::string out;
    out.reserve(text.size());
    for (char c : text) {
        switch (c) {
        case '&': out += "&amp;"; break;
        case '<': out += "&lt;"; break;
        case '>': out += "&gt;"; break;
        case '"': out += "&quot;"; break;
        case '\'': out += "&#x27;"; break;
        default: out.push_back(c);
        }
    }
    return out;
}
void append_download_body(std::string& out, std::string_view body) {
    std::size_t copied = 0;
    for (auto pos = body.find("assets/"); pos != body.npos; pos = body.find("assets/", pos + 7)) {
        bool relative = false;
        for (std::string_view prefix : {"src=\"", "src='", "href=\"", "href='"}) {
            if (pos >= prefix.size() && body.substr(pos - prefix.size(), prefix.size()) == prefix) {
                relative = true;
                break;
            }
        }
        if (relative) {
            out.append(body.substr(copied, pos - copied));
            out += "../../";
            copied = pos;
        }
    }
    out.append(body.substr(copied));
}
}

DailySourceStatus validate_daily_source(std::string_view directory, std::string_view source) noexcept {
    using Status = DailySourceStatus;
    if (source.size() < 5 || source.substr(source.size() - 5) != ".html"
        || source.find_first_of("\\:") != source.npos || source.find('\0') != source.npos)
        return Status::invalid_relative_path;
    for (std::size_t start = 0; start < source.size();) {
        const auto end = source.find('/', start);
        const auto name = source.substr(start, end == source.npos ? end : end - start);
        if (name.empty() || name == "." || name == "..") return Status::invalid_relative_path;
        if (end == source.npos) break;
        start = end + 1;
    }
    try {
        if (directory.find('\0') != directory.npos) return Status::unreadable_path;
        const auto parent = resolve_source_path(fs::absolute(fs::u8path(directory)));
        const auto target = resolve_source_path(parent / fs::u8path(source));
        auto part = target.begin();
        for (const auto& component : parent) {
            if (part == target.end() || !same_component(component, *part++))
                return Status::outside_daily_directory;
        }
        return Status::valid;
    } catch (...) {
        return Status::unreadable_path;
    }
}

std::string daily_scenes(std::string_view body) {
    constexpr std::string_view heading = "<h2";
    std::string result;
    result.reserve(body.size());
    std::size_t start = body.find(heading);
    if (start == body.npos) {
        start = 0;
    }
    auto intro = start ? strip_python_whitespace(body.substr(0, start)) : std::string_view{};
    for (std::size_t index = 0;; ++index) {
        const auto next = body.find(heading, start + heading.size());
        if (index) result += '\n';
        result += "<section class=\"daily-show-scene markdown-body\" data-scene=\"";
        result += std::to_string(index);
        result += "\">\n";
        if (index == 0 && !intro.empty()) {
            result.append(intro);
            result += '\n';
        }
        result.append(body.substr(start, next == body.npos ? next : next - start));
        result += "\n</section>";
        if (next == body.npos) break;
        start = next;
    }
    return result;
}

std::string markdown_title(std::string_view body, std::string_view fallback) {
    constexpr std::string_view break_candidates = "\n\r\v\f\x1c\x1d\x1e\xc2\xe2";
    while (!body.empty()) {
        auto next = body.find_first_of(break_candidates);
        while (next != body.npos && !line_break_width(body.substr(next)))
            next = body.find_first_of(break_candidates, next + 1);
        const auto line = body.substr(0, next);
        if (line.substr(0, 2) == "# ") return std::string(strip_python_whitespace(line.substr(2)));
        if (next == body.npos) break;
        body.remove_prefix(next + line_break_width(body.substr(next)));
    }
    return std::string(fallback);
}

std::string page(bool daily, const std::string& title, const std::string& body,
                 const std::string& redirect, const Metadata& metadata) {
    const std::string safe_title = escape(title);
    std::string tags, output;
    for (const auto& [key,value] : metadata) {
        if (value.empty()) continue;
        if (!tags.empty()) tags += "\n  ";
        tags += "<span hidden data-pagefind-meta=\"" + escape(key + ":" + value) + "\"></span>";
    }
    const std::string_view form = daily ? daily_template : index_template;
    output.reserve(form.size() + body.size() + tags.size());
    std::size_t pos = 0;
    while (pos < form.size()) {
        const auto open = form.find('@',pos);
        output.append(form.substr(pos,open-pos));
        if (open == form.npos) break;
        const auto remaining = form.substr(open);
        auto matches = [&](std::string_view token) { return remaining.substr(0, token.size()) == token; };
        if (matches("@TITLE_ATTR@")) {
            output += safe_title;
            pos = open + sizeof("@TITLE_ATTR@") - 1;
        } else if (matches("@BODY@")) {
            if (daily) append_download_body(output, body); else output += body;
            pos = open + sizeof("@BODY@") - 1;
        } else if (matches("@META_TAGS@")) {
            output += tags;
            pos = open + sizeof("@META_TAGS@") - 1;
        } else if (matches("@REDIRECT_HASH@")) {
            output += redirect;
            pos = open + sizeof("@REDIRECT_HASH@") - 1;
        } else {
            output += '@';
            pos = open + 1;
        }
    }
    return output;
}
}

#ifdef _WIN32
#define PAGE_API extern "C" __declspec(dllexport)
#else
#define PAGE_API extern "C"
#endif
struct Field { const char* data; std::size_t size; };
PAGE_API const char* dashboard_page_identity() noexcept { return dashboard::page_identity; }
PAGE_API int dashboard_daily_source_status(const Field* fields) noexcept {
    if (!fields || !fields[0].data || !fields[1].data)
        return static_cast<int>(dashboard::DailySourceStatus::unreadable_path);
    return static_cast<int>(dashboard::validate_daily_source(
        {fields[0].data, fields[0].size}, {fields[1].data, fields[1].size}));
}
PAGE_API const char* dashboard_daily_scenes(const char* body, std::size_t length, std::size_t* bytes) noexcept {
    try {
        if (!body || !bytes) return nullptr;
        thread_local std::string result;
        result = dashboard::daily_scenes({body, length});
        *bytes = result.size();
        return result.data();
    } catch (...) {
        return nullptr;
    }
}
PAGE_API const char* dashboard_markdown_title(const Field* fields, std::size_t* bytes) noexcept {
    try {
        if (!fields || !fields[0].data || !fields[1].data || !bytes) return nullptr;
        thread_local std::string result;
        result = dashboard::markdown_title({fields[0].data, fields[0].size}, {fields[1].data, fields[1].size});
        *bytes = result.size();
        return result.data();
    } catch (...) {
        return nullptr;
    }
}
PAGE_API const char* dashboard_render_page(int daily, const Field* fields, std::size_t count,
                                         std::size_t* bytes) noexcept {
    try {
        if (!fields || !bytes || count < 3 || (count-3)%2 || (daily != 0 && daily != 1)) return nullptr;
        auto get = [&](std::size_t i) { return std::string(fields[i].data, fields[i].size); };
        dashboard::Metadata metadata;
        for (std::size_t i=3; i<count; i+=2) metadata.emplace_back(get(i),get(i+1));
        thread_local std::string result;
        result = dashboard::page(daily != 0,get(0),get(1),get(2),metadata);
        *bytes = result.size();
        return result.data();
    } catch (...) { return nullptr; }
}
