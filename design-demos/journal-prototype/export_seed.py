# -*- coding: utf-8 -*-
"""把原型里的链条草案与手写内容导出成正式契约文件（一次性迁移脚本）。

读 `data.json`（由 build_data.py 生成），写：
  content/chains.json              轨道、链条、交接
  content/journal/YYYY-MM-DD.md    88 天的 headline / chains / highlights / reports_covering

只写「人写」那一层。`content/journal/_evidence/*.json` 由正式采集脚本
`scripts/collect_journal_evidence.py` 生成，不在这里产出。

跑完这一次就可以删掉；之后这些文件由人直接维护。
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data.json"
CHAINS_OUT = ROOT / "content" / "chains.json"
JOURNAL_DIR = ROOT / "content" / "journal"

# 每条链条一句话说清它要干成什么。链条的起止不写进 chains.json，由有记录的日子推出来。
PURPOSE = {
    "onboarding": "接上米筐行情环境，把沪深交易规则和异常交易监控细则整理成可查的材料",
    "doris-migration": "把数据访问从本地切到服务器 Doris，并在内存事故后加固 RUNBOOK",
    "wangly-env": "在 wangly 上建起可跑的研究环境，并把结果转回 wenjie",
    "doris-efficiency": "压低 Doris 侧通用查询的开销",
    "storage-cleanup": "盘点对象存储与暂存，按保留策略清理重复副本并留下恢复映射",
    "lv2-snapshot": "把逐笔流水按真实事件顺序回放成 100ms 订单簿快照，并与米筐 3 秒数据逐档对齐",
    "replay": "核验深市回放规则，迁移原生回放入口，审计基础正确性",
    "literature": "复现订单流失衡、ClusterLOB 与低延迟交易三条线，搭起 factor_lab 因子框架",
    "algobench": "建起 algobench 台架与全市场注意力面板，确定检测算法痕迹的方向",
    "formal-engine": "做出正式因子引擎：生命周期 schema、配对与打分器、冲击响应与端到端回归",
    "gates": "定标数量门与价格门，并把正式评价区间扩展到更长样本",
    "fixed-history": "用固定参数回补历史区间的因子评价",
    "open5m": "把开盘五分钟因子的表现、核定标与九参数定标跑通并提速",
    "cancel-phase": "测出撤单延迟分布，做出撤单阶段与机械撤单相关的因子",
    "depth-match": "做出盘口深度精确匹配与跨股同步行为的预查因子",
    "old-factor-bank": "把老因子库重算到 300 秒门内，并启动 601 日全历史计算",
    "grouped-calibration": "做分组定标，并把分组定标的分析提速",
    "szse-model328": "把深市 328 列因子在 601 个交易日上算完、验收、封存并评价表现",
    "sse-v2": "还原沪市原始委托并做出可见 G1 口径，把全流程提速到可用",
    "ml-count": "用 51 个 count 因子做机器学习与结构诊断",
    "ml-exec": "做出各族模型的执行适配与资源合同，去掉 ML 流水线里的重复计算",
    "ml-330": "用 330 个候选做 LightGBM 全量研究与因果单次拟合重算",
    "dashboard-build": "把成果看板从零建起来并部署上线",
    "report-publish": "持续把日报与阶段报告发布到看板，并维护展示页",
    "visual-b": "把看板实施成「研究编辑台」这套视觉方向",
    "report-tags": "给每日汇报做标签体系，支持归类、筛选与在线编辑",
    "model-report": "发布模型相关的成果报告页",
    "report328": "发布深市 328 列因子的 601 日成果报告",
}


def yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    days = data["days"]
    chains = {c["id"]: c for c in data["chains"]}

    # 每条链条实际活跃的日子 / 它的工作写进了哪几篇汇报 / 哪几天的归属还是推断
    active: dict[str, list[str]] = {}
    covered: dict[str, list[str]] = {}
    inferred_days: dict[str, list[str]] = {}
    for day in days:
        for cid in day["chains"]:
            active.setdefault(cid, []).append(day["date"])
            for rep in day.get("reports_covering", []):
                if rep not in covered.setdefault(cid, []):
                    covered[cid].append(rep)
            if day["chain_confidence"].get(cid) != "confirmed":
                inferred_days.setdefault(cid, []).append(day["date"])

    sealed = {h["from"] for h in data["handoffs"] if h["type"] == "收口"}
    track_stage = {t["id"]: t["stage"] for t in data["tracks"]}
    last_day = days[-1]["date"]

    missing = [cid for cid in active if cid not in PURPOSE]
    if missing:
        print("这些链条还没写 purpose：", missing)
        return 1

    out_chains = []
    for c in data["chains"]:
        cid = c["id"]
        a = active.get(cid)
        if not a:
            continue
        closes: dict[str, object] = {}
        if cid in sealed and track_stage.get(c["track"]):
            closes["showcase"] = track_stage[c["track"]]
        if covered.get(cid):
            closes["daily"] = sorted(covered[cid])
        out_chains.append({
            "id": cid,
            "track": c["track"],
            "label": c["label"],
            "short": c["short"],
            "purpose": PURPOSE[cid],
            "status": "active" if a[-1] >= "2026-10-17" else "done",
            "closes_into": closes or None,
            "review": {
                "days": len(a),
                "span": [a[0], a[-1]],
                "unreviewed_days": inferred_days.get(cid, []),
            },
        })

    payload = {
        "schemaVersion": 1,
        "note": ("链条逻辑的唯一权威。起止不写在这里，由 content/journal/*.md 里引用它的日子推出来。"
                 "chains[].review 是从草案带过来的审阅状态，unreviewed_days 里的归属还是脚本推断的，"
                 "逐条看过之后把那一天从列表里删掉；列表清空即这条链已确认。"),
        "tracks": data["tracks"],
        "chains": out_chains,
        "handoffs": [{"from": h["from"], "to": h["to"], "type": h["type"], "confidence": "inferred"}
                     for h in data["handoffs"]
                     if h["from"] in active and h["to"] in active],
    }
    CHAINS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHAINS_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")

    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for day in days:
        lines = ["---", f"date: {day['date']}", f'headline: "{day["headline"]}"',
                 f"chains: {yaml_list(day['chains'])}"]
        reviewed = bool(day["chains"]) and all(
            day["chain_confidence"].get(c) == "confirmed" for c in day["chains"])
        lines.append(f"chains_reviewed: {'true' if reviewed else 'false'}")
        if day.get("highlights"):
            lines.append("highlights:")
            lines.extend(f'  - "{h}"' for h in day["highlights"])
        if day.get("reports_covering"):
            lines.append(f"reports_covering: {yaml_list(day['reports_covering'])}")
        lines.append(f"headline_source: {day['headline_source']}")
        lines.append("---")
        lines.append("")
        (JOURNAL_DIR / f"{day['date']}.md").write_text("\n".join(lines) + "\n",
                                                       encoding="utf-8", newline="\n")
        written += 1

    reviewed_n = sum(1 for d in days
                     if d["chains"] and all(d["chain_confidence"].get(c) == "confirmed"
                                            for c in d["chains"]))
    print(f"content/chains.json：{len(out_chains)} 条链条、{len(payload['handoffs'])} 条交接")
    print(f"content/journal/：{written} 个文件，{reviewed_n} 天归属已确认、"
          f"{written - reviewed_n} 天待你过目")
    print(f"最后一天 {last_day}；"
          f"status=active 的链条 {sum(1 for c in out_chains if c['status'] == 'active')} 条")
    return 0


sys.exit(main())
