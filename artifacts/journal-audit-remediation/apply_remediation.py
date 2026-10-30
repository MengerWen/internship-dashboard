"""本次内容修订的本地工作脚本；不参与站点构建。"""
from __future__ import annotations
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote
import frontmatter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = WORK / "baseline"
R = "9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6"
P = "e63c0d3726d03245724fd15e59ecf8ff0000a825"
D = "0910a201154aa02b6889ad77899943a2eb656d1c"
PREFIX = "26 Summer/❗思瑞投资/"
REPOS = {
    "R": (Path("D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research"), "sirui-quant-research", R),
    "P": (Path("D:/MG/_GitLinked/Quant_Research-Trading"), "Quant_Research-Trading", P),
    "D": (ROOT, "internship-dashboard", D),
}

def git(repo, *args):
    return subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(REPOS[repo][0]), *args], capture_output=True, encoding="utf-8", check=True).stdout

if not BASE.exists():
    BASE.mkdir(parents=True)
    shutil.copy2(ROOT / "content/chains.json", BASE / "chains.json")
    shutil.copytree(ROOT / "content/journal", BASE / "journal")
    shutil.copy2(ROOT / "scripts/journal_repos.json", BASE / "journal_repos.json")

registry = json.loads((BASE / "chains.json").read_text(encoding="utf-8"))
original = copy.deepcopy(registry)
notes = {p.stem: frontmatter.load(p) for p in sorted((BASE / "journal").glob("????-??-??.md"))}
refs = {}
point_refs = collections.defaultdict(list)
extras = collections.defaultdict(list)
date_notes = collections.defaultdict(dict)
actions = []

def source(key, repo, path, start=1, end=None, rev=None, title=None):
    root, name, pin = REPOS[repo]
    rev = rev or pin
    body = git(repo, "show", f"{rev}:{path}")
    lines = body.splitlines()
    stop = min(end or len(lines), len(lines))
    assert 1 <= start <= stop, (key, path, len(lines), start, stop)
    title = title or next((s.lstrip("# ") for s in lines if s.startswith("# ")), Path(path).name)
    refs[key] = {"kind": "file", "repo": name, "revision": rev, "path": path,
                 "lines": [start, stop], "title": title,
                 "url": f"https://github.com/MengerWen/{name}/blob/{rev}/{quote(path, safe='/')}#L{start}-L{stop}"}
    return key

def commit(key, repo, sha, title=None):
    full = git(repo, "rev-parse", sha).strip()
    subprocess.run(["git", "-C", str(REPOS[repo][0]), "merge-base", "--is-ancestor", full, REPOS[repo][2]], check=True)
    refs[key] = {"kind": "commit", "repo": REPOS[repo][1], "revision": full,
                 "title": title or git(repo, "show", "-s", "--format=%s", full).strip(),
                 "url": f"https://github.com/MengerWen/{REPOS[repo][1]}/commit/{full}"}
    return key

# 原始来源均回到固定 Git 对象，不把审阅报告作为研究的自证材料。
late = (ROOT / "docs/journal-review/audit-2026-10-21/late-chains.md").read_text(encoding="utf-8")
for key, repo_name, rev, path, lo, hi in re.findall(r"^\[(R\d+|D\d+)\]: https://github\.com/MengerWen/([^/]+)/blob/([a-f0-9]{40})/([^#\n]+)#L(\d+)-L(\d+)", late, re.M):
    from urllib.parse import unquote
    source(key, "R" if repo_name == "sirui-quant-research" else "D", unquote(path), int(lo), int(hi), rev)

source("S01", "P", PREFIX + "米筐Ricequant/reports/buy_and_hold_report.csv/portfolio.csv", 1, 5, title="米筐示例回测输出")
commit("S02", "P", "b852739ab5018ad30df1972dbbd5f7f96d9f613c", "沪深规则与异常交易监控资料提交")
source("S03", "P", PREFIX + "lv2_snapshot_workspace/README.md", 3, 99, "41a3f9522814fc622e5723b89ae93cc09c27ef17")
source("S04", "P", PREFIX + "lv2_snapshot_workspace/DATA_SUMMARY_for_smartmoney.md", 1, 46)
source("S05", "P", PREFIX + "因子/factor_lab/configs/default.yaml", 1, 20, "94492df7f1e937c20fa9727351ad5ad90326ec7f", "首个因子框架的快照输入配置")
source("S07", "P", PREFIX + "因子/algobench/README.md", 3, 18, "80513f65e40b4c89ef2d2e23b36a75283cfafd59")
source("S09", "P", PREFIX + "因子/algobench/configs/attention13_m202507.yaml", 23, 59, "b4f413755c07c9e482e24b96330197045f125567", "主动关注度与单月评价配置")
source("S10", "R", "PLAN/服务器迁移与Doris数据访问重构总计划_2026-07-15.md", 3, 100)
source("S11", "R", "lv2_snapshot_workspace/src/snapshot/io.py", 1, 205, "9e4260f4425b3b158b6d71fdf7a9b410ace8bf38", "Doris 唯一网关的实际实现")
source("S12", "R", "PLAN/2026-08-06-open5m-2025-2026h1-performance-design.md", 5, 21)
source("S13", "R", "因子/algobench/src/algobench/formal_engine.py", 1, 46, "a214f26e0756739d7aedfe9b0eb909f2c3203ef3", "正式因子引擎实现")
source("S14", "R", "PLAN/2026-07-27-开盘前三分钟连续评分可行性重构实施计划.md", 7, 34)
source("S17", "R", "PLAN/2026-08-02-2026年固定参数全区间因子评价实施计划.md", 5, 43)
source("S18", "R", "PLAN/2026-08-03-fixed-history-through-latest-complete-design.md", 5, 43)
source("S19", "R", "PLAN/2026-10-08-grouped-calibration-bucket-precheck.md", 3, 59)
source("S20", "R", "PLAN/2026-08-04-51个count因子机器学习与结构诊断实施计划.md", 1, 25, "2318d2ff29815213e6f108cb3308629dfa601869", "首次入库的 127 个 total-only 模型计划")
source("S22", "R", "PLAN/2026-09-01-cancel-phase-factor-library-implementation.md", 17, 59)
source("S23", "R", "因子/algobench/src/algobench/ml/data.py", 107, 178, title="模型输入的冻结来源检查")
source("S24", "R", "PLAN/2026-09-09-mechanical-cancel-prescreen.md", 3, 59)
source("S25", "R", "PLAN/2026-08-19-open5m-cancel-lag-distribution-design.md", 5, 85)
source("S26", "R", "reports/2026-09/2026-09-06-cancel-phase-601d-completion-evidence/CANCEL_PHASE_2024_2026Q2_RESULT.json", 1, 25, title="相位 601 日业务结果")
source("S27", "R", "reports/2026-09/2026-09-11-mechanical-cancel-final-evidence/PRESCREEN_RESULT.json", 1, 25, title="机械撤单全期结果")
source("S28", "R", "reports/2026-09/2026-09-11-mechanical-cancel-final-evidence/final_guard_manifest.json", 1, 30, title="机械撤单跨午夜完成回执")
commit("S29", "R", "2497d417ee7a8f03d52ba6ccc1c4895c2fb46594", "停止机械撤单稳定性后续生成")
source("S30", "R", "PLAN/2026-10-17-szse-replay-rule-verification.md", 7, 28)
source("S31", "R", "因子/algobench/src/algobench/ml/open5m_330_runtime.py", 24, 57, title="330 研究独立执行合同及公共基础复用")
source("INPUT330", "R", "因子/algobench/configs/intraday_ml_open5m_330_lightgbm_v1.yaml", 24, 42, title="330 列研究的三类封存因子来源")
source("INPUT330CODE", "R", "因子/algobench/src/algobench/ml/open5m_330_data.py", 1, 30, title="330 来源只读对齐实现")
source("MLAUG06", "R", "PLAN/2026-08-06-2026年至今全量原始因子LightGBM实施与运行计划.md", 1, 30)
source("PHASEMETHOD", "R", "reports/2026-08/2026-08-26-arbitrary-multimodal-circular-phase-methods.md", 1, 35)
commit("MLPLANS", "R", "2318d2ff29815213e6f108cb3308629dfa601869", "8 月 10 日两份模型计划首次入库")
commit("DORISIMPL", "R", "9e4260f4425b3b158b6d71fdf7a9b410ace8bf38")
commit("DORISWORKERS", "R", "c4abed19afa2af9c10bc3028415ac0b1658673f4")
source("ACTUALONLY", "R", "decisions/2026-09-03-actual-only-new-factor-prescreen.md", 1, 35)
source("FREEZE", "R", "reports/2026-10/2026-10-09-trading-window-freeze.md", 1, 65)
source("FREEZEHARD", "R", "reports/2026-10/2026-10-09-trading-window-freeze-hardening.md", 1, 65)
source("FREEZEPROD", "R", "reports/2026-10/2026-10-13-szse-model328-trading-window-verification.md", 1, 45)
source("OLD2220", "R", "reports/2026-10/2026-10-10-szse-old-bank-invariance.md", 1, 55)
source("MLIMPL", "R", "PLAN/2026-08-11-Open5m-ML实现前仓库审计.md", 1, 42)
source("STORE1018", "R", "reports/2026-10/2026-10-18-szse-model328-factor-performance-evidence/storage-closeout.json", 1, 12, title="10月18日报告暂存清理机器回执")
commit("RATIOADD", "R", "c84aaaa6df538656dd16a2e7bddd967e338a086f", "比例尺寸线预检的实现尝试")
commit("RATIOREVERT", "R", "5ce9efe180533808586dc3758c7798c0d7e613b0", "撤销比例尺寸线尝试：无查询、无真实结果")
source("JPLAN", "D", "PLAN/2026-10-20-journal-column.md", 1, 45)
source("JV2", "D", "PLAN/2026-10-20-journal-column-v2.md", 1, 45)
commit("JOURNALZOOM", "D", "902b03b440425600c64ac4ba0030eeab3a36d9e9")
commit("JOURNALLEGEND", "D", D)
commit("DASHBUILD", "D", "1b792246376fa7a0cdd20025642d3be0c9a85544")
commit("DASHPUBLISH", "D", "11d42ebed84aa734e189b30d63c782f7cb816f1b")
commit("TAGFEATURE", "D", "7896f7d9")
commit("MODELINIT", "D", "a4f5af84182616227fe6d21c86c7a29e00631b63")
commit("MODELCORRECT", "D", "bc1098eb8bc950290a83e37b92ad6da1c730d67d")
commit("CROSSDAY", "R", "931697771c6e")
commit("CROSSSTOP", "R", "9e26b6ed8b13")

storage = {
    "STORE0909": "reports/2026-09/2026-09-09-calibration-storage-cleanup.md",
    "STORE0910": "reports/2026-09/2026-09-10-calibration-storage-cleanup.md",
    "STORE0911": "reports/2026-09/2026-09-11-server-storage-cleanup.md",
    "STORE0911OLD": "reports/2026-09/2026-09-11-old-factor-storage-cleanup.md",
    "STORE1009": "reports/2026-10/2026-10-09-grouped-calibration-cleanup.md",
    "STORE1010": "reports/2026-10/2026-10-10-calibration-storage-cleanup.md",
    "STORE1012": "reports/2026-10/2026-10-12-calibration-storage-cleanup.md",
    "STORE1013": "reports/2026-10/2026-10-13-szse-model328-scoped-file-cache-reclaim.md",
}
for key, path in storage.items(): source(key, "R", path, 1, 38)
source("STORE1008", "P", PREFIX + "benchmark-evidence/2026-10-08-two-server-storage-cleanup.md", 1, 40)

chain_sources = {
 "onboarding":["S01","S02"], "doris-migration":["S10","S11"], "wangly-env":["R01","R02","R14"],
 "doris-efficiency":["R03"], "storage-cleanup":["STORE0911","STORE1012","R19"],
 "lv2-snapshot":["S03","S04"], "replay":["R22","R23","R25"], "literature":["S05","S07"],
 "algobench":["S07","S09"], "formal-engine":["S13"], "gates":["S14","S17"],
 "fixed-history":["S18","S12"], "open5m":["S12","S19","ACTUALONLY"],
 "cancel-phase":["S25","S22","S27"], "depth-match":["R07","R08"],
 "old-factor-bank":["R04","R05","D01"], "grouped-calibration":["R11","R12","R13"],
 "szse-model328":["R26","R30","R13"], "sse-v2":["R31","R33","R16"],
 "ml-count":["S20","MLAUG06","MLPLANS"], "ml-exec":["S23","MLIMPL"],
 "ml-330":["INPUT330","R34","R35","R36"], "dashboard-build":["DASHBUILD"],
 "report-publish":["DASHPUBLISH"], "visual-b":["D03","D04"], "report-tags":["TAGFEATURE"],
 "model-report":["MODELINIT","D05","MODELCORRECT"], "report328":["D06","R30"],
 "corrected-replay-344":["R15","R13"], "trading-window-freeze":["FREEZE","FREEZEHARD","FREEZEPROD"],
 "research-journal":["JPLAN","JV2","JOURNALZOOM","JOURNALLEGEND"],
 "cross-stock-sync":["R09","CROSSDAY","CROSSSTOP"],
}

chains = {c["id"]: c for c in registry["chains"]}
def edit_chain(cid, **changes):
    chains[cid].update(changes)
    actions.append({"entity":"chain", "id":cid, "action":"revise", "fields":list(changes)})

edit_chain("wangly-env", label="服务器环境与跨账户结果传输", short="环境与传输",
 purpose="配置 wangly 研究环境，建立并有界验收向 wenjie 的结果传输；后续修复两账户默认 Python 环境及来源校验。",
 status="active", closes_into=None,
 fate_note="9 月 4 日已有传输实现及大小文件 canary、重复传输和篡改拒绝验收；不等于所有研究结果均已回传。10 月 20 日另有两账户环境故障定位、重建与独立来源核验。")
edit_chain("doris-efficiency", label="Doris 公共取数实现与有界实测", short="Doris 效率",
 purpose="实现并接入公共 L2 有界取数，实测解析、分组和分页开销，整理统一使用规约。", closes_into=None,
 fate_note="公共入口已实现并接入分组 runner，保存真实 SQL 和 Windows/Linux 回归。36.6% 是解析/分组子阶段，完整读取样本降幅为21.9%—30.4%；沪市自适应复测有变慢样本。未完成全部历史入口迁移。")
edit_chain("doris-migration", fate_note="7 月 15 日草稿后被替换；7 月 16 日已实现唯一网关、查询计划与日级调度，7 月 17 日继续配置资源，7 月 30 日处理数据库恢复后的续算。")
edit_chain("storage-cleanup", status="active", fate_note="9 月起已有多批清理及归档回读，按批次保留恢复与退役范围。对象逻辑字节、临时盘分配量、系统盘和实际配额分别计量，不把各批相加当成同一块硬盘的可用空间。")
edit_chain("fixed-history", fate_note="历史区间组织、恢复与评价框架继续用于后续研究；Open5m 另建窗口、标签及参数身份，旧 open3m 面板仅作比较。定标日前回溯结果不能自动作为纯样本外检验。")
edit_chain("algobench", purpose="先实现六篇论文的痕迹指标与检验，再于7月10日转向主动关注度预测面板；两个阶段的目标和评价分开记录。",
 fate_note="论文痕迹指标阶段不直接做收益预测；关注度阶段采用未来1—3日标签并限单月研究。后续正式引擎复用公共代码，不由此证明关注度预测结论已被采用。")
edit_chain("open5m", purpose="分阶段记录五分钟正式因子库、连续评分核定标、候选行为机制预查与共享收益标签诊断，各阶段保留独立输入及验收范围。",
 fate_note="窗口/因子库、六核定标、actual-only机制预查和标签尾部诊断分别看待；A_clean等仍有计划门，代表日未过60秒不能写成性能通过。后续分组定标复用历史定标方法。")
edit_chain("cancel-phase", purpose="分别研究撤单等待时间分布、正式相位因子与机械撤单测量及条件收益，保留各阶段的范围、完成与停止状态。",
 fate_note="分布与相位已有历史交付；机械撤单于9月11日完成独立验收、封存及整包回验。10月15日仅停止后续逐股稳定性生成，不撤销既有相位结果或已交付预检。")
edit_chain("depth-match", label="盘口深度匹配预检与24列因子", short="深度匹配",
 purpose="检查委托股数与可见盘口深度的关系，从描述性预检推进到独立24列买卖侧因子及601日评价；跨股票同步另列。",
 fate_note="C7.1在9月8日交付601日、24列评价。10月16日另有比例尺寸线实现后撤销，无Doris查询、无真实分布结果；不把局部撤销写成24列深度匹配成果失效。")
edit_chain("old-factor-bank", closes_into={"daily":["2026-09-16"]},
 fate_note="旧R19来源的601日面板及评价保留；原生产guard最终汇总曾超时，逐日数值/独立检查与进程退出分开。10月10日2220数值列含1932诊断列的单日不变性通过，但822.468秒未过300秒门。当前回放下旧参数来源需重新核验。")
edit_chain("grouped-calibration", fate_note="核包在10月10日零点封存，结构runtime_v2在10月12日凌晨交接；七组结构601日重估，z12与λRV沿用200日R19。历史验收保留，10月20日确认旧包缺当前回放来源、不能直接用于当前正式全量计算。")
edit_chain("szse-model328", closes_into={"showcase":"factor","daily":["2026-10-16","2026-10-18"]},
 fate_note="10月18日旧参数/旧回放下601日、328列科学验收与单因子评价完成，性能采用record_only且未达门。10月20日旧包被当前回放准入拒收；新344清单与重新定参独立，不改写旧验收为从未发生。")
edit_chain("replay", closes_into=None, fate_note="保留单日、三日和后续v4/v5完整日签收的具体版本与边界；10月20日明确旧参数不能直接用于当前回放。10月21日六核采集启动属于独立344定参链，不证明全历史修正因子已经生产完成。")
edit_chain("sse-v2", label="沪市委托还原与公开可见因子口径", fate_note="原始委托、公开G1及后续v3分阶段记录。固定版本中v3候选已有实现，29/30股速度试算后触发一小时停止门，未完成全市场验收或生产面板；不将不同列数和候选身份混为同一已验收版本。")
edit_chain("ml-count", purpose="记录127个total-only连续强度输入的模型计划与结构诊断起步。文件名保留‘51个’，首次可追溯正文已为127，未找到51到127的改数证据。",
 fate_note="两份计划于8月10日首次入库；8月4日、8月6日是文件名/正文日期线索，实际编写日仍待核。它们不是当日已训练或全量计算完成的证据。")
edit_chain("ml-exec", fate_note="区分模型适配/调度实现、Development、Freeze、Final与post-hoc比较；不同study身份和资源合同分别保存。后续330仅复用公共合同、权重及守护基础，不能据此沿用旧127研究的全部输入和运行结论。")
edit_chain("ml-330", purpose="分别记录330列候选manifest与选优runner实现，以及9月21日沿9月18日第15折模型开展的328列单次因果复算。",
 fate_note="有133配置候选设施实现，未找到全部候选完整运行签收。9月21日交付固定第15折/1000轮/176日测试区间的因果复算；测试窗口已观察、未计完整成本和跨日退出，不能称为新的封存测试或完成全部候选选优。")
edit_chain("report-publish", purpose="发布研究报告、解释与图表，修正通用阅读功能并维护项目规则；研究日志建设另列独立目标。")
edit_chain("report-tags", closes_into=None,
 fate_note="9月7日在线标签/API持久化与9月9日报告方向对照、筛选排序分别记录。报告正文不能证明标签功能，标签也不是模型报告的研究前提。")
edit_chain("model-report", closes_into={"daily":["2026-09-18"]})

def add_chain(cid, track, label, short, purpose, status, fate, fate_note):
    c={"id":cid,"track":track,"label":label,"short":short,"purpose":purpose,
       "status":status,"fate":fate,"fate_note":fate_note,"closes_into":None}
    registry["chains"].append(c);chains[cid]=c
    actions.append({"entity":"chain","id":cid,"action":"add","reason":purpose})

add_chain("corrected-replay-344","factor","正确盘口344列重新定参","344重定参",
 "按独立344列清单和修正回放，重新取得六个全局共享核与八组结构参数各601日观测，止于冻结参数和有界消费者验收。",
 "active","landed","截至固定来源记录，10月21日00:50:52已启动601日六核正式采集；八组结构、全期冻结和消费者交接尚未完成，未启动344列全期因子生产。")
add_chain("trading-window-freeze","infra","交易日早盘自动冻结与恢复","早盘冻结",
 "按交易日自动暂停和恢复研究任务，处理在途SQL、scope冻结、独立定时器和看门狗计时，验证失败恢复与科学输出不变。",
 "done","landed","10月9日完成实现、Linux回归和有界集成，随后补缺失定时器等兜底；10月13日复验真实生产冻结。未把未实测的45分钟/GPU等场景写成通过。")
add_chain("research-journal","delivery","研究日志与证据图谱建设","研究日志",
 "建立固定版本证据、逐日多任务记录与链条图谱，完成交互、内容审阅及每日维护规则，使工作与原始来源可追溯。",
 "active","landed","10月20日完成首轮采集和竖向图谱，10月21日继续缩放及图例高亮。当前分类修订和历史审计分开记录，日志维护自身不反复制造研究成果。")
add_chain("cross-stock-sync","factor","C3.3跨股票同步预查","跨股同步",
 "独立预查全市场跨股票的同量/同步委托关系，保存统计实现、性能及单日试跑边界；与单只股票盘口深度匹配分开。",
 "done","dropped","后补计划称9月11日放弃C3.3；9月18日提交停止说明并清理相关执行材料。保留已发生的实现和单日试跑，不声称全历史/机制显著性通过；决定日自述与补记日分别说明。")

def point(day, cid, note, use=(), detail=None, date_note=None, outcome=None):
    if day not in notes:
        notes[day] = frontmatter.Post("", date=day, headline="", headline_source="written", chains=[], chains_reviewed=True, highlights=[])
    post=notes[day]
    existing=next((c for c in post["chains"] if (c.get("id") if isinstance(c,dict) else c)==cid),None)
    c=existing if isinstance(existing,dict) else {"id":cid}
    if existing is None: post["chains"].append(c)
    elif not isinstance(existing,dict): post["chains"][post["chains"].index(existing)]=c
    c["note"]=note
    if outcome: c["outcome"]=outcome
    if date_note:
        c["date_status"]="uncertain"
        date_notes[day][cid]=date_note
    point_refs[(day,cid)].extend(use)
    if detail and detail not in extras[day]: extras[day].append(detail)
    actions.append({"entity":"point","date":day,"chain":cid,"action":"revise" if existing else "add", "sources":list(use), "date_note":date_note})
    assert len(note)<=24,(day,cid,note,len(note))
    return c

def remove_point(day,cid):
    post=notes[day]
    post["chains"]=[c for c in post["chains"] if (c.get("id") if isinstance(c,dict) else c)!=cid]
    actions.append({"entity":"point","date":day,"chain":cid,"action":"move_out"})

point("2026-07-15","doris-migration","编写数据库迁移草稿，日期待核",["S10","DORISIMPL"],
 date_note="计划自述7月15日，首次Git入库为7月16日00:44；实际编写时间未由同日记录闭合。后来废止的是原固定分批方案。")
point("2026-07-16","doris-migration","实现唯一取数网关与日级调度",["DORISIMPL","S11"])
point("2026-07-17","doris-migration","接入16工作进程并更新资源配置",["DORISWORKERS"])
point("2026-07-28","gates","调整报价尺度与评分，时点待核",["S14"],
 date_note="当日代码变更成立；题为7月28日真实Tick重定标的计划于7月29日01:25首次入库，不能仅凭文件名确认其完成时点。")
point("2026-08-04","ml-count","模型计划名义日期，编写日待核",["S20","MLPLANS"],
 date_note="文件名为8月4日，首次可追溯入库为8月10日16:41:44；首次正文已为127个total-only输入，未找到51→127的改动证据。")
point("2026-08-06","ml-count","模型计划自述日期，编写日待核",["MLAUG06","MLPLANS"],
 date_note="正文自述编写日8月6日，首次可追溯入库为8月10日16:41:44；保留自述线索，不据此确认当天训练或全量执行。")
point("2026-08-10","ml-count","两份总量模型计划首次入库",["MLPLANS","S20","MLAUG06"],
 detail="8月10日是两份模型计划可核实的首次Git入库日，不倒推其此前没有编写；8月4日和6日仍分别保留日期待核说明。")
point("2026-08-28","cancel-phase","补入多峰圆周相位的方法研究",["PHASEMETHOD"],
 detail="圆周相位方法报告自述8月26日，8月28日首次入库，9月2日再修订。此点按资料入库日记录；实际研究日待核，不凭文件名新增8月26日完成记录。")
point("2026-09-03","open5m","转为实际统计预查并流式归约",["ACTUALONLY"],
 detail="机制预查正式路径改为actual_only、随机化次数0及30秒单日门，保留diagnostic_only/not_run；此前CUDA/null/序号布局优化不等于显著性或算法身份检验已通过。")
point("2026-09-04","open5m","统计股数分布并选择定参代表日",["ACTUALONLY"],
 detail="以L1市场状态从601日中选200个代表定参日，服务后续参数估计；抽样配置和正式全期验收分开。")
point("2026-09-04","wangly-env","配置环境并验收跨账户传输样本",["R01","R02"],
 detail="跨账户传输已有256MiB大文件、1002个小文件、重复执行与目标篡改拒绝canary，不只是一份方案；不等于全部研究结果均已回传。")
point("2026-09-08","old-factor-bank","修复老库并核验F40精确匹配",["R10"],
 detail="9月8日实际接入结构参数和完整响应候选；F40调度验证432.50秒，不证明整库300秒或601日已经完成。")
for day,note in {"2026-09-08":"建立跨股票同步预查与执行方案","2026-09-09":"优化跨股统计并保存性能诊断","2026-09-10":"改进跨股预查暂存与原生输出","2026-09-18":"补记停止决定并清理预查材料"}.items():
    point(day,"cross-stock-sync",note,["R09","CROSSSTOP"] if day.endswith("18") else ["R09"],outcome="dropped" if day.endswith("18") else "landed")
for day in ("2026-09-09","2026-09-10","2026-09-18"): remove_point(day,"depth-match")
point("2026-09-08","depth-match","交付深度匹配24列全历史评价",["R08"])
point("2026-09-11","cross-stock-sync","单日预查及后补停止日期说明",["CROSSDAY","R09","CROSSSTOP"],
 date_note="9月11日单日提交可以核实；放弃决定日期来自9月18日补写的计划自述，未找到同日决定原件。9月18日为可核实补记和清理日。",outcome="landed")
point("2026-09-11","cancel-phase","完成机械撤单独立验收与整包回读",["S24","S27","S28"],
 detail="机械撤单601日计算后的独立正确性、封存和整包回验在上海时间9月11日01:10:41结束，guard退出0；该研究交付不能只归为报告发布。")
point("2026-09-17","old-factor-bank","完成全期评价并保留运行异常说明",["D01"],
 detail="原公开报告说明评价实际完成于9月17日，覆盖601日数值、逐日审核和独立检查；原生产guard最终汇总超时，不能改成正常退出。精确运行身份仍以原结果/guard收据为准。")
point("2026-09-11","old-factor-bank","优化F40并核对正式Python运行环境",["R06","R05"],
 detail="本日正式Python依赖副本和资源核验在wenjie；环境核验不能证明整库300秒达标，也不构成wangly环境对老库的依赖。")
point("2026-09-09","storage-cleanup","清理报告名义日期，执行日待核",["STORE0909"],
 date_note="报告标题为9月9日，首次Git入库为9月10日；正文有09:47/09:48时刻但本轮未取得带完整日期的独立机器回执，因此清理日保留待核。")
for day,note,keys,detail in [
 ("2026-09-10","归档清理旧定参暂存并补入前报告",["STORE0910","STORE0909"],"前一清理报告在9月10日入库；本日遗留暂存清理分别计对象存储166.51MB净减少与临时盘1.68GB释放，不能相加为持久盘回收。"),
 ("2026-09-11","检查双账户存储并清理退役载荷",["STORE0911","STORE0911OLD"],"双账户清理有逐项删除及保留依据；84.42GB是多个文件系统的逻辑净减合计，不代表一块物理磁盘同量增加可用空间。"),
 ("2026-09-12","清理退役试跑并保留生产来源",["R21"],"全期启动前后清理约64.85GB逻辑载荷，未扣证据写入，不等于桶配额增加；601日任务此时只是启动。"),
 ("2026-10-08","清理双账户副本并保存分发凭证",["STORE1008"],None),
 ("2026-10-09","归档预检中间文件并复核保留成果",["STORE1009"],None),
 ("2026-10-10","清理重复定参结果并保留在用缓存",["STORE1010"],"10月10日删除重复结果并归档临时材料；当时正式定参仍在进行，不把清理写成计算已完成。"),
 ("2026-10-12","结构参数封存后清理副本并核验恢复",["STORE1012"],"10月12日10:40复核2433封存文件及139条恢复索引；9.637GiB为tmpfs分配空间，S3净逻辑减少下界0.491GiB，分别计量。"),
 ("2026-10-13","回收生产任务自己的未活跃文件缓存",["STORE1013"],"回收约18.0683GiB任务内未活跃文件缓存并核对运行/来源，属于缓存回收，不是删除同量持久数据或证明Python内存泄漏。"),
 ("2026-10-18","报告封存后清理暂存并核对回读",["STORE1018"],"机器回执为上海时间10月18日21:34:21：移除801个文件、6,200,739,404逻辑字节；tmpfs分配字节另计。持久结果回读通过，不把逻辑删除量说成硬盘配额增量。"),
]: point(day,"storage-cleanup",note,keys,detail=detail)
point("2026-10-09","doris-efficiency","实现公共L2入口并做有界取数实测",["R03"],
 detail="公共L2取数已实现并接入分组runner。36.6%只对应解析与分组；完整读取样本改善21.9%—30.4%，另有变慢样本，不写全流程统一提速。")
point("2026-10-09","grouped-calibration","估计六核尺度并推进参数包封存",["R28","R11","D02"],
 detail="10月9日完成开发/估计阶段，核参数包的实际最终封存是10月10日00:31:50，归档为10月9日的报告不改变执行时间。")
point("2026-10-10","grouped-calibration","封存核包并接入股票日表与结构采集",["R11","R29","D02"])
point("2026-10-12","grouped-calibration","封存结构参数v2并完成正式交接",["R12"],
 detail="结构计算10月12日02:36:46结束、02:38:16封存。七组结构在601日重估，z12与λRV仍为R19的200日来源；参数表生成不是再估计一次核。")
point("2026-10-10","old-factor-bank","验收2220数值列单日严格不变性",["OLD2220"],
 detail="2220数值列含1932个diag__审计列，是旧库单日全市场严格不变性验收，不是2220个新因子研究；完整guard822.468秒，300秒性能门未过。")
point("2026-10-09","trading-window-freeze","实现早盘冻结恢复并完成集成验收",["FREEZE","FREEZEHARD"],
 detail="交易日自动冻结/恢复已有实现、Linux130项及加固后的159项回归和有界集成；两组测试有重叠，不相加为独立总数。未实测的45分钟、GPU等场景保留限制。")
point("2026-10-13","trading-window-freeze","核验生产任务早盘暂停与恢复",["FREEZEPROD"])
q=point("2026-10-16","depth-match","比例尺寸线实现后撤销，无真实结果",["RATIOADD","RATIOREVERT"],
 detail="比例尺寸线是深市委托量对盘口深度的另一项预检尝试，与沪市公开可见v3不同。实现后全部撤销，业务启动即停止，没有Doris查询或真实分布结果。",outcome="dropped")
q["outcome_note"]="仅比例尺寸线尝试被撤销；9月8日已交付的24列深度匹配因子仍保留。"
point("2026-10-20","wangly-env","核验并重建两账户默认Python环境",["R14"],
 detail="本日包含只读启动故障诊断，以及后续默认环境来源、锁文件与独立校验的恢复记录；诊断时未启动业务与随后修复通过分别看待。")
point("2026-10-20","replay","交付回放整改并拒收旧参数来源",["R25","R13","R14"],
 detail="旧核/结构包哈希仍完整，但缺当前修正回放观测来源，实际正式入口拒绝；旧版本历史验收保留，不能直接当当前生产准入。")
point("2026-10-20","sse-v2","核对逻辑分类并实现公开可见v3候选",["R16"],
 detail="沪市逻辑分类与公开可见v3属于原研究主线延续；定义替换、候选实现和真实验收分别记录。")
point("2026-10-20","corrected-replay-344","建立344清单与八组定参来源合同",["R15","R13"],
 detail="344清单独立于旧328，使用全局共享六核和八组结构各601日，排除Z12；代码/有界验证不等于已冻结全期参数。")
remove_point("2026-10-20","report-publish")
point("2026-10-20","research-journal","建设研究日志并审阅历史记录",["JPLAN","JV2"],
 detail="研究日志的证据采集、逐日多链、竖向图谱和内容审阅有独立交付目标，从日常报告发布中分出；不重复记维护提交为新的研究成果。")
point("2026-10-21","replay","签收v5完整日并保留回放来源证明",["R15"])
point("2026-10-21","corrected-replay-344","启动601日六核采集，结构尚未启动",["R15"],
 detail="固定来源记录显示10月21日00:50:52启动六核正式采集；八组结构、正式冻结和消费者交接未完成，未启动344全期因子生产。这里是保存回执的状态，不是本次服务器实时探测。")
point("2026-10-21","sse-v2","记录v3候选验收及一小时速度停止",["R16"],
 detail="v3候选有352源列/540候选身份和单股构造检查；速度试算29/30股后触发一小时停止门，尚无全市场验收或生产面板。")
point("2026-10-21","research-journal","实现纵向缩放与图例高亮连线",["JOURNALZOOM","JOURNALLEGEND"])
notes["2026-10-21"]["headline"]="启动344列六核定参，核对沪市候选并改进日志"
notes["2026-10-21"]["highlights"]=["正确回放v5的完整日签收进入正式601日六核采集；结构定参及全期冻结尚未完成。","沪市公开可见v3候选已有实现，速度门触发停止，未完成全市场验收。","研究日志加入Ctrl滚轮纵向缩放和图例交接高亮。"]

# 修正会误读成已实施、改数或提前收口的旧摘要。
notes["2026-08-04"]["headline"]="核对历史恢复来源；模型计划编写日期待核"
notes["2026-08-04"]["highlights"]=["核对不可变恢复种子、历史来源和收益标签兼容性。","模型计划文件名标8月4日，首次可追溯入库8月10日；编写日待核，首次正文已为127个输入。"]
notes["2026-08-06"]["highlights"]=["改进事件读取、回放和正式因子计算的执行开销。","原始因子模型计划自述8月6日，8月10日首次入库；不能据此认定当日训练或全量运行已完成。","为研究文档加入标题折叠。"]
notes["2026-09-04"]["highlights"]=["统计开盘订单股数分布并选择参数估计代表日，推进撤单相位评价。","配置wangly环境并完成跨账户大小文件传输canary、重复执行和篡改拒绝检查。","更新研究报告；环境、预查与相位计算的验收范围分别保留。"]
notes["2026-09-11"]["headline"]="交付机械撤单预检，优化老库并清理存储"
notes["2026-09-11"]["highlights"]=["机械撤单601日预检完成独立正确性、封存及整包回读。","减少BBO和F40索引开销，检查两账户存储并按清单清理。","C3.3有单日预查；停止决定日期来自后补说明，与9月18日补记/清理分开。"]
notes["2026-10-09"]["headline"]="实测公共取数，推进定标并验收早盘冻结"
notes["2026-10-09"]["highlights"]=["公共L2入口已实现、接入分组runner并完成代表样本实测；保留未迁移与变慢样本。","估计六核尺度、推进参数包封存并归档中间文件；最终封存实际跨至10月10日零点。","交易日自动冻结/恢复及失败兜底通过限定Linux回归与集成验收；并行沪市输入核对另记。"]
notes["2026-10-12"]["headline"]="交接结构参数并启动328列生产，清理定参副本"
notes["2026-10-12"]["highlights"]=["结构runtime_v2于02:38:16封存交接，七组601日重估、两组保留R19的200日来源。","随后按冻结328列合同推进全期因子生产和压力日验证。","清理定参重复副本并复核封存与恢复来源；清理不代表当天完成全部328列生产。"]
notes["2026-10-20"]["headline"]="核验回放与环境，启动新定参准备并建设日志"
notes["2026-10-20"]["highlights"]=["交付回放/执行阶段整改，正式入口拒收缺当前回放来源的旧参数，并核对两账户默认环境。","建立独立344列与八组定参合同，推进沪市公开可见v3候选实现；真实运行状态分别记录。","建设并验收研究日志与证据图谱，从日常报告维护中独立记录。"]
notes["2026-09-21"]["highlights"]=["仅复算9月18日第15折/1000轮模型的176日测试区间：先锁定名单，再处理进场成交，未退出持仓保留估值。","330候选移除f97两列后为328列；不是全部133配置重新选优，已观察测试窗口不能当新封存测试。","发布修正结果并恢复原报告版式；毛收益未扣完整成本与跨日退出。"]
extras["2026-10-07"].append("名义9月29日的分组分类设计于10月7日首次入库；本日按补入与修订资料记录，实际早期编写日期待核，不据文件名新增9月29日完成点。")
extras["2026-10-08"].append("名义9月22日的沪市委托还原报告于10月8日首次入库；当日实现与核对另有提交支持。早期研究日期待核，不把资料标题日期等同于已核实工作日。")

# 精确报告覆盖；空列表明确覆盖旧机器的同日默认推断。
for day in ("2026-07-05","2026-10-10"):
    if day in notes: notes[day]["reports_covering"]=[]
notes["2026-10-21"]["reports_covering"]=[]

# 成果出口按本链内容单独复核，不能从同日其他任务继承。
for cid, days in {
 "doris-migration":[], "lv2-snapshot":["2026-06-25","2026-06-26"],
 "algobench":["2026-07-07","2026-07-08","2026-07-09","2026-07-13"],
 "open5m":["2026-08-06","2026-08-07","2026-09-02","2026-09-03","2026-09-04","2026-09-17"],
 "cancel-phase":["2026-08-16","2026-08-24","2026-09-06"],
 "sse-v2":["2026-10-14"],
}.items():
    chains[cid]["closes_into"]={**(chains[cid].get("closes_into") or {}),"daily":days}
for c in chains.values():
    c["closes_into"] = c.get("closes_into") or {"daily":[]}
    c["report_coverage"]="curated"

edge_specs = [
 ("lv2-snapshot","literature","依赖解除","2026-06-30",["S05","S04"],"6月30日快照分区供factor_lab首个OFI框架读取；纯文献收集不依赖快照完成。","artifact_input"),
 ("literature","algobench","延续","2026-07-06",["S07"],"论文痕迹台架明确复用lowlat事件、生命周期与snapshot订单簿；承接方法和公共代码。","code_reuse"),
 ("algobench","formal-engine","延续","2026-07-16",["S13"],"7月16日在同一研究代码基础扩展生命周期、配对与评分；不承接主动关注度预测结论。","code_reuse"),
 ("doris-migration","formal-engine","依赖解除","2026-07-16",["S11","S13"],"7月16日正式面板接入已实现的Doris网关和日级调度；7月15日草稿不是运行放行。","code_input"),
 ("formal-engine","gates","延续","2026-07-27",["S14"],"7月27日在正式评分与Response流程上调整候选、数量与连续价格规则。","direct_file"),
 ("gates","fixed-history","延续","2026-08-03",["S17","S18"],"固定open3m规则和不可变种子后扩展历史区间；定标日前回溯不自动成为纯样本外。","artifact_input"),
 ("fixed-history","open5m","延续","2026-08-06",["S12"],"复用区间组织和计算/评价框架；Open5m另建窗口、标签和参数身份，旧面板只作比较。","method_reuse"),
 ("ml-count","ml-exec","延续","2026-08-11",["S20","MLPLANS","S23"],"8月10日可追溯入库的总量模型计划进入8月11日实现；8月4日、6日编写日期仍待核。","direct_file"),
 ("open5m","ml-exec","依赖解除","2026-08-11",["S23"],"模型输入检查只读冻结的Open5m来源、manifest和354日完整性；不等于所有模型已运行完成。","artifact_input"),
 ("open5m","cancel-phase","派生","2026-08-19",["S25"],"撤单分布直接复用五分钟生命周期、日历与事件入口，不读取收益或推断账户身份。","code_reuse"),
 ("open5m","depth-match","派生","2026-09-05",["R07"],"C7.1复用现有机制预查和事件几何组件，已有股数汇总只作核验旁证。","direct_file"),
 ("old-factor-bank","sse-v2","派生","2026-09-23",["R31","R32"],"旧库原定义与实际评分器进入沪市可见输入的适用性核验；不表示全部沪市原式已可无损恢复。","code_input"),
 ("old-factor-bank","szse-model328","延续","2026-10-12",["R26"],"10月12日清单精确选择256个旧输出及其必要依赖，并非原284列全搬或只留325个分裂列。","direct_file"),
 ("open5m","grouped-calibration","延续","2026-10-08",["S19"],"10月8日分组预检明确复用连续核历史脚本和股票日中心；200日预检不是601日最终参数。","method_reuse"),
 ("grouped-calibration","szse-model328","延续","2026-10-12",["R12","R26"],"结构runtime_v2于10月12日02:38封存交接，重算计划绑定核表和哈希。此为旧回放版本的历史交接。","artifact_input"),
 ("szse-model328","storage-cleanup","派生","2026-10-16",["R19"],"10月16日清理深市328生产/性能任务的自有暂存并保护恢复来源，不包含全部沪市和账户治理。","direct_file"),
 ("szse-model328","report328","收口","2026-10-18",["R30","D06"],"10月18日同一批328列单因子评价被发布为可浏览报告，不是新模型训练结果。","artifact_input"),
 ("ml-exec","ml-330","延续","2026-09-20",["S31","INPUT330CODE"],"330另建输入和运行身份，仅复用ML公共合同、权重与守护基础，不沿用整套127模型结果。","code_reuse"),
 ("lv2-snapshot","replay","延续","2026-10-17",["S30"],"10月17日重新核验OrderBook状态和数量操作的规则及因子影响；早期样本对照不能提前通过新审计。","code_reuse"),
 ("dashboard-build","report-publish","延续","2026-07-23",["DASHBUILD","DASHPUBLISH"],"后续报告直接继续使用原站点构建与内容管线，有源码/产物连续性。","code_reuse"),
 ("dashboard-build","visual-b","延续","2026-08-11",["D04"],"研究编辑台直接修改既有站点壳层和样式，保留原路由与构建基础。","code_reuse"),
 ("ml-330","model-report","收口","2026-09-21",["R34","D05","MODELCORRECT"],"仅9月21日因果328单次复算替换报告数据；9月19日初版及全部133候选未被算作本次交接。","artifact_input"),
 # 固定列合同和直接因子输入，不能只靠执行框架关系替代。
 ("old-factor-bank","ml-330","依赖解除","2026-09-20",["INPUT330","INPUT330CODE"],"330合同只读封存老因子来源；这是因子输入关系，不是模型执行框架关系。","artifact_input"),
 ("cancel-phase","ml-330","依赖解除","2026-09-20",["INPUT330"],"330输入绑定撤单相位买卖各24列的封存来源与命名空间。","artifact_input"),
 ("depth-match","ml-330","依赖解除","2026-09-20",["INPUT330"],"330输入明确读取独立24列深度匹配的封存来源。","artifact_input"),
 ("ml-330","szse-model328","依赖解除","2026-10-12",["R26","R34"],"9月21日r03冻结模型的全部输入映射、顺序与哈希决定328重算范围；模型预测分数不是因子输入。","artifact_input"),
 ("cancel-phase","szse-model328","依赖解除","2026-10-12",["R26"],"328生产直接保留相位买卖各24列的原定义与分母，不能把来源全归老库。","direct_file"),
 ("depth-match","szse-model328","依赖解除","2026-10-12",["R26"],"328生产直接保留24列深度匹配原注册合同与必要依赖。","direct_file"),
 ("open5m","cross-stock-sync","派生","2026-09-08",["R09","ACTUALONLY"],"C3.3从已有候选机制预查独立展开跨股同步问题；不因同日推进深度匹配就将两者串成因果。","method_reuse"),
 ("dashboard-build","research-journal","延续","2026-10-20",["JPLAN","JV2"],"研究日志在既有静态构建和站点路由上新增独立证据与任务链内容。","code_reuse"),
 ("wangly-env","depth-match","依赖解除","2026-09-08",["R01","R08"],"C7.1在wangly以核对后的环境和guard执行；仅表示环境前提，不表示全量结果已回传wenjie。","direct_file"),
 ("doris-efficiency","grouped-calibration","依赖解除","2026-10-09",["R03"],"10月9日公共有界L2 reader实际接入分组runner；此前预检不追溯归因于本次优化。","code_input"),
 ("trading-window-freeze","szse-model328","依赖解除","2026-10-13",["FREEZEPROD"],"10月13日生产回执核验328任务的早盘暂停与恢复；这是运行保障，不是因子科学输入。","operational_input"),
 ("replay","corrected-replay-344","依赖解除","2026-10-20",["R13","R15"],"修正回放合同与真实worker来源成为344重新定参前提；旧参数包不具备当前来源。","artifact_input"),
 ("grouped-calibration","corrected-replay-344","延续","2026-10-20",["R15","R13"],"只复用归约方法和公共采集接口；新范围采用全局六核、八组各601日，旧分组参数值不直接复用。","method_reuse"),
 ("szse-model328","corrected-replay-344","延续","2026-10-20",["R15"],"复用旧精确列校验与消费者抽取方法，同时新建344独立清单，不宣称新范围绑定旧模型。","method_reuse"),
]

registry["handoffs"]=[]
source_dates={
 ("lv2-snapshot","literature"):"2026-06-30", ("literature","algobench"):"2026-07-03",
 ("algobench","formal-engine"):"2026-07-14", ("doris-migration","formal-engine"):"2026-07-16",
 ("formal-engine","gates"):"2026-07-25", ("gates","fixed-history"):"2026-08-02",
 ("fixed-history","open5m"):"2026-08-04", ("ml-count","ml-exec"):"2026-08-10",
 ("open5m","ml-exec"):"2026-08-10", ("open5m","cancel-phase"):"2026-08-10",
 ("open5m","depth-match"):"2026-09-04", ("old-factor-bank","sse-v2"):"2026-09-17",
 ("old-factor-bank","szse-model328"):"2026-10-10", ("open5m","grouped-calibration"):"2026-08-27",
 ("grouped-calibration","szse-model328"):"2026-10-12", ("szse-model328","storage-cleanup"):"2026-10-16",
 ("szse-model328","report328"):"2026-10-18", ("ml-exec","ml-330"):"2026-08-20",
 ("lv2-snapshot","replay"):"2026-06-26", ("dashboard-build","report-publish"):"2026-07-07",
 ("dashboard-build","visual-b"):"2026-07-13", ("ml-330","model-report"):"2026-09-21",
 ("old-factor-bank","ml-330"):"2026-09-17", ("cancel-phase","ml-330"):"2026-09-09",
 ("depth-match","ml-330"):"2026-09-08", ("ml-330","szse-model328"):"2026-09-21",
 ("cancel-phase","szse-model328"):"2026-09-09", ("depth-match","szse-model328"):"2026-09-08",
 ("open5m","cross-stock-sync"):"2026-09-03", ("dashboard-build","research-journal"):"2026-07-07",
 ("wangly-env","depth-match"):"2026-09-04", ("doris-efficiency","grouped-calibration"):"2026-10-09",
 ("trading-window-freeze","szse-model328"):"2026-10-13", ("replay","corrected-replay-344"):"2026-10-20",
 ("grouped-calibration","corrected-replay-344"):"2026-10-12", ("szse-model328","corrected-replay-344"):"2026-10-18",
}
for frm,to,kind,day,keys,note,basis_kind in edge_specs:
    registry["handoffs"].append({"from":frm,"to":to,"type":kind,"date":day,"source_date":source_dates[(frm,to)],"confidence":"confirmed",
        "evidence_kind":basis_kind,"source_refs":[refs[k] for k in keys],"note":note,
        "review":{"by":"Codex","on":"2026-10-21","basis":note,"scope":"原始引用支持本条承接，不代表全部阶段验收通过。"}})

removed={(e["from"],e["to"]) for e in original["handoffs"]}-{(e["from"],e["to"]) for e in registry["handoffs"]}
assert removed=={("onboarding","lv2-snapshot"),("wangly-env","old-factor-bank"),("visual-b","report-tags"),("report-tags","model-report")}

for cid,c in chains.items():
    active=[day for day,post in sorted(notes.items()) if any((x.get("id") if isinstance(x,dict) else x)==cid for x in post["chains"])]
    c["review"]={"by":"Codex","on":"2026-10-21","days":len(active),"span":[min(active),max(active)],
                  "unreviewed_days":[day for day in active if cid in date_notes[day]],
                  "scope":"研究归属及原始来源已复核；待核列表表示日期或具体断言尚未闭合，不替代运行验收。"}
    c["source_refs"]=[refs[k] for k in chain_sources[cid]]

registry["schemaVersion"]=1
registry["note"]="2026-10-21依审计修正的任务及承接登记。首末日期是记录跨度；待核日期另注。confirmed表示原始引用支持该关系，不是用户逐条签字或全流程已验收。source_date为来源阶段的已登记记录，date为承接记录，不宣称来源当天已完成未来交接；精确对象以source_refs为准。"
registry["evidence_snapshot"]={"as_of":"2026-10-21","repos":{REPOS[k][1]:REPOS[k][2] for k in REPOS},
                               "audit":"docs/journal-review/chain-audit-2026-10-21.md"}

for day,post in sorted(notes.items()):
    post["date"]=day;post["chains_reviewed"]=True;post["reviewed_on"]="2026-10-21"
    if date_notes[day]:post["date_notes"]=date_notes[day]
    if len(post.get("highlights",[]))>3: raise AssertionError((day,"too many highlights"))
    if len(post.get("headline",""))>40: raise AssertionError((day,"long headline",post["headline"]))
    if extras[day]:
        section="\n\n## 日期与结果说明\n\n"+"\n\n".join(extras[day])
    else:section=""
    if date_notes[day]:
        section+="\n\n## 日期待核\n\n"+"\n\n".join(f"**{chains[cid]['short']}：** {txt}" for cid,txt in date_notes[day].items())
    section+="\n\n## 原始依据\n\n以下固定文件核对定义、输入与结果范围；入库日、归档日和实际运行日分别解释。各仓当日提交索引在‘原始记录’中，提交数量不等于工时或单链贡献。\n\n"
    for item in post["chains"]:
        cid=item["id"] if isinstance(item,dict) else item
        keys=list(dict.fromkeys(point_refs[(day,cid)] or chain_sources[cid]))
        section+=f"- **{chains[cid]['label']}**："+"；".join(f"[{refs[k]['title']}]({refs[k]['url']})" for k in keys)+"。\n"
    # 只在本次工作快照上生成；此前正文逐字保留。
    body=post.content.rstrip()
    post.content=body+"\n\n<!-- journal-audit-provenance-2026-10-21 -->"+section+"\n"
    (ROOT / f"content/journal/{day}.md").write_text(frontmatter.dumps(post)+"\n",encoding="utf-8")

(ROOT / "content/chains.json").write_text(json.dumps(registry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
config=json.loads((BASE/"journal_repos.json").read_text(encoding="utf-8"))
for spec in config["repos"]:
    spec["revision"]=next(REPOS[k][2] for k in REPOS if REPOS[k][1]==spec["name"])
config["snapshot_note"]="2026-10-21审计修订固定快照；研究9d3e0a37、父仓e63c0d37、看板0910a201。计划按文件名归档不代表实际工作日；正文日期待核及人工归属优先。"
for cid in ("corrected-replay-344","trading-window-freeze","research-journal","cross-stock-sync"):
    tokens={"corrected-replay-344":["corrected-replay-344","limit-terminal-closure","rule-supported-cancel"],
            "trading-window-freeze":["trading-window","trading-freeze"],
            "research-journal":["journal-column","journal-handoff"],
            "cross-stock-sync":["C3.3","cross-stock-synchronization"]}[cid]
    config["suggest"][cid]={"tokens":tokens,"paths":[]}
(ROOT/"scripts/journal_repos.json").write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

manifest={"on":"2026-10-21","source_snapshot":registry["evidence_snapshot"],"actions":actions,
          "removed_edges":[list(e) for e in sorted(removed)],"added_edges":[[e["from"],e["to"]] for e in registry["handoffs"] if (e["from"],e["to"]) not in {(x["from"],x["to"]) for x in original["handoffs"]}],
          "source_catalog":refs,"counts":{"chains":len(chains),"edges":len(registry["handoffs"]),"days":len(notes),"points":sum(len(p["chains"]) for p in notes.values())},
          "date_notes":{d:n for d,n in date_notes.items() if n}}
(ROOT/"docs/journal-review/audit-2026-10-21/remediation-actions.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(manifest["counts"],ensure_ascii=False))
print("date_notes",json.dumps(manifest["date_notes"],ensure_ascii=False))
