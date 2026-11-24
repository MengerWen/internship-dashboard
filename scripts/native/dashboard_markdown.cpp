#include "dashboard_build.hpp"

#include <algorithm>
#include <cctype>
#include <codecvt>
#include <locale>
#include <map>
#include <regex>
#include <set>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

namespace dashboard {
namespace {
constexpr char tick = '`';

bool starts(std::string_view text, std::string_view prefix) {
    return text.substr(0, prefix.size()) == prefix;
}

bool space(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
}

bool word(char c) {
    return c == '_' || std::isalnum(static_cast<unsigned char>(c));
}

std::size_t dollar_end(std::string_view text, std::size_t i) {
    if (text[i] != '$' || (i && (text[i - 1] == '$' || text[i - 1] == '\\')) ||
        i + 1 == text.size() || space(text[i + 1]) || text[i + 1] == '$') return std::string_view::npos;
    for (auto end = i + 1; end < text.size() && text[end] != '\n'; ++end)
        if (text[end] == '$' && text[end - 1] != '\\' && !space(text[end - 1]) &&
            (end + 1 == text.size() || text[end + 1] != '$')) return end;
    return std::string_view::npos;
}

std::size_t code_end(std::string_view text, std::size_t opening, std::size_t& marker_length) {
    auto after = opening + 1;
    while (after < text.size() && text[after] == tick) ++after;
    marker_length = after - opening;
    const auto marker = text.substr(opening, marker_length);
    auto end = text.find(marker, after);
    while (end != std::string::npos &&
           ((end > after && text[end - 1] == tick) || (end + marker_length < text.size() && text[end + marker_length] == tick)))
        end = text.find(marker, end + 1);
    return end;
}

std::size_t emphasis_end(std::string_view text, std::size_t start, std::string_view marker) {
    for (auto i = start; i < text.size(); ++i) {
        if (text[i] == tick && (i == 0 || text[i - 1] != '\\')) {
            std::size_t length = 0;
            const auto end = code_end(text, i, length);
            if (end != std::string_view::npos) { i = end + length - 1; continue; }
        }
        if (text[i] == '$') {
            const auto end = dollar_end(text, i);
            if (end != std::string_view::npos) { i = end; continue; }
        }
        if (i != start && text.substr(i, marker.size()) == marker && text[i - 1] != '\\' &&
            !space(text[i - 1]) && (marker.front() != '_' ||
            (text[i - 1] != '_' && (i + marker.size() == text.size() || !word(text[i + marker.size()]))))) return i;
    }
    return std::string_view::npos;
}

std::string join(const Strings& lines, std::size_t start, std::size_t end) {
    std::string result;
    for (auto i = start; i < end; ++i) {
        if (i != start) result += '\n';
        result += lines[i];
    }
    return result;
}

std::size_t indent(std::string_view line) {
    const auto pos = line.find_first_not_of(' ');
    return pos == std::string::npos ? line.size() : pos;
}

std::string lowercase(std::string text) {
    for (auto& c : text) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return text;
}

std::string escape_attribute(std::string_view value) {
    std::string result = escape_html(value, false);
    for (auto pos = result.find('"'); pos != std::string::npos; pos = result.find('"', pos + 6))
        result.replace(pos, 1, "&quot;");
    return result;
}

std::string escape_code(std::string_view text, bool highlighted) {
    auto result = highlighted ? escape_attribute(text) : escape_html(text, false);
    if (highlighted)
        for (auto pos = result.find('\''); pos != std::string::npos; pos = result.find('\'', pos + 5))
            result.replace(pos, 1, "&#39;");
    return result;
}

std::string strip_tags(const std::string& text) {
    static const std::regex tag(R"(<(?:/?[A-Za-z][^>]*|!--[\s\S]*?--)>)");
    return std::regex_replace(text, tag, "");
}

std::string slug_for(std::string text) {
    static const std::regex entity(R"(&(?:#\d+|#x[\da-fA-F]+|[a-zA-Z][a-zA-Z\d]+);)");
    static const std::regex whitespace(R"(\s+)");
    text = trim(std::regex_replace(strip_tags(text), whitespace, " "));
    text = std::regex_replace(text, entity, "");
    if (text.empty()) return {};
    std::wstring kept;
#ifdef _WIN32
    const auto length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), nullptr, 0);
    if (!length) throw std::runtime_error("heading is not UTF-8");
    std::wstring wide(static_cast<std::size_t>(length), L'\0');
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), wide.data(), length))
        throw std::runtime_error("cannot decode heading");
    std::wstring lower(wide.size(), L'\0');
    if (LCMapStringEx(LOCALE_NAME_INVARIANT, LCMAP_LOWERCASE, wide.data(), length, lower.data(), length,
                      nullptr, nullptr, 0)) wide = std::move(lower);
    std::vector<WORD> types(wide.size());
    GetStringTypeW(CT_CTYPE1, wide.data(), length, types.data());
    for (std::size_t i = 0; i < wide.size(); ++i) {
        const auto c = wide[i];
        if (c == L' ') kept += L'-';
        else if (c == L'_' || c == L'-' || (types[i] & (C1_ALPHA | C1_DIGIT)) ||
                 c == L'²' || c == L'³' || c == L'¹' || (0x2070 <= c && c <= 0x209f)) kept += c;
    }
    if (kept.empty()) return {};
    const auto bytes = WideCharToMultiByte(CP_UTF8, 0, kept.data(), static_cast<int>(kept.size()), nullptr, 0, nullptr, nullptr);
    std::string result(static_cast<std::size_t>(bytes), '\0');
    WideCharToMultiByte(CP_UTF8, 0, kept.data(), static_cast<int>(kept.size()), result.data(), bytes, nullptr, nullptr);
    return result;
#else
    std::wstring_convert<std::codecvt_utf8<wchar_t>> codec;
    const auto wide = codec.from_bytes(text);
    static const std::locale utf8("C.UTF-8");
    const auto& ct = std::use_facet<std::ctype<wchar_t>>(utf8);
    for (const auto c : wide) {
        if (c == L' ') kept += L'-';
        else if (c == L'_' || c == L'-' || ct.is(std::ctype_base::alnum, c)) kept += ct.tolower(c);
    }
    return codec.to_bytes(kept);
#endif
}

struct Link {
    std::string url, title;
};

Link link_target(std::string target) {
    static const std::regex quoted(R"re(^(.*?)\s+["'](.*)["']$)re");
    std::smatch parts;
    std::string title;
    if (std::regex_match(target, parts, quoted)) {
        title = parts[2].str();
        target = trim(parts[1].str());
    }
    if (starts(target, "<") && ends_with(target, ">")) target = target.substr(1, target.size() - 2);
    return {std::move(target), std::move(title)};
}

std::size_t closing(std::string_view text, std::size_t start, char open, char close) {
    int depth = 1;
    for (std::size_t i = start; i < text.size(); ++i) {
        if (text[i] == '\\' && i + 1 < text.size()) ++i;
        else if (text[i] == open) ++depth;
        else if (text[i] == close && --depth == 0) return i;
    }
    return std::string::npos;
}

struct Marker {
    bool ordered;
    std::string text;
};

bool list_marker(const std::string& line, Marker& marker) {
    static const std::regex pattern(R"(^ {0,3}(?:([-+*])|([0-9]+)\.) +(.*)$)");
    std::smatch parts;
    if (!std::regex_match(line, parts, pattern)) return false;
    marker = {parts[2].matched, parts[3].str()};
    return true;
}

bool ruler(const std::string& line) {
    const auto first = indent(line);
    if (first >= 4 || first >= line.size()) return false;
    const auto c = line[first];
    return (c == '-' || c == '*' || c == '_') &&
           std::count(line.begin(), line.end(), c) >= 3 &&
           std::all_of(line.begin(), line.end(), [c](char x) { return x == c || x == ' '; });
}

bool raw_block(const std::string& line, std::string& tag) {
    if (indent(line) >= 4) return false;
    const auto text = std::string_view(line).substr(indent(line));
    if (starts(text, "<!--")) { tag = "!--"; return true; }
    if (!starts(text, "<")) return false;
    static const std::regex opener(R"(^<([a-zA-Z][a-zA-Z0-9]*)(?:[ />]|$))");
    static const std::set<std::string> tags{"address", "article", "aside", "blockquote", "canvas", "dd", "details",
        "dialog", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "hgroup", "hr", "iframe", "li", "main", "nav", "ol", "p", "pre", "script",
        "section", "style", "table", "tbody", "td", "th", "thead", "tr", "ul"};
    std::match_results<std::string_view::const_iterator> match;
    if (!std::regex_search(text.begin(), text.end(), match, opener)) return false;
    tag = lowercase(match[1].str());
    return tags.count(tag) != 0;
}

std::size_t raw_end(const Strings& lines, std::size_t start, const std::string& tag) {
    if (tag == "hr") return start;
    const auto ending = tag == "!--" ? "-->" : "</" + tag + '>';
    while (start + 1 < lines.size() && lowercase(lines[start]).find(ending) == std::string::npos) ++start;
    return start;
}

Strings cells(std::string_view line) {
    const auto trimmed = trim(line);
    line = trimmed;
    if (starts(line, "|")) line.remove_prefix(1);
    if (ends_with(line, "|") && !ends_with(line, "\\|")) line.remove_suffix(1);
    Strings result;
    std::size_t start = 0, code = 0;
    for (std::size_t i = 0; i < line.size(); ++i) {
        if (line[i] == '\\' && i + 1 < line.size()) { ++i; continue; }
        if (line[i] == tick) {
            auto end = i + 1;
            while (end < line.size() && line[end] == tick) ++end;
            const auto length = end - i;
            if (code == length) code = 0;
            else if (code == 0 && line.find(std::string(length, tick), end) != std::string::npos) code = length;
            i = end - 1;
        } else if (line[i] == '|' && !code) {
            result.push_back(trim(line.substr(start, i - start)));
            start = i + 1;
        }
    }
    result.push_back(trim(line.substr(start)));
    return result;
}

bool table_separator(const std::string& line, Strings& alignment) {
    static const std::regex separator(R"(^:?-+:?$)");
    if (line.find('|') == std::string::npos || indent(line) >= 4) return false;
    alignment.clear();
    for (const auto& col : cells(line)) {
        if (!std::regex_match(col, separator)) return false;
        const bool left = starts(col, ":"), right = ends_with(col, ":");
        alignment.push_back(left && right ? "center" : left ? "left" : right ? "right" : "");
    }
    return !alignment.empty();
}

class Markdown {
public:
    std::string convert(std::string_view source) {
        auto lines = split(source, '\n');
        static const std::regex reference(R"(^ {0,3}\[([^\]]+)\]:[ \t]+(.+)$)");
        bool fenced = false;
        for (auto& line : lines) {
            std::string expanded;
            std::size_t column = 0;
            for (const auto c : line) {
                if (c == '\t') {
                    expanded.append(4 - column % 4, ' ');
                    column += 4 - column % 4;
                } else {
                    expanded += c;
                    if ((static_cast<unsigned char>(c) & 0xc0) != 0x80) ++column;
                }
            }
            line = std::move(expanded);
            if (trim(line).empty()) line.clear();
            if (is_fence(trim(line))) { fenced = !fenced; continue; }
            if (fenced) continue;
            std::smatch parts;
            if (std::regex_match(line, parts, reference)) {
                references_[lowercase(parts[1].str())] = link_target(trim(parts[2].str()));
                line.clear();
            }
        }
        return trim(blocks(lines));
    }

private:
    std::map<std::string, Link> references_;
    std::set<std::string> slugs_;

    static bool is_fence(std::string_view text) {
        return starts(text, "~~~") || starts(text, "```");
    }

    std::string inline_html(std::string_view text, bool links = true, unsigned depth = 0) {
        if (depth > 32) return escape_html(text, false);
        std::string result;
        for (std::size_t i = 0; i < text.size();) {
            const auto c = text[i];
            if (c == '\\' && i + 1 < text.size()) {
                if (text[i + 1] == '(') {
                    const auto end = text.find("\\)", i + 2);
                    if (end != std::string::npos && end > i + 2) {
                        result += "<span class=\"arithmatex\">\\(" + escape_html(text.substr(i + 2, end - i - 2), false) + "\\)</span>";
                        i = end + 2;
                        continue;
                    }
                }
                if (std::string_view("\\`*_{}[]()>#+-.!|~$").find(text[i + 1]) != std::string::npos) {
                    result += escape_html(text.substr(i + 1, 1), false);
                    i += 2;
                    continue;
                }
            }
            if (c == tick) {
                std::size_t length = 0;
                const auto end = code_end(text, i, length);
                const auto end_run = i + length;
                if (end != std::string::npos) {
                    result += "<code>" + escape_code(trim(text.substr(end_run, end - end_run)), false) + "</code>";
                    i = end + length;
                    continue;
                }
                result.append(text.substr(i, length));
                i = end_run;
                continue;
            }
            if (c == '<') {
                const bool comment = starts(text.substr(i), "<!--");
                const auto end = comment ? text.find("-->", i + 4) : text.find('>', i + 1);
                if (end != std::string::npos) {
                    const auto tag = text.substr(i + 1, end - i - 1);
                    const bool autolink = starts(tag, "https://") || starts(tag, "http://") || starts(tag, "ftp://");
                    if (autolink && tag.find_first_of(" \t\n") == std::string::npos) {
                        result += "<a href=\"" + escape_attribute(tag) + "\">" + escape_html(tag, false) + "</a>";
                        i = end + 1;
                        continue;
                    }
                    static const std::regex email(R"((?:mailto:)?[^<>\s@]+@[^<>\s@]+)");
                    if (std::regex_match(tag.begin(), tag.end(), email)) {
                        auto encoded = [](std::string_view value) {
                            std::string x;
                            for (const unsigned char ch : value) x += "&#" + std::to_string(ch) + ";";
                            return x;
                        };
                        auto address = starts(tag, "mailto:") ? tag.substr(7) : tag;
                        result += "<a href=\"" + encoded("mailto:" + std::string(address)) + "\">" + encoded(address) + "</a>";
                        i = end + 1;
                        continue;
                    }
                    static const std::regex valid_tag(R"(^/?[A-Za-z][A-Za-z0-9:-]*(?:\s[\s\S]*|/)?$)");
                    if (comment || starts(tag, "!") || starts(tag, "?") ||
                        std::regex_match(tag.begin(), tag.end(), valid_tag)) {
                        const auto close = end + (comment ? 3 : 1);
                        result.append(text.substr(i, close - i));
                        i = close;
                        continue;
                    }
                }
            }
            if (c == '&') {
                static const std::regex entity(R"(^&(?:#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*);)");
                std::match_results<std::string_view::const_iterator> match;
                if (std::regex_search(text.begin() + i, text.begin() + std::min(i + 64, text.size()), match, entity)) {
                    result.append(match[0].first, match[0].second);
                    i += static_cast<std::size_t>(match.length());
                    continue;
                }
            }
            const bool image = c == '!' && i + 1 < text.size() && text[i + 1] == '[';
            if (image || (links && c == '[')) {
                const auto open = i + (image ? 1 : 0);
                const auto end = closing(text, open + 1, '[', ']');
                if (end != std::string::npos) {
                    const auto label = std::string(text.substr(open + 1, end - open - 1));
                    auto next = end + 1;
                    Link target;
                    bool found = false;
                    if (next < text.size() && text[next] == '(') {
                        const auto end_url = closing(text, next + 1, '(', ')');
                        if (end_url != std::string::npos) {
                            target = link_target(trim(text.substr(next + 1, end_url - next - 1)));
                            next = end_url + 1;
                            found = true;
                        }
                    } else {
                        auto reference = label;
                        if (next + 1 < text.size() && text[next] == ' ' && text[next + 1] == '[') ++next;
                        if (next < text.size() && text[next] == '[') {
                            const auto end_ref = text.find(']', next + 1);
                            if (end_ref != std::string::npos) {
                                if (end_ref > next + 1) reference = std::string(text.substr(next + 1, end_ref - next - 1));
                                next = end_ref + 1;
                            }
                        }
                        if (const auto entry = references_.find(lowercase(reference)); entry != references_.end()) {
                            target = entry->second;
                            found = true;
                        }
                    }
                    if (found) {
                        const std::string title = target.title.empty() ? "" : " title=\"" + escape_attribute(target.title) + '"';
                        auto contents = inline_html(label, false, depth + 1);
                        if (image) {
                            contents = strip_tags(contents);
                            for (auto q = contents.find('"'); q != std::string::npos; q = contents.find('"', q + 6))
                                contents.replace(q, 1, "&quot;");
                            result += "<img alt=\"" + contents + "\" src=\"" + escape_attribute(target.url) + '"' + title + ">";
                        } else result += "<a href=\"" + escape_attribute(target.url) + '"' + title + ">" + contents + "</a>";
                        i = next;
                        continue;
                    }
                }
            }
            if (c == '$') {
                if (const auto end = dollar_end(text, i); end != std::string_view::npos) {
                    result += "<span class=\"arithmatex\">\\(" + escape_html(text.substr(i + 1, end - i - 1), false) + "\\)</span>";
                    i = end + 1;
                    continue;
                }
            }
            if (c == '*' || (c == '_' && (i == 0 || !word(text[i - 1])))) {
                std::size_t count = 1;
                while (i + count < text.size() && text[i + count] == c && count < 3) ++count;
                if (i + count < text.size() && !space(text[i + count])) {
                    const std::string marker(count, c);
                    const auto end = emphasis_end(text, i + count, marker);
                    if (end != std::string::npos) {
                        const std::string opening = count == 3 ? "<strong><em>" : count == 2 ? "<strong>" : "<em>";
                        const std::string ending = count == 3 ? "</em></strong>" : count == 2 ? "</strong>" : "</em>";
                        result += opening + inline_html(text.substr(i + count, end - i - count), links, depth + 1) + ending;
                        i = end + count;
                        continue;
                    }
                }
            }
            if (c == ' ') {
                auto end = i + 1;
                while (end < text.size() && text[end] == ' ') ++end;
                if (end - i >= 2 && end < text.size() && text[end] == '\n') {
                    result += "<br>\n";
                    i = end + 1;
                    continue;
                }
            }
            if (c == '&') result += "&amp;";
            else if (c == '<') result += "&lt;";
            else if (c == '>') result += "&gt;";
            else result += c;
            ++i;
        }
        return result;
    }

    std::string heading(std::string text, std::size_t level) {
        static const std::regex closing_hashes(R"( *#+$)");
        text = trim(std::regex_replace(text, closing_hashes, ""));
        static const std::regex attr(R"( +\{#([^} ]+)\}$)");
        std::smatch explicit_id;
        std::string id;
        if (std::regex_search(text, explicit_id, attr)) {
            id = explicit_id[1].str();
            text.erase(static_cast<std::size_t>(explicit_id.position()));
            slugs_.insert(id);
        }
        auto html = inline_html(text);
        if (id.empty()) {
            id = slug_for(html);
            auto base = id;
            static const std::regex numbered(R"(^(.*)_(\d+)$)");
            std::smatch counter;
            std::size_t index = 1;
            if (std::regex_match(id, counter, numbered)) {
                base = counter[1].str();
                index = std::stoull(counter[2].str()) + 1;
            }
            while (id.empty() || slugs_.count(id)) id = base + '_' + std::to_string(index++);
            slugs_.insert(id);
        }
        const auto tag = "h" + std::to_string(level);
        return "<" + tag + " id=\"" + escape_attribute(id) + "\">" + html + "</" + tag + ">";
    }

    std::string table(const Strings& lines, std::size_t& i, const Strings& align) {
        auto html = std::string("<table>\n<thead>\n");
        auto row = [&](const Strings& input, const std::string& tag) {
            html += "<tr>\n";
            for (std::size_t k = 0; k < align.size(); ++k) {
                html += '<' + tag;
                if (!align[k].empty()) html += " style=\"text-align: " + align[k] + ";\"";
                html += '>' + (k < input.size() ? inline_html(input[k]) : "") + "</" + tag + ">\n";
            }
            html += "</tr>\n";
        };
        row(cells(lines[i]), "th");
        html += "</thead>\n<tbody>\n";
        i += 2;
        if (i == lines.size() || lines[i].empty()) row({}, "td");
        while (i < lines.size() && !lines[i].empty()) row(cells(lines[i++]), "td");
        return html + "</tbody>\n</table>";
    }

    std::string list(const Strings& lines, std::size_t& i, const Marker& first) {
        const std::string tag = first.ordered ? "ol" : "ul";
        std::vector<Strings> items;
        std::vector<Strings> continuations;
        std::vector<bool> loose;
        std::vector<std::string> trailing_html;
        bool previous_blank = false;
        Marker mark{};
        while (i < lines.size() && !ruler(lines[i]) && list_marker(lines[i], mark)) {
            Strings item{mark.text};
            Strings continuation;
            ++i;
            bool has_blank = previous_blank;
            previous_blank = false;
            std::string raw_html;
            while (i < lines.size()) {
                if (lines[i].empty()) {
                    auto next = i + 1;
                    while (next < lines.size() && lines[next].empty()) ++next;
                    if (next == lines.size()) { i = next; break; }
                    Marker next_mark{};
                    if (list_marker(lines[next], next_mark) && !ruler(lines[next])) {
                        has_blank = true;
                        previous_blank = true;
                        i = next;
                    } else if (indent(lines[next]) >= 4) {
                        has_blank = true;
                        i = next;
                        auto end = next;
                        bool crosses_indent = false;
                        while (end < lines.size() && !lines[end].empty()) {
                            crosses_indent |= indent(lines[end]) < 4;
                            ++end;
                        }
                        // A dollar delimiter in a mixed-indent list block is literal Markdown text.
                        if (trim(lines[next]) == "$$" && crosses_indent) {
                            while (i < end) {
                                const auto padding = indent(lines[i]) >= 4 ? 4 : 0;
                                continuation.push_back(lines[i++].substr(padding));
                            }
                        } else {
                            item.emplace_back();
                            continue;
                        }
                    } else i = next;
                    break;
                }
                std::string raw_tag;
                if (raw_block(lines[i], raw_tag)) {
                    if (raw_tag != "!--") {
                        const auto end = raw_end(lines, i, raw_tag);
                        raw_html = join(lines, i, end + 1).substr(indent(lines[i]));
                        i = end + 1;
                    }
                    break;
                }
                Marker next{};
                if (list_marker(lines[i], next) || ruler(lines[i]) || starts(lines[i], "#")) break;
                if (indent(lines[i]) >= 4) item.push_back(lines[i++].substr(4));
                else item.push_back(lines[i++]);
            }
            items.push_back(std::move(item));
            continuations.push_back(std::move(continuation));
            loose.push_back(has_blank);
            const bool interrupted_by_html = !raw_html.empty();
            trailing_html.push_back(std::move(raw_html));
            if (interrupted_by_html) break;
        }
        std::string html = '<' + tag + ">\n";
        for (std::size_t j = 0; j < items.size(); ++j) {
            const auto& item = items[j];
            std::string body;
            std::size_t boundary = 1;
            Marker nested{};
            while (boundary < item.size() && !item[boundary].empty() && !list_marker(item[boundary], nested)) ++boundary;
            auto start = inline_html(join(item, 0, boundary));
            body = loose[j] ? "\n<p>" + start + "</p>\n" : start;
            if (boundary < item.size()) body += blocks(Strings(item.begin() + boundary, item.end())) + '\n';
            if (!continuations[j].empty()) body += "<p>" + inline_html(join(continuations[j], 0, continuations[j].size())) + "</p>\n";
            if (!trailing_html[j].empty()) body += "\n<br>\n" + trailing_html[j];
            html += "<li>" + body + "</li>\n";
        }
        return html + "</" + tag + '>';
    }

    std::string blocks(const Strings& lines) {
        static const std::regex atx(R"(^(#{1,6})(.*)$)");
        static const std::regex setext(R"(^ *(=+|-+) *$)");
        static const std::regex fence(R"(^ {0,3}(~{3,}|`{3,}) *([a-zA-Z0-9_+-]*) *(?:\{[^}]*\})? *$)");
        static const std::regex disclosure(R"re(^(\?\?\?\+?|!!!) +([A-Za-z0-9_-]+(?: +[A-Za-z0-9_-]+)*?)(?: +"(.*)")? *$)re");
        std::string html;
        auto emit = [&](std::string text) {
            if (!html.empty()) html += '\n';
            html += text;
        };
        for (std::size_t i = 0; i < lines.size();) {
            const auto& line = lines[i];
            if (line.empty()) { ++i; continue; }
            std::smatch match;
            if (is_fence(trim(line)) && std::regex_match(line, match, fence)) {
                const auto marker = match[1].str();
                auto end = i + 1;
                while (end < lines.size() && trim(lines[end]) != marker) ++end;
                if (end < lines.size()) {
                    const auto code = join(lines, i + 1, end);
                    if (match[2].str() == "mermaid") emit("<div class=\"mermaid\">" + escape_code(code, false) + "</div>");
                    else emit("<div class=\"highlight\"><pre><span></span><code>" +
                              highlight_code(code, match[2].str()) + "</code></pre></div>");
                    i = end + 1;
                    continue;
                }
            }
            if (starts(line, "#") && std::regex_match(line, match, atx)) {
                emit(heading(match[2].str(), static_cast<std::size_t>(match[1].length())));
                ++i;
                continue;
            }
            if (i + 1 < lines.size() && indent(line) < 4 && std::regex_match(lines[i + 1], match, setext)) {
                emit(heading(line, match[1].str().front() == '=' ? 1 : 2));
                i += 2;
                continue;
            }
            if (ruler(line)) { emit("<hr>"); ++i; continue; }
            if (i + 1 < lines.size() && line.find('|') != std::string::npos) {
                Strings alignment;
                if (table_separator(lines[i + 1], alignment) && cells(line).size() == alignment.size()) {
                    emit(table(lines, i, alignment));
                    continue;
                }
            }
            if (std::regex_match(line, match, disclosure)) {
                const auto kind = match[1].str();
                const auto classes = match[2].str();
                auto title = match[3].matched ? match[3].str() : classes.substr(0, classes.find(' '));
                if (!match[3].matched && !title.empty()) title[0] = static_cast<char>(std::toupper(static_cast<unsigned char>(title[0])));
                Strings inner;
                ++i;
                while (i < lines.size()) {
                    if (indent(lines[i]) >= 4) inner.push_back(lines[i++].substr(4));
                    else if (lines[i].empty()) inner.push_back(lines[i++]);
                    else break;
                }
                const auto body = blocks(inner);
                if (kind == "!!!")
                    emit("<div class=\"admonition " + classes + "\">\n" +
                         (title.empty() ? "" : "<p class=\"admonition-title\">" + inline_html(title) + "</p>\n") +
                         body + (body.empty() ? "" : "\n") + "</div>");
                else emit("<details class=\"" + classes + '"' + (kind == "???+" ? " open=\"open\"" : "") +
                          ">\n<summary>" + inline_html(title) + "</summary>\n" + body +
                          (body.empty() ? "" : "\n") + "</details>");
                continue;
            }
            if (starts(line, "$$") || starts(line, "\\[")) {
                const auto delimiter = starts(line, "$$") ? "$$" : "\\]";
                auto end = i;
                while (end < lines.size() &&
                       !(ends_with(trim(lines[end]), delimiter) && (end != i || trim(line).size() > 3))) ++end;
                if (end < lines.size()) {
                    const auto body = trim(join(lines, i, end + 1));
                    emit("<div class=\"arithmatex\">\\[" + escape_html(std::string_view(body).substr(2, body.size() - 4), false) + "\\]</div>");
                    i = end + 1;
                    continue;
                }
            }
            const auto trimmed = trim(line);
            std::string tag;
            if (raw_block(line, tag)) {
                const auto end = raw_end(lines, i, tag);
                auto body = join(lines, i, end + 1).substr(indent(line));
                if (end + 1 < lines.size() && lines[end + 1].empty() && tag != "p") body += '\n';
                emit(std::move(body));
                i = end + 1;
                continue;
            }
            if (starts(trimmed, ">") && indent(line) < 4) {
                Strings quote;
                while (i < lines.size()) {
                    auto q = lines[i].substr(indent(lines[i]));
                    if (starts(q, ">")) {
                        q.erase(0, starts(q, "> ") ? 2 : 1);
                        quote.push_back(q);
                        ++i;
                    } else if (lines[i].empty()) {
                        auto next = i + 1;
                        while (next < lines.size() && lines[next].empty()) ++next;
                        if (next < lines.size() && starts(trim(lines[next]), ">")) {
                            quote.emplace_back();
                            i = next;
                        } else break;
                    } else quote.push_back(lines[i++]);
                }
                emit("<blockquote>\n" + blocks(quote) + "\n</blockquote>");
                continue;
            }
            Marker marker{};
            if (list_marker(line, marker)) { emit(list(lines, i, marker)); continue; }
            if (indent(line) >= 4) {
                Strings code;
                while (i < lines.size() && (indent(lines[i]) >= 4 || lines[i].empty())) {
                    code.push_back(lines[i].empty() ? "" : lines[i].substr(4));
                    ++i;
                }
                const bool separated = !code.empty() && code.back().empty();
                while (!code.empty() && code.back().empty()) code.pop_back();
                emit("<div class=\"codehilite\"><pre><span></span><code>" +
                     escape_code(join(code, 0, code.size()), true) + "\n</code></pre></div>" + (separated ? "\n" : ""));
                continue;
            }
            auto end = i + 1;
            while (end < lines.size() && !lines[end].empty() && !starts(lines[end], "#") &&
                   !ruler(lines[end]) && !is_fence(trim(lines[end])) && !raw_block(lines[end], tag)) ++end;
            emit("<p>" + inline_html(join(lines, i, end).substr(indent(line))) + "</p>");
            i = end;
        }
        return html;
    }
};
}

std::string render_markdown(std::string_view markdown) {
    return Markdown().convert(markdown);
}
} // namespace dashboard
