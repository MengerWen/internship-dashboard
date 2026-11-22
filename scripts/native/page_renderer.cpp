#include "page_renderer.hpp"
#include "compiled_pages.hpp"
#include <cstddef>
#include <string_view>

namespace dashboard {
namespace {
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
