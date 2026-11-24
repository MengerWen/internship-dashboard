#include "dashboard_build.hpp"

#include <cctype>
#include <regex>
#include <set>
#include <string_view>

namespace dashboard {
namespace {
std::string escaped(std::string_view value) {
    std::string result;
    for (const char c : value) {
        switch (c) {
        case '&': result += "&amp;"; break;
        case '<': result += "&lt;"; break;
        case '>': result += "&gt;"; break;
        case '"': result += "&quot;"; break;
        case '\'': result += "&#39;"; break;
        default: result += c; break;
        }
    }
    return result;
}

class Spans {
public:
    void add(std::string_view name, std::string_view value) {
        if (value.empty()) return;
        if (active_ != name) {
            if (!active_.empty()) text_ += "</span>";
            if (!name.empty()) text_ += "<span class=\"" + std::string(name) + "\">";
            active_ = name;
        }
        text_ += escaped(value);
    }

    std::string finish() {
        if (!active_.empty()) text_ += "</span>";
        return std::move(text_);
    }

private:
    std::string text_;
    std::string_view active_;
};

bool is_letter(char c) {
    return std::isalpha(static_cast<unsigned char>(c)) || static_cast<unsigned char>(c) >= 0x80 || c == '_';
}

bool is_digit(char c) {
    return std::isdigit(static_cast<unsigned char>(c)) != 0;
}

std::size_t match_prefix(std::string_view text, const std::regex& pattern) {
    std::match_results<std::string_view::const_iterator> match;
    return std::regex_search(text.begin(), text.end(), match, pattern, std::regex_constants::match_continuous)
        ? static_cast<std::size_t>(match.length()) : 0;
}

void python_tokens(Spans& output, std::string_view code, unsigned depth = 0) {
    static const std::set<std::string_view> keywords{
        "as", "assert", "async", "await", "break", "case", "class", "continue", "def", "del", "elif", "else",
        "except", "finally", "for", "global", "if", "lambda", "match", "nonlocal", "pass", "raise", "return",
        "try", "while", "with", "yield"
    };
    static const std::set<std::string_view> builtins{
        "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex",
        "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset",
        "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter",
        "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow",
        "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
        "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__"
    };
    static const std::set<std::string_view> operators{"and", "in", "is", "not", "or"};
    static const std::regex number(R"((0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:[0-9][0-9_]*\.?[0-9_]*|\.[0-9][0-9_]*)(?:[eE][+-]?[0-9_]+)?[jJ]?))");
    std::string_view next_name;
    bool importing = false, from_import = false;
    for (std::size_t i = 0; i < code.size();) {
        auto end = i + 1;
        std::string_view kind;
        const auto c = code[i];
        const bool prefixed_string = std::string_view("fFrRbBuU").find(c) != std::string_view::npos &&
            end < code.size() && (code[end] == '\'' || code[end] == '"');
        if (c == '#') end = code.size(), kind = "c1";
        else if (c == '\'' || c == '"' || prefixed_string) {
            const auto quote_pos = prefixed_string ? i + 1 : i;
            if (prefixed_string) output.add("sa", code.substr(i, 1));
            const char quote = code[quote_pos];
            const auto quoted = quote == '\'' ? "s1" : "s2";
            output.add(quoted, code.substr(quote_pos, 1));
            i = quote_pos + 1;
            while (i < code.size()) {
                const char current = code[i];
                if (current == '\\' && i + 1 < code.size() &&
                    std::string_view("\\'\"abfnrtv").find(code[i + 1]) != std::string_view::npos) {
                    output.add("se", code.substr(i, 2));
                    i += 2;
                    continue;
                }
                if (prefixed_string && (c == 'f' || c == 'F') && current == '{' && depth < 8) {
                    const auto close = code.find('}', i + 1);
                    if (close != std::string_view::npos) {
                        output.add("si", code.substr(i, 1));
                        python_tokens(output, code.substr(i + 1, close - i - 1), depth + 1);
                        output.add("si", code.substr(close, 1));
                        i = close + 1;
                        continue;
                    }
                }
                output.add(quoted, code.substr(i++, 1));
                if (current == quote) break;
            }
            continue;
        } else if (is_letter(c)) {
            while (end < code.size() && (is_letter(code[end]) || is_digit(code[end]) || (importing && code[end] == '.'))) ++end;
            const auto word = code.substr(i, end - i);
            if (word == "from" || word == "import") {
                kind = "kn";
                if (word == "from") from_import = true;
                importing = word == "from" || !from_import;
            } else if (operators.count(word)) kind = "ow";
            else if (keywords.count(word)) {
                kind = "k";
                if (word == "def") next_name = "nf";
                else if (word == "class") next_name = "nc";
            } else if (!next_name.empty()) {
                kind = next_name;
                next_name = {};
            } else if (importing) kind = "nn";
            else if (word == "True" || word == "False" || word == "None") kind = "kc";
            else if (word == "self" || word == "cls" || word == "Ellipsis" || word == "NotImplemented") kind = "bp";
            else if ((i == 0 || code[i - 1] != '.') && builtins.count(word)) kind = "nb";
            else kind = "n";
        } else if (is_digit(c) || (c == '.' && end < code.size() && is_digit(code[end]))) {
            const auto length = match_prefix(code.substr(i), number);
            end = i + length;
            const auto value = code.substr(i, length);
            if (value.size() > 2 && (value[1] == 'x' || value[1] == 'X')) kind = "mh";
            else if (value.size() > 2 && (value[1] == 'b' || value[1] == 'B')) kind = "mb";
            else if (value.size() > 2 && (value[1] == 'o' || value[1] == 'O')) kind = "mo";
            else kind = value.find_first_of(".eE") == std::string_view::npos ? "mi" : "mf";
        } else if (std::string_view("[]{}():,;").find(c) != std::string_view::npos) kind = "p";
        else if (std::string_view("+-*/%&|^<>=~@.").find(c) != std::string_view::npos) kind = "o";
        output.add(kind, code.substr(i, end - i));
        i = end;
    }
}

void shell_tokens(Spans& output, std::string_view code, bool powershell) {
    static const std::set<std::string_view> commands{"echo", "cd", "printf", "export", "read", "set", "exit", "source", "return"};
    for (std::size_t i = 0; i < code.size();) {
        auto end = i + 1;
        std::string_view kind;
        const auto c = code[i];
        if (c == '#') end = code.size(), kind = "c1";
        else if (c == ' ' || c == '\t') {
            while (end < code.size() && (code[end] == ' ' || code[end] == '\t')) ++end;
            kind = powershell ? "" : "w";
        } else if (c == '\'' || c == '"') {
            const auto close = code.find(c, end);
            end = close == std::string_view::npos ? code.size() : close + 1;
            kind = c == '\'' ? "s1" : "s2";
        } else if (powershell) {
            if (c == '[') {
                const auto close = code.find(']', end);
                end = close == std::string_view::npos ? end : close + 1;
                kind = "no";
            } else if (std::string_view(":\\.,{}()|<>").find(c) != std::string_view::npos ||
                       (c == '-' && i > 0 && code[i - 1] == ' ' && end < code.size() && code[end] == '-')) kind = "p";
            else {
                while (end < code.size() && (is_letter(code[end]) || is_digit(code[end]) || code[end] == '-')) ++end;
                kind = "n";
                if (code.substr(i, end - i) == "cli" && end < code.size() && code[end] == ' ') {
                    ++end;
                    kind = "nb";
                }
            }
        } else {
            while (end < code.size() && code[end] != ' ' && code[end] != '\t' && code[end] != ';' && code[end] != '|') ++end;
            if (is_digit(c)) {
                auto number_end = i + 1;
                while (number_end < end && is_digit(code[number_end])) ++number_end;
                if (number_end == end || code[number_end] == '-') {
                    kind = "m";
                    end = number_end;
                }
            } else if (commands.count(code.substr(i, end - i))) kind = "nb";
        }
        output.add(kind, code.substr(i, end - i));
        i = end;
    }
}
}

std::string highlight_code(std::string_view code, std::string_view language) {
    std::string html;
    const auto source = split(code, '\n');
    for (const auto& line : source) {
        Spans output;
        if (language == "python" || language == "py") python_tokens(output, line);
        else if (language == "bash" || language == "sh") shell_tokens(output, line, false);
        else if (language == "powershell" || language == "ps1") shell_tokens(output, line, true);
        else output.add("", line);
        html += output.finish() + '\n';
    }
    return html;
}
} // namespace dashboard
