#pragma once

#include <json.hpp>

#include <ctime>
#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

namespace dashboard {
namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
using Strings = std::vector<std::string>;

struct Page {
    std::string key, title, body, stage;
};

struct BuildOptions {
    fs::path root, output, asset_manifest, daily_cache, tags, pagefind;
    std::string build_time, asset_version;
};

struct Journal {
    Json entries = Json::array();
    Json chains = {{"tracks", Json::array()}, {"chains", Json::array()}, {"handoffs", Json::array()}};
    std::vector<Page> pages;
};

struct Document {
    Json metadata;
    std::string body;
};

std::string path_text(const fs::path& path);
std::string read_bytes(const fs::path& path);
std::string read_text(const fs::path& path);
void write_text(const fs::path& path, std::string_view content);
void write_atomic(const fs::path& path, std::string_view content);
Json read_json(const fs::path& path);
Json json_or(const Json& value, const std::string& field, Json fallback);
std::string string_or(const Json& value, const std::string& field, std::string fallback = {});
std::string trim(std::string_view text);
std::vector<fs::path> files_with_suffix(const fs::path& dir, std::string_view suffix);
bool ends_with(std::string_view text, std::string_view suffix);
bool contains(const Json& array, const Json& value);
std::string escape_html(std::string_view text, bool quotes = true);
std::string json_canonical(const Json& value);
std::string sha256(std::string_view bytes);
std::string china_time(std::string_view iso);
std::string china_time(std::time_t utc);
std::string mtime(const fs::path& path);
std::string weekday(const std::string& day);
bool valid_day(std::string_view text);
Document load_document(const fs::path& path);
std::string render_markdown(std::string_view markdown);
std::string highlight_code(std::string_view code, std::string_view language);
std::string runtime_html(std::string html, const std::string& prefix);
std::string run_process(const std::string& program, const Strings& args);
Strings split(std::string_view text, char delimiter);
void safe_output(const BuildOptions& options);
void copy_assets(const BuildOptions& options);
Journal build_journal(const BuildOptions& options, const Json& stages, const Json& daily);
void build_dashboard(const BuildOptions& options);
}
