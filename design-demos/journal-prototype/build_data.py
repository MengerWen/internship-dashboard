# -*- coding: utf-8 -*-
"""原型用数据生成器（throwaway）。从本机三个仓库 + content/daily 生成 data.json。

不参与站点构建；只给 design-demos/journal-prototype/direction-*.html 使用。
"""
from __future__ import annotations

import collections
import datetime
import json
import pathlib
import re
import subprocess

from headlines import HEADLINES

DASH = pathlib.Path(r"D:/MG/！Internship/BUILD/汇报")
RESEARCH = pathlib.Path(r"D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research")
PARENT = pathlib.Path(r"D:/MG/_GitLinked/Quant_Research-Trading")
OUT = DASH / "design-demos/journal-prototype/data.json"

REPOS = [
    ("sirui-quant-research", RESEARCH, "https://github.com/MengerWen/sirui-quant-research/commit/{sha}"),
    ("Quant_Research-Trading", PARENT, "https://github.com/MengerWen/Quant_Research-Trading/commit/{sha}"),
    ("internship-dashboard", DASH, "https://github.com/MengerWen/internship-dashboard/commit/{sha}"),
]

TRACKS = [
    {"id": "infra", "label": "数据与服务器", "stage": "data-processing"},
    {"id": "snapshot", "label": "快照与回放", "stage": "lv2-snapshot"},
    {"id": "footprint", "label": "算法痕迹", "stage": "algo-footprint"},
    {"id": "factor", "label": "因子与定标", "stage": "factor"},
    {"id": "model", "label": "模型", "stage": "model"},
    {"id": "delivery", "label": "看板与交付", "stage": None},
]

# 链条草案：id, 轨道, 名称, 起, 止, 匹配 PLAN 文件名的关键词
# 链条草案（第二轮：按 lv2_snapshot_workspace / algobench / 米筐 的真实触及日修订）
CHAINS = [
    ("onboarding", "infra", "上手：行情环境与交易规则", "2026-06-23", "2026-06-24", []),
    ("doris-migration", "infra", "Doris 访问重构与服务器迁移", "2026-07-15", "2026-07-30",
     ["doris", "服务器", "内存事故", "RUNBOOK"]),
    ("wangly-env", "infra", "wangly 环境与结果转移", "2026-09-04", "2026-09-11",
     ["wangly-environment", "wangly-to-wenjie"]),
    ("doris-efficiency", "infra", "Doris 通用效率", "2026-10-08", "2026-10-09", ["general-doris"]),
    ("storage-cleanup", "infra", "存储盘点、保留与清理", "2026-10-14", "2026-10-16",
     ["wangly-", "storage-principles", "hot-cleanup"]),
    ("lv2-snapshot", "snapshot", "LV2 逐笔重建 100ms 快照", "2026-06-25", "2026-07-08", ["lv2"]),
    ("replay", "snapshot", "深市回放与基础正确性", "2026-10-17", "2026-10-20",
     ["replay", "chinext", "foundation-correctness", "project-architecture", "remediation"]),
    ("literature", "footprint", "文献复现与因子框架搭建", "2026-06-29", "2026-07-03", []),
    ("algobench", "footprint", "algobench 台架与注意力面板", "2026-07-06", "2026-07-14",
     ["最初构建因子", "L1参考数据"]),
    ("formal-engine", "footprint", "正式因子引擎与打分器", "2026-07-15", "2026-07-25",
     ["formal", "final-assembly", "step7a", "候选边", "Task12", "日内因子", "2026Q2"]),
    ("gates", "footprint", "数量门与价格门定标与区间扩展", "2026-07-27", "2026-08-02",
     ["Xq10", "价格Gate", "Tick", "三分钟", "固定参数全区间"]),
    ("fixed-history", "factor", "固定参数历史回补", "2026-08-03", "2026-08-06",
     ["fixed-", "复用2026年"]),
    ("open5m", "factor", "open5m 因子表现与核定标", "2026-08-06", "2026-09-04",
     ["open5m-2025", "open5m-no", "open5m-kernel", "open5m-real", "nine-parameter", "高频量价",
      "A-clean", "new-factor-mechanism", "order-quantity", "定标与3.11"]),
    ("cancel-phase", "factor", "撤单延迟与撤单阶段因子", "2026-08-19", "2026-09-09",
     ["cancel-lag", "cancel-phase", "mechanical-cancel"]),
    ("depth-match", "factor", "深度匹配与跨股同步预查", "2026-09-05", "2026-09-09",
     ["C7.1", "C3.3", "depth-match"]),
    ("old-factor-bank", "factor", "老因子库与 300 秒门", "2026-09-07", "2026-09-12", ["old-factor"]),
    ("grouped-calibration", "factor", "分组定标", "2026-10-07", "2026-10-11", ["grouped-", "f40-"]),
    ("szse-model328", "factor", "深市 328 列：重算到签收", "2026-10-10", "2026-10-18",
     ["szse-model328", "szse-old-factor"]),
    ("sse-v2", "factor", "沪市委托 v2 与可见 G1", "2026-09-23", "2026-10-17", ["sse-", "沪市委托"]),
    ("ml-count", "model", "51 个 count 因子 ML", "2026-08-04", "2026-08-06", ["51个count", "LightGBM"]),
    ("ml-exec", "model", "ML 执行适配与资源合同", "2026-08-11", "2026-08-18",
     ["Open5m-ML", "ml-", "algebra", "boosting", "random-forest", "raw-linear", "项目统一Python"]),
    ("ml-330", "model", "330 候选与因果单次拟合", "2026-09-19", "2026-09-23",
     ["open5m-330", "causal-single"]),
    ("dashboard-build", "delivery", "看板建站", "2026-07-07", "2026-07-13", []),
    ("report-publish", "delivery", "日报与报告发布、看板维护", "2026-07-22", "2026-10-20", []),
    ("visual-b", "delivery", "研究编辑台视觉实施", "2026-08-11", "2026-08-11",
     ["research-desk", "visual"]),
    ("report-tags", "delivery", "汇报标签与报告页", "2026-09-04", "2026-09-09",
     ["report-tags", "atlas-design", "all-directions-design"]),
    ("model-report", "delivery", "模型报告发布", "2026-09-17", "2026-09-21", ["model-dashboard"]),
    ("report328", "delivery", "328 列成果报告发布", "2026-10-16", "2026-10-18", ["szse-model328-report"]),
]

# 交接草案：来源链 → 目标链，四种类型（延续／派生／依赖解除／收口）
HANDOFFS = [
    ("onboarding", "lv2-snapshot", "延续"),
    ("lv2-snapshot", "literature", "延续"),
    ("literature", "algobench", "延续"),
    ("algobench", "formal-engine", "延续"),
    ("doris-migration", "formal-engine", "依赖解除"),
    ("formal-engine", "gates", "延续"),
    ("gates", "fixed-history", "延续"),
    ("fixed-history", "open5m", "延续"),
    ("ml-count", "ml-exec", "延续"),
    ("open5m", "ml-exec", "依赖解除"),
    ("open5m", "cancel-phase", "派生"),
    ("cancel-phase", "depth-match", "派生"),
    ("wangly-env", "old-factor-bank", "依赖解除"),
    ("old-factor-bank", "sse-v2", "派生"),
    ("old-factor-bank", "szse-model328", "延续"),
    ("depth-match", "grouped-calibration", "延续"),
    ("grouped-calibration", "szse-model328", "延续"),
    ("szse-model328", "storage-cleanup", "派生"),
    ("szse-model328", "report328", "收口"),
    ("ml-exec", "ml-330", "延续"),
    ("sse-v2", "replay", "延续"),
    ("dashboard-build", "report-publish", "延续"),
    ("dashboard-build", "visual-b", "延续"),
    ("visual-b", "report-tags", "延续"),
    ("report-tags", "model-report", "延续"),
    ("ml-330", "model-report", "收口"),
]

# 窄列里用的短名
SHORT = {
    "onboarding": "上手", "doris-migration": "Doris 迁移", "wangly-env": "wangly 环境",
    "doris-efficiency": "Doris 效率", "storage-cleanup": "存储收尾", "lv2-snapshot": "LV2 快照",
    "literature": "文献复现", "algobench": "algobench", "replay": "回放核验",
    "formal-engine": "因子引擎", "gates": "门限定标", "fixed-history": "历史回补",
    "open5m": "open5m", "cancel-phase": "撤单阶段", "depth-match": "深度匹配",
    "old-factor-bank": "老因子库", "grouped-calibration": "分组定标", "szse-model328": "深市 328",
    "sse-v2": "沪市 v2", "ml-count": "count ML", "ml-exec": "ML 执行", "ml-330": "330 候选",
    "dashboard-build": "看板建站", "report-publish": "发布维护", "visual-b": "视觉实施",
    "report-tags": "汇报标签", "model-report": "模型报告", "report328": "328 报告",
}

# 链条的路径特征：PLAN 没命中时用它把当天归到链上（标为 inferred）
CHAIN_PATHS = {
    "onboarding": ["米筐Ricequant", "交易规则"],
    "lv2-snapshot": ["lv2_snapshot_workspace"],
    "literature": ["因子/文献", "因子/factor_lab", "因子/clusterlob", "因子/lowlat", "Cross-Impact"],
    "algobench": ["因子/algobench", "因子/PLAN"],
    "doris-migration": ["benchmark-evidence"],
    "formal-engine": ["scripts/run_formal", "scripts/validate_formal", "scripts/prepare_intraday"],
    "gates": ["scripts/run_intraday_interval", "scripts/audit_intraday_interval", "scripts/formal_study_control"],
    "dashboard-build": ["site/", "build.py", "worker/"],
    "report-publish": ["content/daily", "content/assets", "artifacts/", "tools/", "templates/"],
    "storage-cleanup": ["scripts/cleanup", "scripts/tests"],
    "replay": ["lv2_snapshot_workspace/src", "scripts/certify", "scripts/run_szse_replay"],
    "szse-model328": ["scripts/run_szse_model328", "scripts/build_szse_model328"],
    "sse-v2": ["scripts/sse_original", "scripts/run_sse", "docs/sse-original-order-v2", "scripts/audit_sse"],
    "open5m": ["scripts/run_open5m", "scripts/_open5m", "scripts/build_open5m", "scripts/rank_open5m",
               "scripts/audit_open5m", "scripts/prepare_open5m"],
    "cancel-phase": ["scripts/run_open5m_cancel", "scripts/render_open5m_cancel"],
    "ml-exec": ["scripts/benchmark_intraday_ml", "scripts/run_intraday_ml", "docs/evidence"],
    "ml-330": ["scripts/run_open5m_single_fit", "scripts/build_intraday_ml_open5m_330"],
    "report-tags": ["worker/", "site/js/report-tags.js", "site/js/tag-model.js"],
    "report328": ["templates/"],
}

PATH_TRACK = [
    ("lv2_snapshot_workspace", "snapshot"),
    ("因子/algobench", "factor"),
    ("reports/", "factor"),
    ("scripts/", "factor"),
    ("benchmark-evidence", "infra"),
    ("米筐", "infra"),
    ("content/", "delivery"),
    ("site/", "delivery"),
    ("build.py", "delivery"),
    ("templates/", "delivery"),
    ("tools/", "delivery"),
    ("artifacts/", "delivery"),
    ("tests/", "delivery"),
    ("worker/", "delivery"),
    ("因子/", "footprint"),
    ("dashboard", "delivery"),
]
# 人工指定归属：脚本推不出来、但人知道该算哪条链的日子。
# 生产里这相当于 content/journal/YYYY-MM-DD.md 的 chains 字段，永远压过脚本的推断。
# 每日汇报的日期是归档标签，不等于做这件事的日子。默认一篇汇报覆盖它自己那天；
# 下面列出经核对确实不是的，值是「实际做这些事的日子」。空列表表示不覆盖任何研究日。
REPORT_COVERS = {
    # 示例占位内容，随建站 init 提交进来的，不是研究
    "2026-07-05": [],
    # 区间扩展：07-30 "extend formal intraday evaluation interval" 起，07-31 收尾
    "2026-08-01": ["2026-07-30", "2026-07-31"],
    # 601 日全部因子评价：09-12 启动后台计算，报告正文自述「实际评价完成日期为 2026-09-17」
    "2026-09-16": ["2026-09-12", "2026-09-17"],
}

DAY_OVERRIDE = {}

# 按仓库限定取哪棵子树；没列的仓库整仓都算
ONLY_UNDER = {"Quant_Research-Trading": "26 Summer/❗思瑞投资/"}

WD = "一二三四五六日"


def run(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout


def collect_repo(name, repo, tmpl, days):
    raw = run(repo, "log", "--date=short", "--pretty=format:C\t%ad\t%h\t%s",
              "--name-only", "--since=2026-06-01")
    cur = None
    for line in raw.splitlines():
        if line.startswith("C\t"):
            _, d, sha, subj = line.split("\t", 3)
            cur = d
            entry = days[d]["repos"].setdefault(
                name, {"commits": 0, "paths": collections.Counter(), "items": [], "url": tmpl})
            entry["commits"] += 1
            if len(entry["items"]) < 10:
                entry["items"].append({"sha": sha, "subject": subj})
        elif line.strip() and cur:
            entry = days[cur]["repos"].get(name)
            if entry is None:
                continue
            path = line.strip()
            # 父仓是个大杂烩：只有思瑞那棵子树算本实习，其余（别家笔试、仓库根文件）全丢
            allow = ONLY_UNDER.get(name)
            if allow:
                if not path.startswith(allow):
                    continue
                path = path[len(allow):]
            parts = path.split("/")
            key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
            entry["paths"][key] += 1


def plan_title(path: pathlib.Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem


def build_days():
    days = collections.defaultdict(
        lambda: {"repos": {}, "plans": [], "report": None})
    for name, repo, tmpl in REPOS:
        collect_repo(name, repo, tmpl, days)

    for path in sorted((RESEARCH / "PLAN").glob("*.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", path.name)
        if not m:
            continue
        slug = m.group(2)
        if slug.startswith("dating") or "wenjie-ide" in slug:
            continue
        days[m.group(1)]["plans"].append(
            {"slug": slug, "file": "PLAN/" + path.name, "title": plan_title(path)})

    for folder in ("docs/plans", "PLAN"):
        for path in sorted((DASH / folder).glob("*.md")):
            m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", path.name)
            if m:
                days[m.group(1)]["plans"].append(
                    {"slug": m.group(2), "file": f"dashboard/{folder}/" + path.name,
                     "title": plan_title(path)})

    for path in sorted((DASH / "content/daily").glob("*.md")):
        if path.name.endswith(".show.md"):
            continue
        txt = path.read_text(encoding="utf-8", errors="replace")
        title = re.search(r'^title:\s*"?(.+?)"?\s*$', txt, re.M)
        summary = re.search(r'^summary:\s*"?(.+?)"?\s*$', txt, re.M)
        has_show = ((path.parent / (path.stem + ".show.html")).exists()
                    or (path.parent / (path.stem + ".show.md")).exists())
        added = run(DASH, "log", "--diff-filter=A", "--date=short", "--pretty=format:%ad",
                    "--", str(path).replace("\\", "/")).split()
        published_on = added[-1] if added else None
        stage = re.search(r"^stage:\s*(\S+)\s*$", txt, re.M)
        days[path.stem]["report"] = {
            "stage": stage.group(1) if stage else None,
            "date": path.stem,
            "title": title.group(1) if title else path.stem,
            "summary": summary.group(1) if summary else "",
            "has_show": has_show,
            "published_on": published_on,
        }
    return days


STAGE_TRACK = {t["stage"]: t["id"] for t in TRACKS if t["stage"]}
STAGE_TRACK["server-l2-factor-pipeline-complete"] = "snapshot"   # 仓库里一处过期 stage


def assign_chains(date, day):
    if date in DAY_OVERRIDE:
        return list(DAY_OVERRIDE[date]), {c: "confirmed" for c in DAY_OVERRIDE[date]}
    picked, how = [], {}
    for cid, track, _label, start, end, kws in CHAINS:
        if not (start <= date <= end) or not kws:
            continue
        if any(any(k.lower() in plan["slug"].lower() for k in kws) for plan in day["plans"]):
            picked.append(cid)
            how[cid] = "confirmed"
    if picked:
        return picked, how

    all_paths = [p for entry in day["repos"].values() for p in entry["paths"]]
    for cid, _track, _label, start, end, _kws in CHAINS:
        if not (start <= date <= end):
            continue
        prefixes = CHAIN_PATHS.get(cid, [])
        if prefixes and any(p.startswith(q) or q in p for p in all_paths for q in prefixes):
            picked.append(cid)
            how[cid] = "inferred"
    if picked:
        return picked, how

    touched = set()
    if day["report"] and day["report"].get("stage") in STAGE_TRACK:
        touched.add(STAGE_TRACK[day["report"]["stage"]])
    for repo_name, entry in day["repos"].items():
        if repo_name == "internship-dashboard":
            touched.add("delivery")
            continue
        for path in entry["paths"]:
            for prefix, track in PATH_TRACK:
                if path.startswith(prefix) or prefix in path:
                    touched.add(track)
                    break
    for cid, track, _label, start, end, _kws in CHAINS:
        if start <= date <= end and track in touched:
            picked.append(cid)
            how[cid] = "inferred"
    return picked, how


def draft_headline(day, date):
    if date in HEADLINES:
        return HEADLINES[date][0], "written"
    if day["report"]:
        return day["report"]["title"], "report"
    if day["plans"]:
        # 只取第一份计划的标题，不拼接：拼出来的句子一律超长，而且读起来像两件事挤在一起
        title = day["plans"][0]["title"]
        title = re.sub(r"^(Superseded|SUPERSEDED)\s*[:：]\s*", "", title).strip()
        title = re.sub(r"实施(计划|与运行计划)$", "", title).strip()
        return title, "plan"
    for repo_name in ("sirui-quant-research", "Quant_Research-Trading", "internship-dashboard"):
        entry = day["repos"].get(repo_name)
        if entry and entry["items"]:
            return entry["items"][0]["subject"], "commit"
    return "无记录", "none"


def main():
    days = build_days()

    # 汇报覆盖了哪些工作日 / 哪天把汇报发了出去
    covering = collections.defaultdict(list)
    published = collections.defaultdict(list)
    for rdate, day in list(days.items()):
        rep = day.get("report")
        if not rep:
            continue
        for wd in REPORT_COVERS.get(rdate, [rdate]):
            covering[wd].append(rdate)
            days[wd]  # 触发 defaultdict，确保这天在表里
        if rep.get("published_on"):
            published[rep["published_on"]].append(rdate)
            days[rep["published_on"]]

    out_days = []
    for date in sorted(days):
        day = days[date]
        # 提交全部落在范围外路径上的仓库条目先丢掉（例如其他公司的笔试）
        for name in [n for n, e in day["repos"].items() if not e["paths"]]:
            del day["repos"][name]
        # 过滤后什么都不剩的日子直接不进日志
        # 只有名义汇报日期、既没提交也没计划、也不发布也不被覆盖的日子，不是工作日
        if (not day["plans"] and not day["repos"]
                and not covering.get(date) and not published.get(date)):
            continue
        picked, how = assign_chains(date, day)
        head, source = draft_headline(day, date)
        weekday = datetime.date.fromisoformat(date).weekday()
        out_days.append({
            "date": date,
            "weekday": "周" + WD[weekday],
            "is_weekend": weekday >= 5,
            "headline": head[:64],
            "headline_source": source,
            "highlights": HEADLINES.get(date, (None, []))[1],
            "chains": picked,
            "chain_confidence": how,
            "commits": {rn: e["commits"] for rn, e in day["repos"].items()},
            "total_commits": sum(e["commits"] for e in day["repos"].values()),
            "paths": {rn: e["paths"].most_common(4) for rn, e in day["repos"].items()},
            "items": {rn: e["items"] for rn, e in day["repos"].items()},
            "urls": {rn: e["url"] for rn, e in day["repos"].items()},
            "plans": day["plans"],
            "report": day["report"],
            "reports_covering": covering.get(date, []),
            "reports_published": published.get(date, []),
        })

    data = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "tracks": TRACKS,
        "chains": [{"id": c[0], "track": c[1], "label": c[2], "short": SHORT.get(c[0], c[0]),
                    "start": c[3], "end": c[4]} for c in CHAINS],
        "handoffs": [{"from": a, "to": b, "type": t} for a, b, t in HANDOFFS],
        "days": out_days,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT.parent / "data.js").write_text(
        "/* 原型数据，由 build_data.py 生成，勿手改 */\nwindow.JOURNAL_DATA = " + payload + ";\n",
        encoding="utf-8")
    print("days:", len(out_days), "chains:", len(CHAINS), "->", OUT.name, "+ data.js")
    unclassified = [d["date"] for d in out_days if not d["chains"]]
    print("未归类天数:", len(unclassified), unclassified)
    counts = collections.Counter(c for d in out_days for c in d["chains"])
    for cid, _t, label, _s, _e, _k in CHAINS:
        print(f"  {cid:22s} {counts.get(cid, 0):3d} 天  {label}")
    overlap = collections.Counter(len(d["chains"]) for d in out_days)
    print("单日链条数分布:", dict(sorted(overlap.items())))


main()
