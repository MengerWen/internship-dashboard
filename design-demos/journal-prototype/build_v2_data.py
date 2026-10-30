# -*- coding: utf-8 -*-
"""竖向原型的数据（throwaway）。直接读已实现的 dist/manifest.json 与证据 JSON，
按轨道分组做泳道打包，并为每个 (日, 链) 起草一条注解——注解全部标为草稿。"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "v2-data.js"

# 宏观「后来没被采用」的候选，来自提交信息与 PLAN 标题的实测（见 v2 PLAN 第 1 节第 5 条）
DROPPED = {
    ("2026-07-01", "literature"): "当天「转向：检测踪迹」，前面几篇复现没有进入后续因子线",
    ("2026-07-10", "algobench"): "当天提交写明「弯路……」，随后改方向重写计划",
    ("2026-07-15", "doris-migration"): "两份 Doris 数据访问计划的标题后来被改成 Superseded",
    ("2026-07-29", "gates"): "决定取消价格硬门，改用 Xq=10% 硬数量门",
    ("2026-09-03", "open5m"): "取消定标候选边物化",
}
CHAIN_FATE = {"literature": "dropped"}


def clean(text: str) -> str:
    text = re.sub(r"^(Superseded:|feat|fix|perf|docs|test|chore|refactor|merge|bench)\s*[:(]?\s*", "", text)
    text = re.sub(r"\s*2[0-9]\.\d+\.\d+\s*\d*:?\d*$", "", text)
    return text.strip(" ：:")[:26]


def main() -> None:
    manifest = json.loads((ROOT / "dist/manifest.json").read_text(encoding="utf-8"))
    days = manifest["journal"]
    reg = manifest["chains"]
    chains = {c["id"]: c for c in reg["chains"]}

    # 泳道打包：按轨道分组，组内按首次出现排序、结束即回收
    active: dict[str, list[str]] = {}
    for d in days:
        for c in d["chains"]:
            active.setdefault(c, []).append(d["date"])
    lane, base = {}, 0
    track_span = []
    for track in reg["tracks"]:
        ids = sorted((c["id"] for c in reg["chains"]
                      if c["track"] == track["id"] and c["id"] in active),
                     key=lambda c: active[c][0])
        free: list[str | None] = []
        for cid in ids:
            first, last = active[cid][0], active[cid][-1]
            slot = next((i for i, end in enumerate(free) if end is None or end < first), None)
            if slot is None:
                slot = len(free)
                free.append(None)
            free[slot] = last
            lane[cid] = base + slot
        if free:
            track_span.append({"id": track["id"], "label": track["label"],
                               "from": base, "to": base + len(free) - 1})
            base += len(free)
    lanes_total = base

    # 为每个 (日, 链) 起草注解
    out_days = []
    for d in days:
        ev_path = ROOT / "content/journal/_evidence" / f"{d['date']}.json"
        ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else {}
        plans = ev.get("plans", [])
        subjects = [i["subject"] for r in ev.get("repos", []) for i in r.get("items", [])]
        notes = []
        for idx, cid in enumerate(d["chains"]):
            token = cid.split("-")[0].lower()
            hit = next((p["title"] for p in plans if token in p["file"].lower()), None)
            if hit is None and len(d["chains"]) == 1 and plans:
                hit = plans[0]["title"]
            if hit is None and idx < len(subjects):
                hit = subjects[idx]
            note = clean(hit or d["headline"])
            entry = {"id": cid, "note": note, "draft": True}
            dropped = DROPPED.get((d["date"], cid))
            if dropped:
                entry["outcome"] = "dropped"
                entry["outcome_note"] = dropped
            notes.append(entry)
        out_days.append({
            "date": d["date"], "weekday": d["weekday"], "headline": d["headline"],
            "headline_source": d["headline_source"], "total_commits": d["total_commits"],
            "notes": notes,
            "plans": [{"file": x["file"], "title": x["title"]} for x in plans],
            "repos": [{"repo": r["repo"], "commits": r["commits"],
                       "items": [i["subject"] for i in r.get("items", [])[:6]]}
                      for r in ev.get("repos", [])],
            "covering": d.get("reports_covering", []), "published": d.get("reports_published", []),
        })

    payload = {
        "tracks": track_span,
        "lanes": lanes_total,
        "chains": [{"id": c["id"], "short": c["short"], "label": c["label"],
                    "track": c["track"], "lane": lane.get(c["id"]),
                    "span": [active[c["id"]][0], active[c["id"]][-1]] if c["id"] in active else None,
                    "days": len(active.get(c["id"], [])),
                    "fate": CHAIN_FATE.get(c["id"], "landed")}
                   for c in reg["chains"] if c["id"] in active],
        "handoffs": reg["handoffs"],
        "days": out_days,
    }
    OUT.write_text("window.V2 = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("天数", len(out_days), "链条", len(payload["chains"]), "泳道", lanes_total)
    print("轨道泳道区间", [(t["label"], t["from"], t["to"]) for t in track_span])
    print("注解草稿", sum(len(d["notes"]) for d in out_days), "条；未采用标记", len(DROPPED), "处")


main()
