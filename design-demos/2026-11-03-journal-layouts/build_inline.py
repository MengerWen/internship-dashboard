"""将相同五版原型打包为不启动服务的对话内预览。"""
from __future__ import annotations

import argparse
import re
from html import escape
from pathlib import Path


HERE = Path(__file__).resolve().parent
NAMES = {"A": "方向总览", "B": "按日日志", "C": "链条工作台", "D": "阶段章节", "E": "月历日程"}


def scope_css(css: str) -> str:
    def rewrite(match):
        header = match.group(1)
        if header.strip().startswith("@"):
            return header + "{"
        selectors = []
        for raw in header.split(","):
            selector = raw.strip()
            selector = re.sub(r'body\[data-variant="([A-E])"\]', r'.jd-product[data-demo-variant="\1"]', selector)
            selector = selector.replace("#demo-root", ".jd-demo-root")
            selector = re.sub(r"(?<![\w-])body(?=[.#\[:\s>+~]|$)", ".jd-product", selector)
            selector = re.sub(r"(?<![\w-])html(?=[.#\[:\s>+~]|$)", ".jd-product", selector)
            if not selector.startswith(".jd-product"):
                selector = ".jd-product " + selector
            selectors.append("#journal-demo-choice " + selector)
        return "\n" + ",".join(selectors) + " {"
    return re.sub(r"([^{}]+)\{", rewrite, css)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    tokens = (HERE.parents[1] / "site/css/tokens.css").read_text(encoding="utf-8")
    token_rules = tokens[tokens.index(":root {"):].replace(":root", "#journal-demo-choice .jd-product", 1)
    css = token_rules + "\n" + scope_css((HERE / "shared.css").read_text(encoding="utf-8"))
    for path in sorted((HERE / "variants").glob("*.css")):
        css += "\n" + scope_css(path.read_text(encoding="utf-8"))
    css += "\n#journal-demo-choice .jd-product{box-sizing:border-box;height:940px;overflow:auto;background:var(--bg);color:var(--text);font:14px/1.7 var(--font-body)}\n"
    css += "#journal-demo-choice .jd-demo-root{max-width:1424px;min-height:560px;padding:28px 28px 48px;margin:auto}\n"
    css += "#journal-demo-choice .jd-reading-layer{height:auto;overflow:visible;background:transparent}\n"
    css += "@media(max-width:760px){#journal-demo-choice .jd-demo-root{padding:22px 16px 36px}#journal-demo-choice .jd-product{font-size:16px}}\n"
    header = (HERE / "demo.html").read_text(encoding="utf-8").split('<header class="site-header">', 1)[1].split("</header>", 1)[0]
    header = '<header class="site-header">' + header.replace('href="index.html"', 'href="#journal-demo-choice"') + '</header>'
    stages = []
    for key, name in NAMES.items():
        hidden = "" if key == "A" else " hidden"
        stages.append(f'<section data-variant="{escape(name)}" aria-label="{escape(name)}"{hidden}><div class="jd-product" data-demo-variant="{key}">{header}<main class="jd-demo-root" id="jd-root-{key}"></main></div></section>')
    scripts = (HERE / "data.js").read_text(encoding="utf-8") + "\n" + (HERE / "shared.js").read_text(encoding="utf-8")
    for path in sorted((HERE / "variants").glob("*.js")):
        scripts += "\n" + path.read_text(encoding="utf-8")
    scripts = scripts.replace("</script", "<\\/script")
    template = (HERE / "inline-template.html").read_text(encoding="utf-8")
    result = template.replace("/* DEMO_STYLES */", css).replace("<!-- DEMO_STAGES -->", "\n".join(stages)).replace("/* DEMO_SCRIPTS */", scripts)
    if len(result.encode("utf-8")) >= 1_000_000:
        raise ValueError("预览超出1MB，请缩减内容后再导出")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    print(f"INLINE {output} / {len(result.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
