"""保留上一轮草稿，另生成B方向的对比预览。"""
from pathlib import Path
import json

base = Path(__file__).resolve().parent
project = base.parents[2]
manifest = json.loads((project / "dist/manifest.json").read_text(encoding="utf-8"))
ordered = [c for t in manifest["chains"]["tracks"] for c in manifest["chains"]["chains"] if c["track"] == t["id"]]
source = {
    "tracks": [{"id": t["id"], "label": t["label"]} for t in manifest["chains"]["tracks"]],
    "chains": [{k: c[k] for k in ("id", "short", "track")} for c in ordered],
    "days": [{"date": d["date"], "chains": d["chains"], "notes": d["chain_notes"], "weights": d["chain_weights"], "report": bool(d["report"])} for d in manifest["journal"] if "2026-10-14" <= d["date"] <= "2026-10-21"],
}
path = base / "inline-day.fragment.html"
fragment = path.read_text(encoding="utf-8")
marker = '<script type="application/json" id="jpd-bplus-data">'
start = fragment.index(marker) + len(marker)
end = fragment.index("</script>", start)
fragment = fragment[:start] + json.dumps(source, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + fragment[end:]
path.write_text(fragment, encoding="utf-8")
visual = Path("C:/Users/19927/.codex/visualizations/2026/10/22/01a16151-032a-7583-b97f-0e92d18fb860/inline-day-expansion.html")
visual.write_text(fragment, encoding="utf-8")
print("B+ draft ready")
