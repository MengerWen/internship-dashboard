"""将当前构建清单中的原始记录嵌入草稿，生成独立预览。"""
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
manifest = json.loads((PROJECT / "dist/manifest.json").read_text(encoding="utf-8"))
ordered = [c for track in manifest["chains"]["tracks"] for c in manifest["chains"]["chains"] if c["track"] == track["id"]]
source = {
    "tracks": [{"id": t["id"], "label": t["label"]} for t in manifest["chains"]["tracks"]],
    "chains": [{k: c[k] for k in ("id", "short", "track")} for c in ordered],
    "days": [{"date": d["date"], "chains": d["chains"], "notes": d["chain_notes"], "weights": d["chain_weights"], "report": bool(d["report"])} for d in manifest["journal"] if "2026-10-14" <= d["date"] <= "2026-10-21"],
}
fragment_path = BASE / "point-notes.fragment.html"
fragment = fragment_path.read_text(encoding="utf-8")
start = '<script type="application/json" id="jpd-source">'
a = fragment.index(start) + len(start)
b = fragment.index("</script>", a)
fragment = fragment[:a] + json.dumps(source, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + fragment[b:]
fragment_path.write_text(fragment, encoding="utf-8")
visual_dir = Path("C:/Users/19927/.codex/visualizations/2026/10/22/01a16151-032a-7583-b97f-0e92d18fb860")
visual_dir.mkdir(parents=True, exist_ok=True)
(visual_dir / "point-notes-drafts.html").write_text(fragment, encoding="utf-8")
(BASE / "source-data.json").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
print("已嵌入 %s 天、%s 条任务链的原始记录。" % (len(source["days"]), len(source["chains"])))
