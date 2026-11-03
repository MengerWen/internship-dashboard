"""复用既有阅读层，将全链五版打包为无后台服务的对话预览。"""
from __future__ import annotations

import argparse
import re
import runpy
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMMON = HERE.parent / "2026-11-03-journal-layouts"
NAMES = {"A": "全链竖轴图谱", "B": "全链横轴年表", "C": "七区平铺图谱", "D": "全链研究墙", "E": "链与月份矩阵"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    scope = runpy.run_path(str(COMMON / "build_inline.py"), run_name="preview_helpers")["scope_css"]
    tokens = (HERE.parents[1] / "site/css/tokens.css").read_text(encoding="utf-8")
    css = tokens[tokens.index(":root {"):].replace(":root", "#journal-demo-choice .jd-product", 1)
    css += "\n" + scope((COMMON / "shared.css").read_text(encoding="utf-8"))
    for path in sorted((HERE / "variants").glob("*.css")):
        css += "\n" + scope(path.read_text(encoding="utf-8"))
    css += "\n#journal-demo-choice .jd-product{box-sizing:border-box;height:940px;overflow:auto;background:var(--bg);color:var(--text);font:14px/1.7 var(--font-body)}\n"
    css += "#journal-demo-choice .jd-demo-root{max-width:1424px;min-height:560px;padding:24px 26px 40px;margin:auto}\n"
    css += "#journal-demo-choice .jd-reading-layer{height:auto;overflow:visible;background:transparent}\n"
    css += "@media(max-width:760px){#journal-demo-choice .jd-demo-root{padding:22px 16px 36px}#journal-demo-choice .jd-product{font-size:16px}}\n"
    header = (HERE / "demo.html").read_text(encoding="utf-8").split('<header class="site-header">', 1)[1].split("</header>", 1)[0]
    header = '<header class="site-header">' + header.replace('href="index.html"', 'href="#journal-all-chains-choice"') + '</header>'
    stages = [f'<section data-variant="{name}" aria-label="{name}"{"" if key == "A" else " hidden"}><div class="jd-product" data-demo-variant="{key}">{header}<main class="jd-demo-root" id="jd-root-{key}"></main></div></section>' for key, name in NAMES.items()]
    scripts = (COMMON / "data.js").read_text(encoding="utf-8") + "\n" + (COMMON / "shared.js").read_text(encoding="utf-8")
    scripts += "\n" + (HERE / "config.js").read_text(encoding="utf-8")
    for path in sorted((HERE / "variants").glob("*.js")):
        scripts += "\n" + path.read_text(encoding="utf-8")
    template = (COMMON / "inline-template.html").read_text(encoding="utf-8")
    result = template.replace("/* DEMO_STYLES */", css).replace("<!-- DEMO_STAGES -->", "\n".join(stages)).replace("/* DEMO_SCRIPTS */", scripts.replace("</script", "<\\/script"))
    result = result.replace("journal-demo-choice", "journal-all-chains-choice")
    if len(result.encode("utf-8")) >= 1_000_000:
        raise ValueError("预览超出1MB")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    print(f"INLINE {output} / {len(result.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
