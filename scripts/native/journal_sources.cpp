#include <json.hpp>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace {
namespace fs = std::filesystem;
using Json = nlohmann::json;
using Arguments = std::vector<std::string>;

std::string utf8_path(const fs::path& path) {
    const auto value = path.u8string();
    return {value.begin(), value.end()};
}

#ifdef _WIN32
class Handle {
public:
    explicit Handle(HANDLE value) : value_(value) {}
    Handle(const Handle&) = delete;
    ~Handle() { close(); }
    HANDLE get() const { return value_; }
    void close() {
        if (value_) CloseHandle(value_);
        value_ = nullptr;
    }
private:
    HANDLE value_;
};

std::wstring quoted(const std::wstring& value) {
    std::wstring result = L"\"";
    std::size_t slashes = 0;
    for (auto character : value) {
        if (character == L'\\') { ++slashes; continue; }
        result.append(character == L'\"' ? slashes * 2 + 1 : slashes, L'\\');
        result += character;
        slashes = 0;
    }
    result.append(slashes * 2, L'\\');
    return result + L'\"';
}

std::string git_output(const Arguments& args) {
    std::wstring command = L"git.exe";
    for (const auto& arg : args) command += L' ' + quoted(fs::u8path(arg).wstring());
    SECURITY_ATTRIBUTES attributes{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    HANDLE reader = nullptr, writer = nullptr;
    if (!CreatePipe(&reader, &writer, &attributes, 0)) throw std::runtime_error("cannot open Git pipe");
    Handle read_end(reader), write_end(writer);
    if (!SetHandleInformation(read_end.get(), HANDLE_FLAG_INHERIT, 0))
        throw std::runtime_error("cannot configure Git pipe");
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = write_end.get();
    startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    PROCESS_INFORMATION child{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
            nullptr, nullptr, &startup, &child)) throw std::runtime_error("cannot start Git");
    Handle process(child.hProcess), thread(child.hThread);
    write_end.close();
    std::string output;
    char bytes[8192];
    DWORD count = 0;
    while (ReadFile(read_end.get(), bytes, sizeof(bytes), &count, nullptr) && count)
        output.append(bytes, count);
    if (GetLastError() != ERROR_BROKEN_PIPE) throw std::runtime_error("cannot read Git output");
    DWORD status = 1;
    if (WaitForSingleObject(process.get(), INFINITE) != WAIT_OBJECT_0
            || !GetExitCodeProcess(process.get(), &status) || status)
        throw std::runtime_error("Git check failed: " + args.at(2));
    return output;
}
#else
std::string git_output(const Arguments& args) {
    char program[] = "git";
    std::vector<char*> argv{program};
    for (const auto& arg : args) argv.push_back(const_cast<char*>(arg.c_str()));
    argv.push_back(nullptr);
    int pipes[2];
    if (pipe(pipes) != 0) throw std::runtime_error("cannot open Git pipe");
    posix_spawn_file_actions_t actions;
    int status = posix_spawn_file_actions_init(&actions);
    pid_t child = -1;
    if (!status) {
        status = posix_spawn_file_actions_addclose(&actions, pipes[0]);
        if (!status) status = posix_spawn_file_actions_adddup2(&actions, pipes[1], STDOUT_FILENO);
        if (!status) status = posix_spawn_file_actions_addclose(&actions, pipes[1]);
        if (!status) status = posix_spawnp(&child, program, &actions, nullptr, argv.data(), environ);
        posix_spawn_file_actions_destroy(&actions);
    }
    close(pipes[1]);
    if (status) { close(pipes[0]); throw std::runtime_error("cannot start Git"); }
    std::string output;
    char bytes[8192];
    ssize_t count;
    do {
        count = read(pipes[0], bytes, sizeof(bytes));
        if (count > 0) output.append(bytes, static_cast<std::size_t>(count));
    } while (count > 0 || (count < 0 && errno == EINTR));
    close(pipes[0]);
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    if (count < 0 || waited < 0 || !WIFEXITED(status) || WEXITSTATUS(status))
        throw std::runtime_error("Git check failed: " + args.at(2));
    return output;
}
#endif

Json json_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open " + utf8_path(path));
    return Json::parse(input);
}

Json dates_in(const Json& rows) {
    std::set<std::string> dates;
    for (const auto& row : rows) dates.insert(row.at("date").get<std::string>());
    return Json(dates);
}

std::string document_stage(const std::string& path, const std::string& title) {
    if (("/" + path).find("/PLAN/") != std::string::npos || path.find("/prompt/") != std::string::npos)
        return "构思（计划文本）";
    static const std::vector<std::pair<std::regex, std::string>> stages = {
        {std::regex("构思|提案|可行性|研判|研究|文献|证据核查"), "构思（研究材料）"},
        {std::regex("验收|核验|验证|审计|审查|复核|诊断"), "验收（检查记录）"},
        {std::regex("启动|运行|续跑|续算|暂停|恢复|完成|交付"), "运行（过程记录）"},
        {std::regex("实现|实施|修复|提速|优化|重构|整改"), "实施（工程记录）"},
    };
    for (const auto& [pattern, label] : stages) if (std::regex_search(title, pattern)) return label;
    return "资料整理";
}

using ChainNames = std::map<std::string, std::string>;

std::string join_chains(const Json& chains, const ChainNames& names) {
    std::string result;
    for (const auto& chain : chains) {
        if (!result.empty()) result += "、";
        result += names.at(chain.get<std::string>());
    }
    return result;
}

std::string markdown_title(std::string title) {
    for (std::size_t i = 0; (i = title.find('|', i)) != std::string::npos; ) {
        title.replace(i, 1, "／");
        i += std::string_view("／").size();
    }
    return title;
}

void write_text(const fs::path& path, const std::string& content) {
    std::ofstream file(path, std::ios::binary);
    file.exceptions(std::ios::badbit | std::ios::failbit);
    file << content;
    file.close();
}

struct JournalDay {
    Json sessions = Json::array();
    Json documents = Json::array();
};

int register_sources(const fs::path& root, const fs::path& input, const fs::path& output) {
    const auto ledger = json_file(input / "dispositions.json");
    const auto documents = json_file(input / "document-review.json");
    const auto sessions = json_file(input / "session-review.json");
    const auto titles = json_file(input / "session-titles.json");
    const auto decisions = json_file(output / "review-decisions.json");
    const auto chains = json_file(root / "content/chains.json");

    ChainNames names;
    for (const auto& chain : chains.at("chains")) names[chain.at("id").get<std::string>()] = chain.at("label").get<std::string>();
    const ChainNames topics = {{"behavior-design", "B/C/D/V算法行为构思与可行性研究"},
        {"fund-research", "量化私募与NEXT产品研究"}, {"model-methods", "模型协议、标签、损失函数与评价口径"},
        {"strategy-research", "股票池、资金分配与成交假设"}, {"mechanism-precheck", "C系列候选机制的分布预检"},
        {"research-code", "研究仓代码结构审查与整改"}};
    for (const auto& [key, label] : topics) names[key] = label;
    std::map<std::string, const Json*> files;
    Json counts, dispositions = Json::object();
    for (const auto* field : {"files", "sessions", "messages", "commits", "actions"}) counts[field] = ledger.at(field).size();
    for (const auto& file : ledger.at("files")) {
        files[file.at("id").get<std::string>()] = &file;
        const auto disposition = file.at("disposition").get<std::string>();
        dispositions[disposition] = dispositions.value(disposition, std::size_t{}) + 1;
    }

    Json sources = Json::array();
    std::map<std::string, std::size_t> document_index;
    std::map<std::string, JournalDay> days;
    for (const auto& document : documents) {
        const auto id = document.at("id").get<std::string>();
        const auto& route = decisions.at("documents").at(id);
        if (route.at("disposition") == "excluded") continue;
        const auto& writes = files.at(id)->at("write_evidence");
        const auto dates = dates_in(writes);
        Json source;
        for (const auto* field : {"id", "source", "path", "title", "sha256", "git_state", "filename_dates"})
            source[field] = document.at(field);
        source.update(Json{{"chains", route.at("chains")}, {"disposition", route.at("disposition")},
            {"stage", document_stage(document.at("path").get<std::string>(), document.at("title").get<std::string>())},
            {"write_dates", dates},
            {"write_evidence", writes}, {"git_dates", dates_in(document.at("git_history"))},
            {"date_status", dates.empty() ? "no-verified-write-time" : "raw-write-receipt"}});
        document_index[id] = sources.size();
        sources.push_back(std::move(source));
        for (const auto& day : dates) days[day.get<std::string>()].documents.push_back(id);
    }

    static const std::regex private_title("密码|password|token|私钥|https?://", std::regex::icase);
    for (const auto& session : sessions) {
        const auto id = session.at("session_id").get<std::string>();
        const auto key = session.at("platform").get<std::string>() + ':' + id;
        const auto& route = decisions.at("sessions").at(key);
        if (route.at("disposition") != "research-related") continue;
        const auto candidate = titles.find(id);
        auto title = candidate == titles.end() || candidate->is_null() ? std::string{} : candidate->get<std::string>();
        if (title.empty() || std::regex_search(title, private_title)) title = join_chains(route.at("chains"), names);
        std::map<std::string, Json> by_date;
        for (const auto& message : session.at("users")) {
            by_date[message.at("date").get<std::string>()].push_back(Json{{"line", message.at("line")},
                {"sha256", message.at("line_sha256")}, {"time", message.at("timestamp")},
                {"kind", message.value("evidence_kind", std::string("message"))}});
        }
        const auto date_chains = route.value("date_chains", Json::object());
        for (const auto& [day, entries] : by_date) {
            days[day].sessions.push_back(Json{{"id", key}, {"title", title},
                {"chains", date_chains.value(day, route.at("chains"))}, {"user_lines", entries}});
        }
    }

    static const std::regex date_format("[0-9]{4}-[0-9]{2}-[0-9]{2}");
    Json day_register = Json::object();
    std::map<std::string, std::string> day_pages;
    for (const auto& [day, data] : days) {
        if (!std::regex_match(day, date_format)) throw std::invalid_argument("invalid journal evidence date");
        day_register[day] = {{"sessions", data.sessions}, {"documents", data.documents}};
        std::ostringstream text;
        text << "# " << day << " 原始来源登记\n\n"
            "日期来自消息自身时间和文件写入回执，均换算为北京时间。材料标题日期、Git入库日期分别保留在 source-register.json。\n\n"
            "会话表证明当时有这些要求、讨论或决定。阶段栏说明材料用途；“运行记录”“验收记录”不表示已经运行成功或验收通过，具体结论须读对应正文与收据。\n\n"
            "## 会话\n\n| 会话与内容定位 | 研究去向 | 当日原始消息行号 |\n|---|---|---|\n";
        for (const auto& session : data.sessions) {
            text << "| " << markdown_title(session.at("title").get<std::string>()) << " · `" << session.at("id").get<std::string>()
                 << "` | " << join_chains(session.at("chains"), names) << " | ";
            bool first = true;
            for (const auto& line : session.at("user_lines")) {
                if (!first) text << ", ";
                first = false;
                text << line.at("line");
                if (line.at("kind") == "automation-message") text << "（自动监控）";
            }
            text << " |\n";
        }
        text << "\n## 已匹配写入回执的材料\n\n| 材料 | 阶段 | 去向 | 内容SHA-256 |\n|---|---|---|---|\n";
        for (const auto& id : data.documents) {
            const auto& item = sources.at(document_index.at(id.get<std::string>()));
            text << "| " << markdown_title(item.at("title").get<std::string>()) << " · `" << item.at("source").get<std::string>()
                 << ':' << item.at("path").get<std::string>() << "` | " << item.at("stage").get<std::string>()
                 << " | " << join_chains(item.at("chains"), names) << " | `" << item.at("sha256").get<std::string>() << "` |\n";
        }
        if (data.documents.empty()) text << "| 本日没有可单独匹配的写入回执；不据此认定没有工作 | — | 见上表原始会话 | — |\n";
        text << "\n原始全文和绝对路径保留在本机 data/journal-rebuild-2026-10-21/；公开清单仅保留必要定位和哈希。\n";
        day_pages.emplace(day, text.str());
    }

    std::ostringstream pending;
    pending << "# 缺少独立写入时间的材料\n\n以下材料均已登记研究去向。文件名、正文自述日期和Git入库日期不能单独证明实际写入日；不为此补造日点。相同目标若有原始会话，按会话自身日期入日志。\n\n";
    std::size_t pending_count = 0;
    for (const auto& item : sources) {
        if (!item.at("write_dates").empty()) continue;
        ++pending_count;
        pending << "- `" << item.at("source").get<std::string>() << ':' << item.at("path").get<std::string>() << "` → ";
        bool first = true;
        for (const auto& chain : item.at("chains")) {
            if (!first) pending << ", ";
            first = false;
            pending << chain.get<std::string>();
        }
        pending << "；材料ID `" << item.at("id").get<std::string>() << "`。\n";
    }
    if (!pending_count) pending << '\n';

    const auto day_root = output / "days";
    fs::create_directories(day_root);
    const Json registration = {{"schema_version", 1}, {"scope", "固定快照内的逐材料、逐会话登记；不代表重新运行研究计算"},
        {"documents", sources}, {"days", day_register}, {"counts", counts}, {"file_dispositions", dispositions}};
    write_text(output / "source-register.json", registration.dump(2) + '\n');
    for (const auto& [day, text] : day_pages) write_text(day_root / (day + ".md"), text);
    write_text(output / "undated-materials.md", pending.str());
    std::cout << "逐日来源登记 " << days.size() << " 材料 " << sources.size() << " 缺独立写入时间 " << pending_count << '\n';
    return 0;
}

std::size_t git_line_count(std::string_view text) {
    // The audit counts Git blob lines, including a final line with no newline.
    constexpr std::string_view ascii_breaks = "\n\v\f\x1c\x1d\x1e";
    std::size_t lines = 0, width = 0;
    for (std::size_t i = 0; i < text.size(); i += width ? width : 1) {
        const auto rest = text.substr(i);
        if (rest.substr(0, 2) == "\r\n" || rest.substr(0, 2) == "\xc2\x85") width = 2;
        else if (rest.substr(0, 3) == "\xe2\x80\xa8" || rest.substr(0, 3) == "\xe2\x80\xa9") width = 3;
        else width = rest.front() == '\r' || ascii_breaks.find(rest.front()) != std::string_view::npos ? 1 : 0;
        lines += width != 0;
    }
    return lines + (!text.empty() && width == 0);
}

Json verify(const fs::path& root) {
    const auto manifest = json_file(root / "docs/journal-review/audit-2026-10-21/remediation-actions.json");
    const auto config = json_file(root / "scripts/journal_repos.json");
    std::map<std::string, Json> repos;
    Json revisions = Json::object();
    for (const auto& repo : config.at("repos")) {
        const auto name = repo.at("name").get<std::string>();
        repos[name] = repo;
        revisions[name] = repo.at("revision");
    }
    std::set<std::pair<std::string, std::string>> verified;
    std::map<std::string, std::size_t> file_lengths;
    Json checked = Json::array();
    for (const auto& [key, ref] : manifest.at("source_catalog").items()) {
        const auto repo = ref.at("repo").get<std::string>();
        const auto revision = ref.at("revision").get<std::string>();
        const auto& spec = repos.at(repo);
        const auto folder = utf8_path(fs::weakly_canonical(root / fs::u8path(spec.at("path").get<std::string>())));
        if (verified.emplace(repo, revision).second)
            git_output({"-C", folder, "merge-base", "--is-ancestor", revision, spec.at("revision").get<std::string>()});
        if (ref.at("kind") == "file") {
            const auto relative = ref.at("path").get<std::string>();
            const auto allowed = spec.value("only_under", std::string{});
            if (relative.compare(0, allowed.size(), allowed) != 0) throw std::runtime_error(key + ": 超出父仓白名单");
            const auto object = revision + ':' + relative;
            const auto [length, fresh] = file_lengths.try_emplace(repo + '\n' + object, 0);
            if (fresh) length->second = git_line_count(git_output({"-C", folder, "show", object}));
            const auto low = ref.at("lines").at(0).get<std::int64_t>();
            const auto high = ref.at("lines").at(1).get<std::int64_t>();
            if (low < 1 || high < low || static_cast<std::uint64_t>(high) > length->second)
                throw std::runtime_error(key + ": 行号超出文件范围");
        } else {
            git_output({"-C", folder, "cat-file", "-e", revision + "^{commit}"});
        }
        checked.push_back(key);
    }
    const auto utc = std::time(nullptr);
    std::tm time{};
#ifdef _WIN32
    if (gmtime_s(&time, &utc) != 0) throw std::runtime_error("cannot format audit time");
#else
    if (!gmtime_r(&utc, &time)) throw std::runtime_error("cannot format audit time");
#endif
    char timestamp[32];
    std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S+00:00", &time);
    return {{"checked_at_utc", timestamp}, {"passed", true}, {"source_count", checked.size()},
        {"source_ids", checked}, {"revisions", revisions},
        {"scope", "Git对象、祖先关系、文件行号、父仓白名单；不表示服务器现场运行验收。"}};
}

int audit(const std::vector<fs::path>& args) {
    try {
        if (args.size() >= 3 && args[0] == "--root" && args[2] == "--register") {
            const auto& root = args[1];
            auto input = root / "data/journal-rebuild-2026-10-21";
            auto output = root / "docs/journal-review/rebuild-2026-10-21";
            for (std::size_t i = 3; i < args.size(); i += 2) {
                if (i + 1 == args.size() || (args[i] != "--input" && args[i] != "--output"))
                    throw std::invalid_argument("journal_sources --root ROOT --register [--input DIR] [--output DIR]");
                (args[i] == "--input" ? input : output) = args[i + 1];
            }
            return register_sources(root, input, output);
        }
        if (args.size() != 2 && args.size() != 4) throw std::invalid_argument("journal_sources --root ROOT [--output FILE]");
        if (args[0] != "--root" || (args.size() == 4 && args[2] != "--output"))
            throw std::invalid_argument("journal_sources --root ROOT [--output FILE]");
        const auto result = verify(args[1]);
        if (args.size() == 4) {
            std::ofstream output(args[3], std::ios::binary);
            output.exceptions(std::ios::badbit | std::ios::failbit);
            output << result.dump(2) << '\n';
            output.close();
        }
        std::cout << "固定原始引用 " << result.at("source_count") << " 项：Git对象、行号及版本包含关系全部通过。\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
}

#ifdef _WIN32
int wmain(int argc, wchar_t** argv) { return audit({argv + 1, argv + argc}); }
#else
int main(int argc, char** argv) { return audit({argv + 1, argv + argc}); }
#endif
