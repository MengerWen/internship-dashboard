#include "dashboard_build.hpp"
#include "native_process.hpp"
#include "page_renderer.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <ctime>
#include <future>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <stdexcept>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

namespace dashboard {
namespace {
const auto array = Json::array();
const auto object = Json::object();
using History = std::pair<std::string, std::string>;
using Clock = std::chrono::steady_clock;

void report_time(const char* name, Clock::time_point started) {
    std::cout << name << ": " << std::chrono::duration<double>(Clock::now() - started).count() << " s\n";
}

const Json* record(const Json& cache, const char* group, const std::string& path) {
    if (const auto rows = cache.find(group); rows != cache.end() && rows->is_object()) {
        const auto row = rows->find(path);
        if (row != rows->end() && row->is_array() && row->size() == 2) return &*row;
    }
    return nullptr;
}

struct ReleaseCache {
    Json previous = object;
    Json rendered = object;
    Json times = object;
    std::set<std::string> changed;
    std::map<std::string, History> fetched;
    std::string head, git_config;
    std::size_t render_hits = 0, time_hits = 0;
    bool reuse_times = false;

    explicit ReleaseCache(const fs::path& path) {
        if (path.empty()) return;
        try { previous = read_json(path); }
        catch (const std::exception&) {}
        try {
            const auto current = split(run_process("git", {"rev-parse", "HEAD", "--is-shallow-repository"}), '\n');
            if (current.at(1) != "false" || !run_process("git", {"replace", "-l"}).empty()) return;
            if (fs::exists(fs::u8path(trim(run_process("git", {"rev-parse", "--git-path", "info/grafts"}))))) return;
            head = current.front();
            git_config = sha256(run_process("git", {"--version"}) +
                                run_process("git", {"config", "--null", "--list"}));
            const auto base = string_or(previous, "head");
            if (!std::regex_match(base, std::regex("[a-f0-9]{40,64}")) ||
                git_config != string_or(previous, "git_config")) return;
            if (base != head) {
                run_process("git", {"merge-base", "--is-ancestor", base, head});
                const auto span = base + ".." + head;
                if (!run_process("git", {"rev-list", "--max-count=1", "--merges", span}).empty()) return;
                auto names = split(run_process("git", {"log", "--format=", "--name-only", "-z", "--no-renames",
                                                       span, "--", "content/daily"}), '\0');
                changed.insert(names.begin(), names.end());
            }
            reuse_times = true;
        } catch (const std::exception&) {}
    }

    std::string render(const std::string& path, const std::string& body, bool cached) {
        if (!cached) return render_markdown(body);
        const auto digest = sha256(body);
        const auto* old = record(previous, "html", path);
        std::string html;
        if (old && string_or(previous, "renderer") == DASHBOARD_RENDERER_ID &&
            (*old)[0] == digest && (*old)[1].is_string()) {
            html = (*old)[1].get<std::string>();
            ++render_hits;
        } else html = render_markdown(body);
        rendered[path] = Json::array({digest, html});
        return html;
    }

    const Json* saved_history(const std::string& path, bool want_first) const {
        if (!reuse_times || changed.count(path)) return nullptr;
        const auto* old = record(previous, "times", path);
        if (!old || !(*old)[1].is_string() || (want_first && !(*old)[0].is_string())) return nullptr;
        return old;
    }

    static History read_history(const std::string& path, bool want_first) {
        try {
            std::string first;
            if (want_first) {
                auto history = trim(run_process("git", {"log", "--follow", "--diff-filter=A", "--format=%aI", "--", path}));
                if (!history.empty()) first = china_time(history.substr(history.find_last_of('\n') + 1));
            }
            auto last = china_time(run_process("git", {"log", "-1", "--format=%aI", "--", path}));
            return {std::move(first), std::move(last)};
        } catch (const std::exception&) { return {}; }
    }

    void prefetch(const std::map<std::string, bool>& sources) {
        std::vector<std::pair<std::string, bool>> work;
        for (const auto& [path, want_first] : sources)
            if (!saved_history(path, want_first)) work.emplace_back(path, want_first);
        std::vector<History> results(work.size());
        std::vector<std::future<void>> workers;
        std::atomic<std::size_t> next{0};
        for (std::size_t i = 0; i < std::min<std::size_t>(4, work.size()); ++i) {
            workers.push_back(std::async(std::launch::async, [&] {
                for (;;) {
                    const auto index = next.fetch_add(1, std::memory_order_relaxed);
                    if (index >= work.size()) break;
                    const auto& [path, want_first] = work[index];
                    results[index] = read_history(path, want_first);
                }
            }));
        }
        for (auto& worker : workers) worker.get();
        for (std::size_t i = 0; i < work.size(); ++i) fetched.emplace(work[i].first, std::move(results[i]));
    }

    History git_times(const std::string& path, bool want_first) {
        if (const auto* old = saved_history(path, want_first)) {
            ++time_hits;
            times[path] = *old;
            return {want_first ? china_time((*old)[0].get_ref<const std::string&>()) : "",
                    china_time((*old)[1].get_ref<const std::string&>())};
        }
        const auto fetched_time = fetched.find(path);
        auto result = fetched_time == fetched.end() ? read_history(path, want_first) : fetched_time->second;
        if (!result.second.empty() && (!want_first || !result.first.empty())) {
            times[path] = Json::array({result.first.empty() ? Json(nullptr) : Json(result.first), result.second});
        }
        if (!want_first) result.first.clear();
        return result;
    }

    void save(const fs::path& path) const {
        if (path.empty()) return;
        const Json data{{"head", head}, {"git_config", git_config}, {"renderer", DASHBOARD_RENDERER_ID},
                        {"html", rendered}, {"times", times}};
        write_atomic(path, data.dump());
        std::cout << "Daily cache reused " << render_hits << " rendered bodies and " << time_hits << " Git timestamps\n";
    }
};

void warn(const fs::path& path, const std::string& message) {
    std::cerr << path_text(path) << ": " << message << '\n';
}

void search_page(const fs::path& output, const std::string& filename, const Page& report,
                 const std::string& redirect, const Metadata& metadata) {
    write_text(output / "_index-pages" / (filename + ".html"),
               page(false, report.title, report.body, redirect, metadata));
}

bool stage_exists(const Json& stages, const std::string& stage) {
    return std::any_of(stages.begin(), stages.end(), [&](const Json& row) { return row.at("id") == stage; });
}

Json build_showcase(const BuildOptions& options, const Json& stages) {
    std::map<std::string, Page> pages;
    std::map<std::string, std::string> statuses;
    for (const auto& path : files_with_suffix(options.root / "content/showcase", ".md")) {
        try {
            const auto doc = load_document(path);
            const auto stage = trim(string_or(doc.metadata, "stage"));
            if (!stage_exists(stages, stage)) {
                warn(path, "invalid showcase stage");
                continue;
            }
            pages[stage] = {stage, string_or(doc.metadata, "title"), render_markdown(doc.body), stage};
            statuses[stage] = string_or(doc.metadata, "status", "planned");
        } catch (const std::exception& error) { warn(path, error.what()); }
    }

    auto entries = array;
    for (const auto& stage : stages) {
        const auto id = stage.at("id").get<std::string>();
        const auto label = stage.at("label").get<std::string>();
        auto entry = pages.find(id);
        Page report = entry != pages.end() ? entry->second :
            Page{id, label, "<h1>" + label + "</h1>\n<p>示例内容,待替换。该阶段暂无正式 Markdown 文档。</p>", id};
        if (report.title.empty()) report.title = label;
        const auto path = "showcase/" + id + ".html";
        write_text(options.output / fs::u8path(path), report.body);
        search_page(options.output, "showcase-" + id, report, "../#/showcase/" + id, {{"stage", id}, {"type", "showcase"}});
        entries.push_back({{"id", id}, {"label", label}, {"title", report.title},
                           {"status", entry != pages.end() ? statuses.at(id) : "planned"},
                           {"order", entries.size() + 1}, {"path", path}});
    }
    write_text(options.output / "showcase/index-data.json", entries.dump(2));
    return entries;
}

Json build_daily(const BuildOptions& options, const Json& stages, ReleaseCache& cache) {
    const auto directory = options.root / "content/daily";
    auto entries = array;
    std::set<std::string> ids;
    std::set<std::string> names;
    const auto paths = files_with_suffix(directory, ".md");
    for (const auto& path : paths)
        if (!ends_with(path_text(path), ".show.md")) names.insert(path_text(path.stem()));
    std::set<std::string> named_sources;
    std::map<fs::path, Document> documents;
    std::map<std::string, bool> time_sources;
    for (const auto& path : paths) {
        const auto stem = path_text(path.stem());
        if (!valid_day(stem)) continue;
        try {
            auto doc = load_document(path);
            time_sources[path_text(path.lexically_relative(options.root))] = china_time(string_or(doc.metadata, "published")).empty();
            const auto source = string_or(doc.metadata, "show_source", stem + ".show.html");
            auto show = directory / (stem + ".show.md");
            if (validate_daily_source(path_text(directory), source) == DailySourceStatus::valid &&
                fs::exists(directory / fs::u8path(source))) show = directory / fs::u8path(source);
            if (fs::exists(show)) time_sources.try_emplace(path_text(show.lexically_relative(options.root)), false);
            documents.emplace(path, std::move(doc));
        } catch (const std::exception& error) { warn(path, error.what()); }
    }
    const auto history_start = Clock::now();
    cache.prefetch(time_sources);
    report_time("Daily Git times", history_start);
    for (const auto& path : paths) {
        const auto name = path_text(path.filename());
        if (ends_with(name, ".show.md")) {
            if (!names.count(name.substr(0, name.size() - 8))) warn(path, "showcase has no daily document");
            continue;
        }
        const auto key = path_text(path.stem());
        if (!valid_day(key)) {
            warn(path, "invalid daily document date");
            continue;
        }
        const auto relative = "content/daily/" + name;
        const auto document = documents.find(path);
        if (document == documents.end()) continue;
        const auto& doc = document->second;
        const auto named_source = string_or(doc.metadata, "show_source");
        if (!named_source.empty()) named_sources.insert(named_source);
        const auto frontmatter_date = string_or(doc.metadata, "date");
        if (!frontmatter_date.empty() && (frontmatter_date.size() < 10 || frontmatter_date.substr(0, 10) != key))
            warn(path, "frontmatter date differs from the filename");

        const auto id = string_or(doc.metadata, "report_id", key);
        static const std::regex valid_id("[a-zA-Z0-9_-]{1,64}");
        if (!std::regex_match(id, valid_id) || id == "__proto__" || id == "constructor" || id == "prototype" ||
            !ids.insert(id).second) throw std::runtime_error(name + ": invalid or duplicate report_id");
        auto stage = string_or(doc.metadata, "stage", "unclassified");
        if (!stage_exists(stages, stage)) {
            warn(path, "invalid stage, using unclassified");
            stage = "unclassified";
        }
        const auto title = string_or(doc.metadata, "title", markdown_title(doc.body, key));
        const auto html = cache.render(relative, doc.body, !options.daily_cache.empty());
        const auto html_path = "daily/" + key + ".html";
        const auto download_md = "downloads/daily/" + key + ".md";
        const auto download_html = "downloads/daily/" + key + ".html";
        write_text(options.output / html_path, html);
        write_text(options.output / download_md, read_bytes(path));
        write_text(options.output / download_html, page(true, title, html, "", {}));
        search_page(options.output, "daily-" + key, {key, title, html, stage}, "../#/daily/" + key,
                    {{"date", key}, {"stage", stage}, {"type", "daily"}});

        const auto override = china_time(string_or(doc.metadata, "published"));
        const auto [first, last] = cache.git_times(relative, override.empty());
        const auto published = !override.empty() ? override : !first.empty() ? first : mtime(path);
        const auto updated = last.empty() ? mtime(path) : last;
        const auto time_source = !override.empty() ? "frontmatter" : first.empty() ? "mtime" : "git";

        auto show_html = directory / (key + ".show.html");
        const auto show_md = directory / (key + ".show.md");
        if (!named_source.empty()) {
            if (validate_daily_source(path_text(directory), named_source) != DailySourceStatus::valid)
                throw std::runtime_error(name + ": invalid show_source " + named_source);
            show_html = directory / fs::u8path(named_source);
        }
        std::string show_type, show_path;
        fs::path show_file;
        if (fs::exists(show_html)) {
            if (fs::exists(show_md)) warn(path, "both show formats exist, using HTML");
            show_type = "html";
            show_file = show_html;
            const auto rel = show_html.lexically_relative(directory);
            show_path = "daily/" + path_text(rel);
            std::string prefix = "../";
            for (const auto& component : rel.parent_path()) if (!component.empty()) prefix += "../";
            write_text(options.output / fs::u8path(show_path), runtime_html(read_text(show_html), prefix));
        } else if (fs::exists(show_md)) {
            Document show;
            bool loaded = false;
            try { show = load_document(show_md); loaded = true; }
            catch (const std::exception& error) { warn(show_md, error.what()); }
            if (loaded) {
                show_type = "md";
                show_file = show_md;
                show_path = "daily/" + key + ".show.html";
                const auto body = daily_scenes(cache.render("content/daily/" + key + ".show.md", show.body,
                                                             !options.daily_cache.empty()));
                write_text(options.output / show_path, body);
                if (!body.empty())
                    search_page(options.output, "daily-" + key + "-show",
                                {key, string_or(show.metadata, "title", key), body, stage},
                                "../#/daily/" + key + "/show",
                                {{"date", key}, {"stage", stage}, {"type", "daily"}, {"view", "展示"}});
            }
        }

        Json show_stamp = nullptr, show_time_source = nullptr;
        if (!show_file.empty()) {
            const auto [unused, show_last] = cache.git_times(path_text(show_file.lexically_relative(options.root)), false);
            show_stamp = show_last.empty() ? mtime(show_file) : show_last;
            show_time_source = show_last.empty() ? "mtime" : "git";
        }

        entries.push_back({
            {"id", id}, {"date", key}, {"title", title}, {"stage", stage},
            {"summary", string_or(doc.metadata, "summary")}, {"path", html_path},
            {"published_at", published}, {"updated_at", updated}, {"time_source", time_source},
            {"has_show", !show_type.empty()}, {"show_type", show_type.empty() ? Json(nullptr) : Json(show_type)},
            {"show_path", show_path.empty() ? Json(nullptr) : Json(show_path)},
            {"show_allow_downloads", json_or(doc.metadata, "show_allow_downloads", false) == true},
            {"show_updated_at", show_stamp}, {"show_time_source", show_time_source},
            {"download_md_path", download_md}, {"download_html_path", download_html}
        });
    }
    for (const auto& path : files_with_suffix(directory, ".show.html")) {
        const auto name = path_text(path.filename());
        if (!names.count(name.substr(0, name.size() - 10)) && !named_sources.count(name))
            warn(path, "showcase has no daily document");
    }
    std::reverse(entries.begin(), entries.end());
    return entries;
}

fs::path installed_pagefind(const fs::path& root) {
#if defined(_WIN32)
    constexpr auto platform = "windows";
    constexpr auto suffix = ".exe";
#elif defined(__APPLE__)
    constexpr auto platform = "darwin";
    constexpr auto suffix = "";
#elif defined(__FreeBSD__)
    constexpr auto platform = "freebsd";
    constexpr auto suffix = "";
#else
    constexpr auto platform = "linux";
    constexpr auto suffix = "";
#endif
#if defined(_M_ARM64) || defined(__aarch64__)
    constexpr auto arch = "arm64";
#else
    constexpr auto arch = "x64";
#endif
    const auto directory = root / "node_modules/@pagefind" / (std::string(platform) + '-' + arch) / "bin";
    for (const auto* name : {"pagefind_extended", "pagefind"}) {
        const auto binary = directory / (std::string(name) + suffix);
        if (fs::is_regular_file(binary)) return binary;
    }
    throw std::runtime_error("Pagefind is missing. Run npm ci or pass --pagefind with an installed binary.");
}

void run_pagefind(const BuildOptions& options) {
    const auto binary = options.pagefind.empty() ? installed_pagefind(options.root) : options.pagefind;
    std::cout << run_process(path_text(binary), {"--site", path_text(options.output)});
    if (!fs::is_regular_file(options.output / "pagefind/pagefind-entry.json") ||
        !fs::is_regular_file(options.output / "pagefind/pagefind-ui.js"))
        throw std::runtime_error("Pagefind did not produce a complete index");
}
}

std::string runtime_html(std::string html, const std::string& prefix) {
    auto lowercase = html;
    std::transform(lowercase.begin(), lowercase.end(), lowercase.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    static const std::regex config(R"(^\s*window\.MathJax\s*=)", std::regex::icase);
    static const std::regex source(R"re(\bsrc=["'][^"']*mathjax[^"']*["'])re", std::regex::icase);
    std::size_t start = 0;
    for (auto pos = lowercase.find("<script"); pos != std::string::npos; pos = lowercase.find("<script", start)) {
        if (pos + 7 >= lowercase.size() || (lowercase[pos + 7] != '>' && !std::isspace(static_cast<unsigned char>(lowercase[pos + 7])))) {
            start = pos + 7;
            continue;
        }
        const auto tag = lowercase.find('>', pos + 7);
        const auto end = lowercase.find("</script>", tag);
        if (tag == std::string::npos || end == std::string::npos) break;
        const auto content = std::string_view(html).substr(tag + 1, end - tag - 1);
        const auto attributes = std::string_view(html).substr(pos + 7, tag - pos - 7);
        const auto last = content.find_last_not_of(" \r\n\t");
        const auto trimmed = content.find_first_not_of(" \r\n\t");
        if ((last != std::string_view::npos && content[last] == ';' &&
             std::regex_search(content.begin() + trimmed, content.begin() + std::min(trimmed + 128, content.size()), config)) ||
            (trimmed == std::string_view::npos && std::regex_search(attributes.begin(), attributes.end(), source))) {
            html.erase(pos, end + 9 - pos);
            lowercase.erase(pos, end + 9 - pos);
            start = pos;
        } else start = end + 9;
    }
    const std::string injection = R"(
<script>
  window.MathJax = {
    tex: {
      inlineMath: [['$', '$'], ['\\(', '\\)']],
      displayMath: [['$$', '$$'], ['\\[', '\\]']],
      processEscapes: true
    },
    svg: {fontCache: 'global'},
    startup: {typeset: false}
  };
</script>
)" + std::string("<script defer src=\"") + prefix + "vendor/mathjax/tex-svg.js\"></script>\n" +
    "<script defer src=\"" + prefix + "vendor/mermaid/mermaid.min.js\"></script>\n" +
    "<script defer src=\"" + prefix + R"(js/content-enhance.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    window.ContentEnhancer?.enhance(document);
  });
</script>
)";
    const auto head = lowercase.find("</head>");
    html.insert(head == std::string::npos ? 0 : head, injection);
    return html;
}

void build_dashboard(const BuildOptions& options) {
    const auto now = china_time(std::time(nullptr));
    auto version = options.asset_version.empty() ? now.substr(0, 19) : options.asset_version;
    version.erase(std::remove_if(version.begin(), version.end(),
                                 [](char c) { return c < '0' || c > '9'; }), version.end());
    const auto asset_start = Clock::now();
    safe_output(options);
    copy_assets(options);
    report_time("Assets and output preparation", asset_start);
    const auto index = options.output / "index.html";
    write_text(index, std::regex_replace(read_text(index), std::regex(R"(\?v=\d+)"), "?v=" + version));

    const auto config = read_json(options.root / "config.json");
    const auto& stages = config.at("stages");
    ReleaseCache cache(options.daily_cache);
    const auto report_start = Clock::now();
    const auto showcase = build_showcase(options, stages);
    const auto daily = build_daily(options, stages, cache);
    const auto journal = build_journal(options, stages, daily);
    for (const auto& report : journal.pages)
        search_page(options.output, "journal-" + report.key, report, "../#/journal/" + report.key,
                    {{"date", report.key}, {"type", "journal"}});

    const auto tags = read_json(options.tags.empty() ? options.root / "content/report-tags.json" : options.tags);
    if (json_or(tags, "schemaVersion", 0) != 1 || !json_or(tags, "tags", nullptr).is_array() ||
        !json_or(tags, "assignments", nullptr).is_object()) throw std::runtime_error("invalid report tags snapshot");
    const auto stamp = options.build_time.empty() ? china_time(std::time(nullptr)) : options.build_time;
    const Json manifest{{"built_at", stamp}, {"site_title", config.at("site_title")}, {"stages", stages},
                        {"showcase", showcase}, {"daily", daily}, {"report_tags", tags},
                        {"journal", journal.entries}, {"chains", journal.chains}};
    write_text(options.output / "manifest.json", manifest.dump(2));
    write_text(options.output / "_headers", "/*\n  X-Robots-Tag: noindex, nofollow\n  X-Frame-Options: DENY\n");
    write_text(options.output / "robots.txt", "User-agent: *\nDisallow: /\n");
    report_time("Reports, journal, and manifests", report_start);
    run_pagefind(options);
    cache.save(options.daily_cache);
    std::cout << "Built " << daily.size() << " daily reports, " << showcase.size() << " stages and "
              << journal.entries.size() << " journal days in " << path_text(options.output) << '\n';
}
}
