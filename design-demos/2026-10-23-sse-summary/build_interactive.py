from pathlib import Path
import csv
import html
import json
import re

ROOT = Path(__file__).resolve().parent
FACTS = ROOT / "source-content.json"
if not FACTS.exists():
    original = (ROOT / "dir-a.html").read_text(encoding="utf-8")
    chapters = re.findall(r'<section class="chapter" id="([^"]+)"><h2>(.*?)</h2><div class="chapter-content">(.*?)</div></section>', original, re.S)
    if len(chapters) != 9:
        raise ValueError("Expected nine verified source chapters")
    FACTS.write_text(json.dumps({key: {"title": title, "body": body} for key, title, body in chapters}, ensure_ascii=False), encoding="utf-8")

source = json.loads(FACTS.read_text(encoding="utf-8"))
research = Path(r"D:\MG\！Internship\26 Summer\❗思瑞投资\sirui-quant-research")
error_path = research / "reports/2026-10/2026-10-23-sse-adapter-closure-evidence/q-equity-errors.csv"
with error_path.open(encoding="utf-8-sig", newline="") as handle:
    errors = list(csv.DictReader(handle))
for row in errors:
    for key, value in tuple(row.items()):
        if key not in ("column", "scale_rule", "zero_scale"):
            row[key] = float(value) if value else None
    row["zero_scale"] = row["zero_scale"] == "True"

closure = (research / "reports/2026-10/2026-10-23-sse-adapter-closure.md").read_text(encoding="utf-8")
mechanisms = {}
for line in closure.splitlines():
    if line.startswith("|f") and ("【事实】" in line or "【推测】" in line):
        cells = line.strip("|").split("|")
        mechanisms[cells[0]] = cells[-1]
data = json.dumps({"source": source, "errors": errors, "mechanisms": mechanisms}, ensure_ascii=False).replace("</", "<\\/")
css = (ROOT / "interactive.css").read_text(encoding="utf-8")
js = (ROOT / "interactive.js").read_text(encoding="utf-8")
modes = {"a": "分页图解", "b": "流程工作台", "c": "案例实验室"}
for key, label in modes.items():
    nav = ''.join(f'<a href="dir-{k}.html"'+(' aria-current="page"' if k == key else '')+f'>{k.upper()} {v}</a>' for k, v in modes.items())
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>26.10.23 沪市原始委托还原｜{label}</title><style>{css}</style></head><body data-mode="{key}"><header class="topbar"><a class="report-name" href="index.html">26.10.23　沪市原始委托还原</a><nav aria-label="设计方案">{nav}</nav><button type="button" class="plain" data-action="sources">技术与证据</button></header><main id="app"></main><dialog id="evidence-dialog" aria-labelledby="evidence-title"><div class="dialog-head"><h2 id="evidence-title">技术与证据</h2><button type="button" class="plain" data-action="close-dialog">关闭</button></div><div id="evidence-body"></div></dialog><noscript><main class="fallback"><h1>沪市原始委托还原</h1><p>公开输入与适配器真值回环已通过；沪市独立定参与正式因子生产待推进。</p>{''.join('<section><h2>'+v['title']+'</h2>'+v['body']+'</section>' for v in source.values())}</main></noscript><script type="application/json" id="report-data">{data}</script><script>{js}</script></body></html>'''
    (ROOT / f"dir-{key}.html").write_text(document, encoding="utf-8")

cards = [
    ("a", "A 分页图解", "逐页回答一个问题，主图先解释，翻页推进全貌。", "11 个主题页；订单逐步回放、匹配前后对照、回环路径和误差图。"),
    ("b", "B 流程工作台", "整条研究链始终可见，点击节点查看机制、证据与交接。", "适合按问题跳读；区分研究线、实施线和后续定参，节点可打开完整图解。"),
    ("c", "C 案例实验室", "先动手看一笔订单，再把例子放回项目全景。", "6 个案例，区分示意与真实样本；另有全景、验收和定参入口。"),
]
card_html = ''.join(f'<section class="proposal"><h2>{title}</h2><p>{intro}</p><a href="dir-{key}.html"><img src="screenshots/v2-{key}.png" alt="{title}的真实浏览器截图"></a><p class="fine">{detail}</p><a class="primary" href="dir-{key}.html">打开 {key.upper()}</a></section>' for key, title, intro, detail in cards)
gallery = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>沪市还原：三种交互式汇报</title><style>{css}</style></head><body><header class="topbar"><span class="report-name">26.10.23　沪市原始委托还原</span><span>交互与图解方案评审</span></header><main class="gallery"><h1>用图解解释，用交互追问</h1><p class="gallery-intro">同一份已核实的项目内容，三种不同阅读方式。每版都能看到前序深市规则、本项公开适配与后续沪市定参的衔接。</p><div class="proposals">{card_html}</div><section class="gallery-guide"><h2>这轮可以直接试的内容</h2><div class="guide-links"><a href="dir-a.html#scene=1">订单逐条发布与盘口变化</a><a href="dir-a.html#scene=4">为什么“匹配前删掉”会改变结果</a><a href="dir-a.html#scene=6">S / H 两条验收路径</a><a href="dir-a.html#scene=8">消息时钟与误差分布</a><a href="dir-a.html#scene=9">沪市定参怎样接到因子生产</a></div><p class="fine">建议 A 作为汇报主体，C 的案例作为讲解入口。原始字段、完整限制、参数表和报告链接均在“技术与证据”中；示意数据明确标注，不冒充实测。</p></section></main></body></html>'''
(ROOT / "index.html").write_text(gallery, encoding="utf-8")
print(json.dumps({"mode": "interactive", "files": ["dir-a.html", "dir-b.html", "dir-c.html", "index.html"], "error_columns": len(errors)}, ensure_ascii=False))
