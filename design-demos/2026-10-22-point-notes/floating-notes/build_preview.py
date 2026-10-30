"""用当前原始记录生成图内浮窗草稿，保留旧版方案。"""
from pathlib import Path
import json

base = Path(__file__).resolve().parent
project = base.parents[2]
manifest = json.loads((project / "dist/manifest.json").read_text(encoding="utf-8"))
registry = manifest["chains"]
source = {
    "tracks": [{k: t[k] for k in ("id", "label")} for t in registry["tracks"]],
    "chains": [{k: c.get(k) for k in ("id", "short", "label", "track", "fate", "status", "start", "end")} for t in registry["tracks"] for c in registry["chains"] if c["track"] == t["id"]],
    "handoffs": [{k: e.get(k) for k in ("from", "to", "type", "date", "source_date", "confidence")} for e in registry["handoffs"]],
    "days": [{"date": d["date"], "weekday": d["weekday"], "chains": d["chains"], "notes": d["chain_notes"], "weights": d.get("chain_weights", {}), "report": bool(d.get("reports_covering") or d.get("report")), "published": len(d.get("reports_published", []))} for d in manifest["journal"]],
}
path = base / "floating-notes.fragment.html"
fragment = path.read_text(encoding="utf-8")
marker = '<script type="application/json" id="jpf-data">'
start = fragment.index(marker) + len(marker)
end = fragment.index("</script>", start)
fragment = fragment[:start] + json.dumps(source, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + fragment[end:]
path.write_text(fragment, encoding="utf-8")
target = Path("C:/Users/19927/.codex/visualizations/2026/10/22/01a16151-032a-7583-b97f-0e92d18fb860/floating-chain-notes.html")
target.write_text(fragment, encoding="utf-8")
print(f"Draft ready: {len(fragment.encode('utf-8'))} bytes; {len(source['chains'])} chains")
