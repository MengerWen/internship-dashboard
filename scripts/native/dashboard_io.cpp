#include "dashboard_build.hpp"

#include <yaml.h>

#include <algorithm>
#include <cctype>
#include <charconv>
#include <chrono>
#include <cstdio>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <regex>
#include <sstream>
#include <stdexcept>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#else
#include <openssl/sha.h>
#endif

namespace dashboard {
namespace {
constexpr std::time_t china_offset = 8 * 3600;

std::tm utc_tm(std::time_t value) {
    std::tm out{};
#ifdef _WIN32
    if (gmtime_s(&out, &value) != 0) throw std::runtime_error("invalid UTC time");
#else
    if (!gmtime_r(&value, &out)) throw std::runtime_error("invalid UTC time");
#endif
    return out;
}

std::time_t utc_epoch(std::tm value) {
#ifdef _WIN32
    return _mkgmtime64(&value);
#else
    return timegm(&value);
#endif
}

std::time_t date_epoch(std::string_view day) {
    std::tm value{};
    value.tm_year = std::stoi(std::string(day.substr(0, 4))) - 1900;
    value.tm_mon = std::stoi(std::string(day.substr(5, 2))) - 1;
    value.tm_mday = std::stoi(std::string(day.substr(8, 2)));
    return utc_epoch(value);
}

Json yaml_value(yaml_document_t& document, int index, unsigned depth) {
    if (depth > 64) throw std::runtime_error("YAML nesting is too deep");
    const auto* node = yaml_document_get_node(&document, index);
    if (!node) throw std::runtime_error("invalid YAML node");
    if (node->type == YAML_MAPPING_NODE) {
        auto value = Json::object();
        for (auto* p = node->data.mapping.pairs.start; p != node->data.mapping.pairs.top; ++p) {
            const auto* key = yaml_document_get_node(&document, p->key);
            if (!key || key->type != YAML_SCALAR_NODE) throw std::runtime_error("YAML keys must be scalars");
            std::string name(reinterpret_cast<const char*>(key->data.scalar.value), key->data.scalar.length);
            value[name] = yaml_value(document, p->value, depth + 1);
        }
        return value;
    }
    if (node->type == YAML_SEQUENCE_NODE) {
        auto value = Json::array();
        for (auto* p = node->data.sequence.items.start; p != node->data.sequence.items.top; ++p)
            value.push_back(yaml_value(document, *p, depth + 1));
        return value;
    }
    if (node->type != YAML_SCALAR_NODE) return nullptr;
    std::string value(reinterpret_cast<const char*>(node->data.scalar.value), node->data.scalar.length);
    if (node->data.scalar.style != YAML_PLAIN_SCALAR_STYLE) return value;
    auto lower = value;
    for (char& c : lower) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    if (lower.empty() || lower == "~" || lower == "null") return nullptr;
    if (lower == "true" || lower == "yes" || lower == "on") return true;
    if (lower == "false" || lower == "no" || lower == "off") return false;
    std::int64_t integer;
    const auto result = std::from_chars(value.data(), value.data() + value.size(), integer);
    if (result.ec == std::errc{} && result.ptr == value.data() + value.size()) return integer;
    return value;
}

Json parse_yaml(std::string_view input) {
    yaml_parser_t parser;
    if (!yaml_parser_initialize(&parser)) throw std::runtime_error("cannot initialize YAML parser");
    yaml_parser_set_input_string(&parser, reinterpret_cast<const unsigned char*>(input.data()), input.size());
    yaml_document_t document;
    if (!yaml_parser_load(&parser, &document)) {
        std::string error = parser.problem ? parser.problem : "invalid YAML";
        yaml_parser_delete(&parser);
        throw std::runtime_error(error);
    }
    yaml_parser_delete(&parser);
    try {
        const auto* root = yaml_document_get_root_node(&document);
        auto result = root && root->type == YAML_MAPPING_NODE ? yaml_value(document, 1, 0) : Json::object();
        yaml_document_delete(&document);
        return result;
    } catch (...) {
        yaml_document_delete(&document);
        throw;
    }
}
}

std::string path_text(const fs::path& path) {
    return path.generic_u8string();
}

std::string read_bytes(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot read " + path_text(path));
    std::string bytes;
    const auto size = fs::file_size(path);
    bytes.resize(static_cast<std::size_t>(size));
    if (!input.read(bytes.data(), static_cast<std::streamsize>(size)))
        throw std::runtime_error("cannot read complete file " + path_text(path));
    return bytes;
}

std::string read_text(const fs::path& path) {
    const auto bytes = read_bytes(path);
    if (bytes.find('\r') == std::string::npos) return bytes;
    std::string text;
    text.reserve(bytes.size());
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        if (bytes[i] != '\r') text += bytes[i];
        else if (i + 1 == bytes.size() || bytes[i + 1] != '\n') text += '\n';
    }
    return text;
}

void write_text(const fs::path& path, std::string_view content) {
    if (!path.parent_path().empty()) fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    out.write(content.data(), static_cast<std::streamsize>(content.size()));
    out.close();
    if (!out) throw std::runtime_error("cannot write " + path_text(path));
}

void write_atomic(const fs::path& path, std::string_view content) {
    auto temporary = path;
    temporary += ".tmp";
    write_text(temporary, content);
#ifdef _WIN32
    if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING))
        throw std::runtime_error("cannot replace " + path_text(path));
#else
    fs::rename(temporary, path);
#endif
}

Json read_json(const fs::path& path) {
    try {
        return Json::parse(read_bytes(path));
    } catch (const std::exception& error) {
        throw std::runtime_error(path_text(path) + ": " + error.what());
    }
}

Json json_or(const Json& value, const std::string& field, Json fallback) {
    if (!value.is_object()) return fallback;
    const auto item = value.find(field);
    return item == value.end() ? std::move(fallback) : *item;
}

std::string string_or(const Json& value, const std::string& field, std::string fallback) {
    if (!value.is_object()) return fallback;
    const auto item = value.find(field);
    if (item == value.end() || item->is_null()) return fallback;
    if (item->is_string()) {
        const auto& text = item->get_ref<const std::string&>();
        return text.empty() ? std::move(fallback) : text;
    }
    if (item->is_boolean()) return *item == true ? "True" : "False";
    return item->dump();
}

std::string trim(std::string_view text) {
    const auto first = text.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string_view::npos) return {};
    return std::string(text.substr(first, text.find_last_not_of(" \t\r\n\f\v") - first + 1));
}

std::vector<fs::path> files_with_suffix(const fs::path& dir, std::string_view suffix) {
    std::vector<fs::path> paths;
    if (!fs::exists(dir)) return paths;
    for (const auto& item : fs::directory_iterator(dir))
        if (ends_with(path_text(item.path().filename()), suffix)) paths.push_back(item.path());
    std::sort(paths.begin(), paths.end());
    return paths;
}

bool ends_with(std::string_view text, std::string_view suffix) {
    return text.size() >= suffix.size() && text.substr(text.size() - suffix.size()) == suffix;
}

bool contains(const Json& array, const Json& value) {
    return std::find(array.begin(), array.end(), value) != array.end();
}

std::string escape_html(std::string_view text, bool quotes) {
    std::string result;
    result.reserve(text.size());
    for (const auto c : text) {
        switch (c) {
        case '&': result += "&amp;"; break;
        case '<': result += "&lt;"; break;
        case '>': result += "&gt;"; break;
        case '"': result += quotes ? "&quot;" : "\""; break;
        case '\'': result += quotes ? "&#x27;" : "'"; break;
        default: result += c;
        }
    }
    return result;
}

std::string json_canonical(const Json& value) {
    const auto compact = nlohmann::json(value).dump();
    std::string result;
    bool in_string = false, escaped = false;
    for (const auto c : compact) {
        result += c;
        if (in_string) {
            if (escaped) escaped = false;
            else if (c == '\\') escaped = true;
            else if (c == '"') in_string = false;
        } else if (c == '"') in_string = true;
        else if (c == ',' || c == ':') result += ' ';
    }
    return result;
}

std::string sha256(std::string_view bytes) {
    unsigned char hash[32]{};
#ifdef _WIN32
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    auto status = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
    if (status < 0) throw std::runtime_error("cannot open SHA-256 provider");
    status = BCryptHash(algorithm, nullptr, 0, reinterpret_cast<PUCHAR>(const_cast<char*>(bytes.data())),
                       static_cast<ULONG>(bytes.size()), hash, sizeof(hash));
    BCryptCloseAlgorithmProvider(algorithm, 0);
    if (status < 0) throw std::runtime_error("SHA-256 failed");
#else
    if (!SHA256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(), hash))
        throw std::runtime_error("SHA-256 failed");
#endif
    constexpr char hex[] = "0123456789abcdef";
    std::string result;
    for (const auto c : hash) {
        result += hex[c >> 4];
        result += hex[c & 15];
    }
    return result;
}

std::string china_time(std::time_t utc) {
    const auto local = utc_tm(utc + china_offset);
    char buffer[40]{};
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S+08:00", &local);
    return buffer;
}

bool valid_day(std::string_view text) {
    static const std::regex date(R"(\d{4}-\d{2}-\d{2})");
    if (!std::regex_match(text.begin(), text.end(), date)) return false;
    try { return china_time(date_epoch(text) - china_offset).substr(0, 10) == text; }
    catch (const std::exception&) { return false; }
}

std::string china_time(std::string_view input) {
    static const std::regex iso(R"((\d{4}-\d{2}-\d{2})(?:[Tt ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?)");
    const auto text = trim(input);
    std::smatch match;
    if (!std::regex_match(text, match, iso) || !valid_day(match[1].str())) return {};
    int offset = china_offset;
    auto seconds = date_epoch(match[1].str());
    if (match[2].matched) {
        const int hour = std::stoi(match[2].str());
        const int minute = std::stoi(match[3].str());
        const int second = match[4].matched ? std::stoi(match[4].str()) : 0;
        if (hour > 23 || minute > 59 || second > 59) return {};
        seconds += hour * 3600 + minute * 60 + second;
        const auto zone = match[5].str();
        if (zone == "Z") offset = 0;
        else if (!zone.empty()) {
            const int zone_hours = std::stoi(zone.substr(1, 2));
            const int zone_minutes = std::stoi(zone.substr(zone.size() - 2));
            if (zone_hours > 23 || zone_minutes > 59) return {};
            offset = (zone_hours * 3600 + zone_minutes * 60) * (zone[0] == '+' ? 1 : -1);
        }
    }
    return china_time(seconds - offset);
}

std::string weekday(const std::string& day) {
    static const char* weekdays[] = {"周日", "周一", "周二", "周三", "周四", "周五", "周六"};
    return weekdays[utc_tm(date_epoch(day)).tm_wday];
}

std::string mtime(const fs::path& path) {
#ifdef _WIN32
    WIN32_FILE_ATTRIBUTE_DATA data;
    if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &data))
        throw std::runtime_error("cannot read modification time " + path_text(path));
    ULARGE_INTEGER win_time;
    win_time.LowPart = data.ftLastWriteTime.dwLowDateTime;
    win_time.HighPart = data.ftLastWriteTime.dwHighDateTime;
    return china_time(static_cast<std::time_t>(win_time.QuadPart / 10000000ULL - 11644473600ULL));
#else
    const auto file = fs::last_write_time(path);
    const auto time = file - fs::file_time_type::clock::now() + std::chrono::system_clock::now();
    return china_time(std::chrono::system_clock::to_time_t(time));
#endif
}

Document load_document(const fs::path& path) {
    auto text = trim(read_text(path));
    if (text.compare(0, 3, "\xef\xbb\xbf") == 0) text = trim(text.substr(3));
    static const std::regex delimiter(R"(^-{3,}[ \t]*$)");
    const auto first = text.find('\n');
    if (first != std::string::npos && std::regex_match(text.substr(0, first), delimiter)) {
        std::size_t start = first + 1;
        for (std::size_t end = text.find('\n', start); ; end = text.find('\n', start)) {
            if (std::regex_match(text.substr(start, end - start), delimiter)) {
                auto meta = parse_yaml(std::string_view(text).substr(first + 1, start - first - 1));
                return {std::move(meta), end == std::string::npos ? "" : trim(text.substr(end + 1))};
            }
            if (end == std::string::npos) break;
            start = end + 1;
        }
    }
    return {Json::object(), std::move(text)};
}

Strings split(std::string_view text, char delimiter) {
    Strings parts;
    for (std::size_t start = 0; start <= text.size();) {
        const auto end = text.find(delimiter, start);
        parts.emplace_back(text.substr(start, end - start));
        if (end == std::string_view::npos) break;
        start = end + 1;
    }
    return parts;
}
}
