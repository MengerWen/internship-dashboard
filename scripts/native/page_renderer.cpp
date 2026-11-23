#include "page_renderer.hpp"
#include "compiled_pages.hpp"
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
