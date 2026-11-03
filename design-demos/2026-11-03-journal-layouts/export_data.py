"""从正式日志导出五版共用的内容快照，不修改正式内容。"""
from __future__ import annotations

import json
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    registry = json.loads((ROOT / "content/chains.json").read_text(encoding="utf-8"))
    days = []
    for path in sorted((ROOT / "content/journal").glob("*.md")):
        meta = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
        days.append({
            "date": str(meta["date"]), "headline": meta["headline"],
            "highlights": meta.get("highlights", []),
            "chains": [{**item, "outcome": item.get("outcome", "")} for item in meta["chains"]],
            "reports": [str(day) for day in meta.get("reports_covering", [])],
        })
    chains = [{key: chain.get(key) for key in (
        "id", "track", "label", "short", "purpose", "status", "fate", "fate_note", "source_refs"
    )} for chain in registry["chains"]]
    data = {
        "tracks": registry["tracks"], "chains": chains, "days": days,
        "handoffs": [{key: edge.get(key) for key in (
            "from", "to", "type", "date", "source_date", "note"
        )} for edge in registry["handoffs"]],
        "asOf": days[-1]["date"],
        "counts": {"tracks": len(registry["tracks"]), "chains": len(chains),
                   "days": len(days), "points": sum(len(day["chains"]) for day in days)},
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (HERE / "data.js").write_text("/* 由 export_data.py 从正式日志生成。 */\nwindow.JOURNAL_DATA=" + payload + ";\n", encoding="utf-8")
    print(json.dumps({"asOf": data["asOf"], **data["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
