"""Build the standalone 2026-10-25 SSE reconstruction and calibration report (restructured edition)."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/sse_report_20261025"
# Frozen 352-column clock errors, mechanisms and factor names from the 10-23 authoring data.
HISTORY = ROOT / "scripts/sse_reconstruction_report_20261023/data.json"
OUTPUT = ROOT / "content/daily/2026-10-25.show.html"
FONTS = {
    ("ReportSerif", 400): "NotoSerifSC-Regular.woff2",
    ("ReportSerif", 700): "NotoSerifSC-Bold.woff2",
    ("ReportNum", 400): "LibreBaskerville-Regular.woff2",
}
TITLE = "26.10.25 沪市委托还原已验收，进入独立定参"
DESCRIPTION = "沪市原始委托还原汇报（2026-10-25）：为什么要还原、还原规则、三类验收、公开口径对因子值的影响、340 列独立定参方法、单日试算结果、f26 门槛风险与下一步。"


def font_fingerprint() -> str:
    return hashlib.sha256(b"".join((ROOT / "site/fonts" / name).read_bytes() for name in FONTS.values())).hexdigest()


def font_face(family: str, weight: int, text: str) -> str:
    font = TTFont(ROOT / "site/fonts" / FONTS[(family, weight)], recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    worker = subset.Subsetter(options=options)
    worker.populate(text=text)
    worker.subset(font)
    buffer = io.BytesIO()
    font.flavor = "woff2"
    font.save(buffer)
    font.close()
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"@font-face{{font-family:{family};src:url(data:font/woff2;base64,{encoded}) format('woff2');font-weight:{weight};font-display:swap}}"


def report_data() -> dict:
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    local = json.loads((SOURCE / "data.json").read_text(encoding="utf-8"))
    errors = history["errors"]
    assert len(errors) == 352
    assert sum(row["zero_scale"] for row in errors) == 6
    assert sum(row["changed"] > 0 for row in errors) == 272
    values = [row["scaled_p99"] for row in errors if not row["zero_scale"]]
    assert sum(v == 0 for v in values) == 74
    assert [sum(lo < v <= hi for v in values) for lo, hi in [(1e-4, 1e-3), (1e-3, 1e-2), (1e-2, 1e-1)]] == [70, 159, 43]
    assert max(values) < 0.1
    groups = history["calibration_groups"]
    assert len(groups) == len(local["groups"]) == 8
    merged_groups = []
    for plain, (name, how, note) in zip(local["groups"], groups):
        assert name.startswith(plain["code"] + " · ") and name.endswith(plain["name"]), name
        merged_groups.append({**plain, "how": how, "note": note})
    assert sum(row[1] for row in local["days"]) == 1335 and sum(row[2] for row in local["days"]) == 4
    assert sum(row[1] for row in local["ledger"]) == 67862452
    return {
        "errors": [
            [row["column"], None if row["zero_scale"] else row["scaled_p99"], None if row["zero_scale"] else row["scaled_max"],
             None if row["zero_scale"] else row["spearman"], int(row["changed"]), bool(row["zero_scale"])]
            for row in errors
        ],
        "mechanisms": history["mechanisms"],
        "factorNames": history["factor_names"],
        "days": local["days"],
        "ledger": local["ledger"],
        "groups": merged_groups,
        "sources": local["sources"],
        "currentResearch": local["current_research"],
    }


def build() -> str:
    page = (SOURCE / "page.html").read_text(encoding="utf-8")
    css = (SOURCE / "report.css").read_text(encoding="utf-8")
    js = (SOURCE / "report.js").read_text(encoding="utf-8")
    data = report_data()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    all_text = TITLE + page + js + payload + "0123456789,.%×−+=≤≥～·—"
    faces = "\n".join(font_face(family, weight, all_text) for family, weight in FONTS)
    document = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="report-font-fingerprint" content="{font_fingerprint()}">
<meta name="description" content="{DESCRIPTION}">
<title>{TITLE}</title>
<style>
{faces}
{css}
</style>
</head>
<body data-report="sse-reconstruction-20261025">
{page}
<script type="application/json" id="report-data">{payload}</script>
<script>
{js}
</script>
</body>
</html>
'''
    assert not re.search(r"<(?:script|link|img)\b[^>]*(?:src|href)=[\"'](?:https?:|\.\./)", document)
    assert not re.search(r"url\([\"']?(?:https?:|\.\./)", document)
    assert "localStorage" not in js and "fetch(" not in js
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed page differs from the sources")
    args = parser.parse_args()
    document = build()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != document:
            raise SystemExit("Report differs from the authoring sources")
        print("Report matches the authoring sources")
        return
    OUTPUT.write_text(document, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(document.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
