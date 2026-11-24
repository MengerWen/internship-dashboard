#include "dashboard_build.hpp"

#include <algorithm>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <regex>
#include <set>
#include <stdexcept>

namespace dashboard {
namespace {
const auto array = Json::array();
const auto object = Json::object();
const std::set<std::string> fates{"landed", "folded", "parked", "dropped"};

void warn(const std::string& message) {
    std::cerr << "Journal: " << message << '\n';
}

void increment(Json& counts, const std::string& name) {
    counts[name] = counts.value(name, 0) + 1;
}

bool is_hash(const Json& value, std::size_t length) {
    if (!value.is_string()) return false;
    const auto& text = value.get_ref<const std::string&>();
    return text.size() == length && text.find_first_not_of("0123456789abcdef") == std::string::npos;
}

std::size_t characters(std::string_view utf8) {
    return static_cast<std::size_t>(std::count_if(utf8.begin(), utf8.end(),
        [](unsigned char c) { return (c & 0xc0) != 0x80; }));
}

struct Fraction {
    std::int64_t numerator = 0, denominator = 1;

    void add(std::int64_t n, std::int64_t d) {
        constexpr auto limit = std::numeric_limits<std::int64_t>::max();
        const auto common = std::gcd(denominator, d);
        const auto left_scale = d / common;
        const auto right_scale = denominator / common;
        if (denominator > limit / left_scale || numerator > limit / left_scale || n > limit / right_scale ||
            numerator * left_scale > limit - n * right_scale)
            throw std::runtime_error("attribution fraction exceeds integer capacity");
        numerator = numerator * left_scale + n * right_scale;
        denominator *= left_scale;
        const auto divisor = std::gcd(numerator, denominator);
        numerator /= divisor;
        denominator /= divisor;
    }
};

struct Counts {
    Fraction value;
    int direct = 0;
    int shared = 0;
};

Json summarize(const Json& attribution, const std::map<std::string, Json>& chains) {
    auto repos = object;
    auto statuses = object;
    std::set<std::pair<std::string, std::string>> seen;
    std::map<std::string, Counts> totals;
    const std::set<std::string> valid{"assigned", "shared", "pending", "maintenance", "mirror", "excluded"};
    for (const auto& item : attribution.at("items")) {
        const auto status = item.at("status").get<std::string>();
        const auto repo = item.at("repo").get<std::string>();
        if (!valid.count(status)) throw std::runtime_error("unknown attribution status");
        if (!is_hash(item.at("sha"), 40) || !seen.emplace(repo, item.at("sha").get<std::string>()).second)
            throw std::runtime_error("duplicate or invalid commit SHA");
        if (item.at("date") != attribution.at("date")) throw std::runtime_error("commit date differs from attribution day");
        increment(statuses, status);
        increment(repos, repo);
        Fraction sum;
        const auto& shares = item.at("shares");
        for (auto it = shares.begin(); it != shares.end(); ++it) {
            const auto& share = it.value();
            if (!chains.count(it.key()) || !share.at("numerator").is_number_integer() ||
                !share.at("denominator").is_number_integer())
                throw std::runtime_error("invalid attribution chain or share type");
            const auto n = share.at("numerator").get<std::int64_t>();
            const auto d = share.at("denominator").get<std::int64_t>();
            if (n <= 0 || n > d) throw std::runtime_error("commit share is out of range");
            sum.add(n, d);
            auto& total = totals[it.key()];
            total.value.add(n, d);
            ++(shares.size() > 1 ? total.shared : total.direct);
        }
        if (sum.denominator != 1 || sum.numerator != (status == "assigned" || status == "shared" ? 1 : 0))
            throw std::runtime_error("commit shares do not sum to the expected total");
    }
    auto weights = object;
    for (const auto& [name, total] : totals) {
        const auto& value = total.value;
        weights[name] = {{"value", static_cast<double>(value.numerator) / value.denominator},
                         {"direct", total.direct}, {"shared", total.shared},
                         {"numerator", value.numerator}, {"denominator", value.denominator}};
    }
    return {{"total_commits", seen.size()}, {"repos", repos}, {"statuses", statuses}, {"chains", weights}};
}

Json point_evidence(const std::string& day, const std::string& chain, const Json& attribution,
                    const Json& source_day, const std::map<std::string, Json>& documents, const Json& urls) {
    auto commits = object, files = object, sessions = object;
    bool has_code = false;
    static const std::regex code_ext(R"(\.(py|js|mjs|cjs|ts|tsx|jsx|cpp|cc|c|h|rs|sql|ipynb)$)", std::regex::icase);
    for (const auto& item : json_or(attribution, "items", array)) {
        const auto share = json_or(json_or(item, "shares", object), chain, object);
        if (string_or(item, "date") != day || string_or(item, "status") != "assigned" ||
            share.value("numerator", 0) <= 0 || share.value("denominator", 0) <= 0 ||
            !is_hash(json_or(item, "sha", nullptr), 40)) continue;
        const auto repo = string_or(item, "repo");
        const auto sha = item.at("sha").get<std::string>();
        bool code = false;
        for (const auto& path : json_or(item, "paths", array))
            if (std::regex_search(path.get_ref<const std::string&>(), code_ext)) { code = true; break; }
        auto url = string_or(urls, repo);
        if (url.compare(0, 19, "https://github.com/") != 0) url.clear();
        for (auto pos = url.find("{sha}"); pos != std::string::npos; pos = url.find("{sha}", pos + sha.size()))
            url.replace(pos, 5, sha);
        has_code |= code;
        commits[repo + '\0' + sha] = {{"kind", "commit"}, {"title", string_or(item, "subject", sha.substr(0, 8))},
                                       {"url", url}, {"sha", sha}, {"repo", repo}, {"label", code ? "代码提交" : "提交"}};
    }
    const auto source_url = "https://github.com/MengerWen/internship-dashboard/blob/main/"
                            "docs/journal-review/rebuild-2026-10-21/days/" + day + ".md";
    const auto operations = Json::array({"add", "update", "write", "edit"});
    const auto bases = Json::array({"native-file-change", "direct-tool-result", "claude-tool-result", "raw-write-receipt"});
    for (const auto& id : json_or(source_day, "documents", array)) {
        auto it = documents.find(id.get<std::string>());
        if (it == documents.end()) continue;
        const auto& doc = it->second;
        if (!contains(json_or(doc, "chains", array), chain) || string_or(doc, "disposition") != "primary" ||
            !is_hash(json_or(doc, "sha256", nullptr), 64)) continue;
        const auto proofs = json_or(doc, "write_evidence", array);
        const auto proof = std::find_if(proofs.begin(), proofs.end(), [&](const Json& p) {
            return string_or(p, "date") == day && is_hash(json_or(p, "receipt_line_sha256", nullptr), 64) &&
                   contains(operations, json_or(p, "operation", nullptr)) &&
                   (contains(bases, json_or(p, "basis", nullptr)) ||
                    string_or(doc, "date_status") == "confirmed-native-or-direct-receipt");
        });
        if (proof == proofs.end()) continue;
        files[id.get<std::string>()] = {
            {"kind", "document"}, {"id", id}, {"title", string_or(doc, "title", string_or(doc, "path", "文档"))},
            {"path", string_or(doc, "path")}, {"sha256", doc.at("sha256")},
            {"url", source_url + "#已确认写入的材料"}, {"label", "文档写入记录"}
        };
    }
    for (const auto& session : json_or(source_day, "sessions", array)) {
        const auto id = string_or(session, "id");
        if (id.empty() || !contains(json_or(session, "chains", array), chain)) continue;
        for (const auto& line : json_or(session, "user_lines", array)) {
            const auto time = string_or(line, "time");
            if (!is_hash(json_or(line, "sha256", nullptr), 64) || time.find_first_of("Z+-", 11) == std::string::npos ||
                china_time(time).substr(0, 10) != day) continue;
            sessions[id] = {{"kind", "session"}, {"id", id}, {"title", string_or(session, "title", "交流记录")},
                            {"url", source_url + "#会话"}, {"time", time}, {"label", "原始会话登记"}};
            break;
        }
    }
    auto kinds = array, artifacts = array, discussions = array;
    if (has_code) kinds.push_back("代码");
    if (!commits.empty()) kinds.push_back("提交");
    if (!files.empty()) kinds.push_back("文档");
    if (!sessions.empty()) kinds.push_back("会话");
    for (const auto* rows : {&files, &commits, &sessions}) {
        auto& output = rows == &sessions ? discussions : artifacts;
        std::size_t count = 0;
        for (const auto& row : *rows) {
            if (count++ == 2) break;
            output.push_back(row);
        }
    }
    return {{"status", !artifacts.empty() ? "artifact" : !discussions.empty() ? "discussion" : "pending"},
            {"kinds", kinds}, {"commit_count", commits.size()}, {"document_count", files.size()},
            {"session_count", sessions.size()}, {"artifacts", artifacts}, {"discussions", discussions}};
}
}

Journal build_journal(const BuildOptions& options, const Json& stages, const Json& daily) {
    Journal result;
    const auto registry_file = options.root / "content/chains.json";
    if (!fs::exists(registry_file)) return result;
    Json registry;
    try { registry = read_json(registry_file); }
    catch (const std::exception& error) { warn(error.what()); return result; }
    auto tracks = json_or(registry, "tracks", array);
    auto chains = json_or(registry, "chains", array);
    auto handoffs = array;
    std::set<std::string> stage_ids, track_ids;
    std::map<std::string, Json> chain_by_id, report_by_day;
    for (const auto& item : stages) stage_ids.insert(item.at("id").get<std::string>());
    for (auto& track : tracks) {
        const auto id = track.at("id").get<std::string>();
        track_ids.insert(id);
        const auto stage = string_or(track, "stage");
        if (!stage.empty() && !stage_ids.count(stage)) {
            warn("invalid stage for track " + id);
            track["stage"] = nullptr;
        }
        if (std::count_if(chains.begin(), chains.end(), [&](const Json& c) { return string_or(c, "track") == id; }) > 10)
            warn("more than ten chains on track " + id);
    }
    for (auto& chain : chains) {
        const auto id = chain.at("id").get<std::string>();
        if (!track_ids.count(string_or(chain, "track"))) warn("missing track for chain " + id);
        if (!fates.count(string_or(chain, "fate", "landed"))) {
            warn("invalid fate for chain " + id);
            chain["fate"] = "landed";
        }
        chain_by_id[id] = chain;
    }
    for (const auto& report : daily) report_by_day[report.at("date").get<std::string>()] = report;

    const auto edges = Json::array({"延续", "派生", "依赖解除", "收口"});
    for (const auto& edge : json_or(registry, "handoffs", array)) {
        const auto confidence = string_or(edge, "confidence");
        const auto day = string_or(edge, "date");
        if (!chain_by_id.count(string_or(edge, "from")) || !chain_by_id.count(string_or(edge, "to")) ||
            !contains(edges, json_or(edge, "type", nullptr)) ||
            (confidence != "confirmed" && confidence != "inferred") || (!day.empty() && !valid_day(day))) {
            warn("invalid chain handoff: " + edge.dump());
            continue;
        }
        handoffs.push_back(edge);
    }

    const auto directory = options.root / "content/journal";
    std::map<std::string, fs::path> notes;
    std::map<std::string, Json> evidence;
    std::set<std::string> days;
    for (const auto& path : files_with_suffix(directory, ".md")) {
        const auto key = path_text(path.stem());
        if (key.size() == 10 && key[4] == '-' && key[7] == '-') {
            notes[key] = path;
            days.insert(key);
        }
    }
    for (const auto& path : files_with_suffix(directory / "_evidence", ".json")) {
        const auto key = path_text(path.stem());
        try {
            auto ev = read_json(path);
            if (!valid_day(key) || string_or(ev, "date") != key) throw std::runtime_error("date differs from filename");
            evidence.emplace(key, std::move(ev));
            days.insert(key);
        } catch (const std::exception& error) { warn(path_text(path) + ": " + error.what()); }
    }
    const auto register_file = options.root / "docs/journal-review/rebuild-2026-10-21/source-register.json";
    const auto source_register = fs::exists(register_file) ? read_json(register_file) : object;
    const auto source_days = json_or(source_register, "days", object);
    std::map<std::string, Json> source_documents;
    for (const auto& doc : json_or(source_register, "documents", array))
        source_documents[doc.at("id").get<std::string>()] = doc;
    auto fingerprints = object;
    for (const auto& [file, field] : {std::pair{"journal_repos.json", "source_config_sha256"},
                                     std::pair{"journal_attribution_rules.json", "rules_sha256"}}) {
        const auto path = options.root / "scripts" / file;
        if (fs::exists(path)) fingerprints[field] = sha256(json_canonical(read_json(path)));
    }

    for (const auto& day : days) {
        if (!valid_day(day)) { warn("invalid date " + day); continue; }
        auto meta = object;
        std::string body;
        if (const auto it = notes.find(day); it != notes.end()) {
            try {
                auto doc = load_document(it->second);
                meta = std::move(doc.metadata);
                body = render_markdown(doc.body);
            } catch (const std::exception& error) { warn(day + ": " + error.what()); }
            if (string_or(meta, "date", day) != day) warn("frontmatter date differs from " + day);
        }
        auto ev = evidence.count(day) ? evidence.at(day) :
            Json{{"date", day}, {"repos", array}, {"plans", array}, {"reports_published", array}};
        const auto repos = json_or(ev, "repos", array);
        const auto plans = json_or(ev, "plans", array);
        auto subjects = array;
        auto commits = object, urls = object;
        int total = 0;
        for (const auto& repo : repos) {
            const auto name = repo.at("repo").get<std::string>();
            commits[name] = repo.at("commits");
            urls[name] = string_or(repo, "commit_url");
            for (const auto& item : json_or(repo, "items", array)) subjects.push_back(item.at("subject"));
        }
        for (const auto& count : commits) total += count.get<int>();
        const auto headline = string_or(meta, "headline", subjects.empty() ? "待写" : subjects.front().get<std::string>());
        const auto source = string_or(meta, "headline_source", "commit");
        if (source == "written" && characters(headline) > 40) warn(day + " headline exceeds 40 characters");
        auto highlights = json_or(meta, "highlights", array);
        if (highlights.size() > 3) warn(day + " has more than three highlights");
        if (highlights.empty()) {
            if (!plans.empty()) for (const auto& plan : plans) highlights.push_back(plan.at("title"));
            else highlights = subjects;
            if (highlights.size() > 3) highlights.erase(highlights.begin() + 3, highlights.end());
        }

        auto picked = array, confidence = object, chain_notes = object;
        for (const auto& value : json_or(meta, "chains", array)) {
            const auto item = value.is_object() ? value : Json{{"id", value}};
            const auto id = string_or(item, "id");
            if (!chain_by_id.count(id) || contains(picked, id)) { warn(day + " has an invalid or duplicate chain " + id); continue; }
            picked.push_back(id);
            const auto& chain = chain_by_id.at(id);
            const auto fate = string_or(chain, "fate", "landed");
            const auto note = trim(string_or(item, "note"));
            if (characters(note) > 24) warn(day + " chain " + id + " note exceeds 24 characters");
            auto outcome = string_or(item, "outcome", fate);
            if (!fates.count(outcome)) { warn(day + " chain " + id + " outcome is invalid"); outcome = fate; }
            const auto default_note = (outcome == "dropped" || outcome == "parked") && outcome == fate
                ? string_or(chain, "fate_note") : "";
            chain_notes[id] = {{"note", note}, {"outcome", outcome}, {"outcome_note", string_or(item, "outcome_note", default_note)}};
            const auto review = json_or(chain, "review", object);
            const bool pending = review.empty() ? json_or(meta, "chains_reviewed", false) != true :
                contains(json_or(review, "unreviewed_days", array), day);
            confidence[id] = pending ? "inferred" : "confirmed";
        }

        auto covering = array, published = array;
        for (const auto& date : json_or(meta, "reports_covering", json_or(ev, "reports_covering", array))) {
            if (date.is_string() && report_by_day.count(date.get<std::string>())) covering.push_back(date);
            else warn(day + " refers to an unavailable daily report " + date.dump());
        }
        for (const auto& date : json_or(ev, "reports_published", array))
            if (date.is_string() && report_by_day.count(date.get<std::string>())) published.push_back(date);

        Json entry{{"date", day}, {"weekday", weekday(day)}, {"headline", headline}, {"headline_source", source},
                   {"chains", picked}, {"chain_confidence", confidence}, {"chain_notes", chain_notes},
                   {"highlights", highlights}, {"commits", commits}, {"total_commits", total},
                   {"report", covering.empty() ? Json(nullptr) : covering.front()}, {"reports_covering", covering},
                   {"reports_published", published}, {"has_body", !trim(body).empty()},
                   {"evidence_path", "journal/_evidence/" + day + ".json"}};
        const auto attribution_file = directory / "_attribution" / (day + ".json");
        Json attribution = nullptr;
        if (fs::exists(attribution_file)) {
            attribution = read_json(attribution_file);
            if (attribution.at("date") != day || attribution.at("schemaVersion") != 1)
                throw std::runtime_error(day + ": invalid journal attribution date or schema");
            for (auto it = fingerprints.begin(); it != fingerprints.end(); ++it)
                if (json_or(attribution, it.key(), nullptr) != it.value())
                    throw std::runtime_error(day + ": outdated journal attribution fingerprint " + it.key());
            auto summary = summarize(attribution, chain_by_id);
            if (nlohmann::json(summary.at("repos")) != nlohmann::json(commits))
                throw std::runtime_error(day + ": journal attribution differs from collected per-repository counts");
            auto weights = summary.at("chains");
            for (const auto& id : picked)
                if (!weights.contains(id.get_ref<const std::string&>()))
                    weights[id.get<std::string>()] = {{"value", 0}, {"direct", 0}, {"shared", 0}, {"numerator", 0}, {"denominator", 1}};
            summary.erase("chains");
            entry["chain_weights"] = std::move(weights);
            entry["attribution_summary"] = std::move(summary);
        }
        const auto date_notes = json_or(meta, "date_notes", object);
        if (!date_notes.empty()) {
            auto trimmed = object;
            for (auto it = date_notes.begin(); it != date_notes.end(); ++it)
                if (contains(picked, it.key())) trimmed[it.key()] = it.value();
            entry["date_notes"] = std::move(trimmed);
        }
        auto chain_evidence = object;
        for (const auto& id : picked)
            chain_evidence[id.get<std::string>()] = point_evidence(day, id.get<std::string>(), attribution,
                json_or(source_days, day, object), source_documents, urls);
        entry["chain_evidence"] = std::move(chain_evidence);
        result.entries.push_back(entry);

        ev["reports_covering"] = covering;
        ev["reports_published"] = published;
        auto reports = array;
        std::set<std::string> seen;
        for (const auto* dates : {&covering, &published}) {
            for (const auto& date : *dates) {
                if (!seen.insert(date.get<std::string>()).second) continue;
                const auto& report = report_by_day.at(date.get<std::string>());
                reports.push_back({{"date", date}, {"title", report.at("title")}, {"summary", report.at("summary")}});
            }
        }
        ev["reports"] = std::move(reports);
        if (!attribution.is_null()) ev["attribution"] = std::move(attribution);
        write_text(options.output / ("journal/_evidence/" + day + ".json"), ev.dump(2));
        write_text(options.output / ("journal/" + day + ".html"), body);

        std::string search = "<p>" + escape_html(headline) + "</p>";
        auto paragraph = [&](const Json& value) { search += "\n<p>" + escape_html(value.get_ref<const std::string&>()) + "</p>"; };
        for (const auto& highlight : highlights) paragraph(highlight);
        for (const auto& note : chain_notes) paragraph(note.at("note"));
        for (const auto& note : chain_notes) paragraph(note.at("outcome_note"));
        for (const auto& plan : plans) paragraph(plan.at("title"));
        for (const auto& subject : subjects) paragraph(subject);
        result.pages.push_back({day, headline, search + body, ""});
    }

    auto output_chains = array;
    std::map<std::string, std::size_t> lanes;
    for (const auto& track : tracks)
        for (const auto& chain : chains)
            if (json_or(chain, "track", nullptr) == track.at("id")) lanes[chain.at("id").get<std::string>()] = lanes.size();
    for (auto chain : chains) {
        const auto id = chain.at("id").get<std::string>();
        Json first = nullptr, last = nullptr;
        for (const auto& entry : result.entries) if (contains(entry.at("chains"), id)) {
            if (first.is_null()) first = entry.at("date");
            last = entry.at("date");
        }
        chain.erase("review");
        chain.erase("start");
        chain.erase("end");
        chain["start"] = first;
        chain["end"] = last;
        chain["fate"] = string_or(chain, "fate", "landed");
        chain["fate_note"] = string_or(chain, "fate_note");
        chain["lane"] = lanes.count(id) ? Json(lanes.at(id)) : Json(nullptr);
        if (auto target = chain.find("closes_into"); target != chain.end() && target->is_object() && !target->empty()) {
            auto available = array;
            for (const auto& day : json_or(*target, "daily", array))
                if (report_by_day.count(day.get<std::string>())) available.push_back(day);
            (*target)["daily"] = std::move(available);
        }
        output_chains.push_back(std::move(chain));
    }
    result.chains = {{"tracks", tracks}, {"chains", output_chains}, {"handoffs", handoffs}};
    return result;
}
} // namespace dashboard
