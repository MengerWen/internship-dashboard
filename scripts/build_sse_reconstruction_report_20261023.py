"""Build the standalone 2026-10-25 SSE reconstruction and calibration report."""
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
SOURCE = ROOT / "scripts/sse_reconstruction_report_20261023"
OUTPUT = ROOT / "content/daily/2026-10-25.show.html"
FONT_FILES = {400: "NotoSerifSC-Regular.woff2", 700: "NotoSerifSC-Bold.woff2"}


def font_fingerprint() -> str:
    return hashlib.sha256(b"".join((ROOT / "site/fonts" / name).read_bytes() for name in FONT_FILES.values())).hexdigest()


def font_face(weight: int, text: str) -> str:
    name = FONT_FILES[weight]
    font = TTFont(ROOT / "site/fonts" / name, recalcTimestamp=False)
    if OUTPUT.exists():
        current = OUTPUT.read_text(encoding="utf-8")
        if f'<meta name="report-font-fingerprint" content="{font_fingerprint()}">' in current:
            pattern = rf"@font-face\{{font-family:ReportSerif;src:url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\) format\('woff2'\);font-weight:{weight};font-display:swap\}}"
            face = re.search(pattern, current)
            if face:
                embedded = TTFont(io.BytesIO(base64.b64decode(face.group(1))))
                needed = {ord(c) for c in text} & set(font.getBestCmap())
                covered = needed <= set(embedded.getBestCmap())
                embedded.close()
                if covered:
                    font.close()
                    return face.group(0)
    options = subset.Options()
    options.flavor = "woff2"
    worker = subset.Subsetter(options=options)
    worker.populate(text=text)
    worker.subset(font)
    buffer = io.BytesIO()
    font.flavor = "woff2"
    font.save(buffer)
    font.close()
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"@font-face{{font-family:ReportSerif;src:url(data:font/woff2;base64,{encoded}) format('woff2');font-weight:{weight};font-display:swap}}"


def build() -> str:
    data = json.loads((SOURCE / "data.json").read_text(encoding="utf-8"))
    assert len(data["errors"]) == 352
    assert sum(row["zero_scale"] for row in data["errors"]) == 6
    values = [row["scaled_p99"] for row in data["errors"] if row["scaled_p99"] is not None]
    counts = [sum(v <= 1e-4 for v in values)]
    counts.extend(sum(lo < v <= hi for v in values) for lo, hi in [(1e-4, 1e-3), (1e-3, 1e-2), (1e-2, 1e-1)])
    counts.append(sum(v > 1e-1 for v in values))
    assert counts == [74, 70, 159, 43, 0]
    assert len(data["mechanisms"]) == 20
    assert sum(row["changed"] > 0 for row in data["errors"]) == 272

    js = "\n".join((SOURCE / name).read_text(encoding="utf-8") for name in ["report.js", "comparison.js", "clock.js", "reader.js"])
    css = "\n".join((SOURCE / name).read_text(encoding="utf-8") for name in ["report.css", "reader.css"])
    css = re.sub(r"@font-face\{[^}]*\}\s*", "", css)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    title = "26.10.25 沪市原始委托还原：输入验收、能力边界与独立定参计划"
    header = '<header class="topbar"><span class="report-name"><span class="reader-date">26.10.25</span>　沪市原始委托还原与定参计划</span><nav class="view-nav" aria-label="阅读方式"><button type="button" data-action="view" data-value="story" aria-pressed="true">分页主线</button><button type="button" data-action="view" data-value="cases" aria-pressed="false">六个案例</button></nav><button type="button" class="plain" data-action="glossary">术语短解</button><button type="button" class="plain" data-action="sources">技术与证据</button></header><div id="reading-state" class="reading-state" role="status" aria-live="polite">主线 1 / 14：项目总结果</div>'
    fallback = f'<h1>{title}</h1><p>补充至 2026-10-25：真实沪市 13 日分层输入验收已完成；340 列独立定参仍在计划审核，第六核建议待审；正式因子计算尚未启动。</p>' + "".join(f'<section><h2>{v["title"]}</h2>{v["body"]}</section>' for v in data["source"].values())
    all_text = title + header + js + payload + fallback
    faces = "\n".join(font_face(w, all_text) for w in (400, 700))
    document = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="report-font-fingerprint" content="{font_fingerprint()}">
<meta name="description" content="沪市原始委托还原汇报，补充至2026年10月25日：公开输入验收、剩余差异与能力边界、340列独立定参计划及f26阈值和窗口尾部诊断。">
<title>{title}</title>
<style>
{faces}
{css}
</style>
</head>
<body data-report="sse-reconstruction-20261025">
{header}
<main id="app" aria-label="项目汇报"></main>
<dialog id="evidence-dialog" aria-labelledby="evidence-title"><div class="dialog-head"><h2 id="evidence-title">技术与证据</h2><button type="button" class="plain" data-action="close-dialog">关闭</button></div><div id="evidence-body"></div></dialog>
<noscript><div class="fallback">{fallback}</div></noscript>
<article class="print-report" aria-hidden="true">{fallback}</article>
<script type="application/json" id="report-data">{payload}</script>
<script>
{js}
</script>
</body>
</html>
'''
    assert "dir-a.html" not in document and "dir-c.html" not in document
    assert "方案初稿" not in document and "本地生成预览" not in document
    assert not re.search(r"<(?:script|link|img)\b[^>]*(?:src|href)=[\"'](?:https?:|\.\./)", document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != document:
            raise SystemExit("Report differs from the authoring sources")
        print("Report matches the frozen sources")
    else:
        OUTPUT.write_text(document, encoding="utf-8", newline="\n")
        print(f"Wrote {OUTPUT.name}: {len(document.encode('utf-8')):,} bytes; 14 chapters, 6 cases, 352 error rows")


if __name__ == "__main__":
    main()
