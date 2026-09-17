"""Build the September 16 factor evaluation atlas and local data assets."""
import base64
import gzip
import html
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'content/assets/raw-bank-2026-09-16'
data=json.loads(gzip.decompress(Path(sys.argv[1]).read_bytes()))
details=json.loads(gzip.decompress(Path(sys.argv[2]).read_bytes()))
proof=json.loads((ASSETS/'evidence/evaluation_result.json').read_bytes())
detail_proof=json.loads((ASSETS/'evidence/details-result.json').read_bytes())
assert hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()==proof['report_sha256']==detail_proof['original_report_sha256']
assert hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()==detail_proof['details_sha256']
definitions=json.loads((ASSETS/'definitions.json').read_bytes())
data['definitions']=definitions
data['label_alignment']=json.loads((ASSETS/'evidence/label_alignment.json').read_bytes())
factor_dir=ASSETS/'factors'
factor_dir.mkdir(exist_ok=True)
for factor in data['factors']:
    factor['details']=details[factor['metadata']['factor_id']]
    alias=factor['metadata']['factor_id'].split('__')[0]+'__'+factor['metadata']['projection']
    packed=base64.b64encode(gzip.compress(json.dumps(factor,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0)).decode()
    (factor_dir/(alias+'.js')).write_text('window.rawbankFactorLoaded('+json.dumps(alias)+','+json.dumps(packed)+');',encoding='utf-8')
data['factors']=[{**{key:factor[key] for key in ('metadata','diagnostic','distribution')},'periods':[{key:p[key] for key in ('ic','spread')} for p in factor['periods']]} for factor in data['factors']]
payload=base64.b64encode(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0)).decode()
css=re.search(r'<style>(.*?)</style>',(ROOT/'content/daily/2026-09-07.show.html').read_text(encoding='utf-8'),re.S)[1]
css+='''
.inventory{grid-template-columns:360px minmax(0,1fr)}.factor-list .factor-item{display:block;overflow-wrap:anywhere}.factor-item small{font-size:11px}.factor-list{max-height:770px}.detail svg{width:100%;height:auto}.plot-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.plot-card{border:1px solid var(--rule);padding:12px;min-width:0}.plot-card h4{font-size:13px;margin:0}.detail-pane[hidden]{display:none!important}.tree-label{background:#e7eee8;padding:9px 12px;font-size:12px;color:var(--teal);position:sticky;top:0}.loading{padding:40px;color:var(--muted)}.status{font-size:12px;color:var(--rust)}.factor-item .item-id{display:block;font-size:11px}.metric b{overflow-wrap:anywhere}.scroll-table{max-height:520px;overflow:auto}.scroll-table th{position:sticky;top:0}#all-results button{font-size:11px;padding:4px 7px}.selected-name{font-size:18px!important;overflow-wrap:anywhere}.download-row a{font-size:12px}.chart-note{font-size:11px;color:var(--muted)}
@media(max-width:900px){.inventory{grid-template-columns:290px minmax(0,1fr)}.plot-grid{grid-template-columns:1fr}}
@media(max-width:700px){.inventory{grid-template-columns:1fr}.factor-list{max-height:300px}.plot-grid{grid-template-columns:1fr}.controls label{flex:1 1 140px}}
'''
css+=(ROOT/'scripts/rawbank_explorer.css').read_text(encoding='utf-8')
template='''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="284列正式因子与4列诊断指标的601日完整评价：IC、Rank IC、10/40分组收益及分期结果。"><title>开盘五分钟的订单行为｜全部因子的 601 日评价</title><style>__CSS__</style></head><body>
<header><div class="wrap"><div class="mast"><span>思瑞投资 · 量化研究</span><span>研究归档 2026.09.16 · 评价完成 2026.09.17</span></div><div class="hero"><div><div class="eyebrow">OPEN5M / FULL FACTOR BANK</div><h1>开盘五分钟，<br><em>订单行为与后续收益</em></h1><p class="subtitle">全部因子的 601 日完整评价</p><p class="lead">从撤单、重挂、订单链到盘口响应，把原始行为证据投影到买卖两侧，再观察它们与同日短窗口收益的关系。每一列都保留覆盖率、日度 IC、分期统计和分组形状。</p></div><aside class="hero-note"><div><strong>284 + 4</strong><small>正式因子列 + 诊断指标列</small></div><div><strong>601</strong><small>2024.01.02 — 2026.06.30</small></div></aside></div><div class="stats"><span><b>1,719,612</b>股票日</span><span><b>44</b>评价区间</span><span><b>10 / 40</b>等秩分组</span><span><b>100</b>固定定义域分箱</span></div></div></header>
<nav class="nav"><div class="wrap"><a href="#definition">01 因子构造</a><a href="#contract">02 收益与样本</a><a href="#results">03 全部结果</a><a href="#factors">04 因子浏览</a><a href="#evidence">05 证据与下载</a></div></nav><main class="wrap">
<section id="definition"><div class="section-head"><span class="num">01</span><div><h2>从行为证据到股票日因子</h2><p class="subtle">因子描述 L2 可观测行为，不能据此确认交易者身份或真实交易目的。</p></div></div><div class="table-scroll"><table><thead><tr><th>层次</th><th>构造与观察问题</th><th>结果含义</th></tr></thead><tbody><tr><td>L1 基础评分投影</td><td>撤单、重挂、订单链及盘口响应等已有评分，分别汇总买侧和卖侧。</td><td>某类行为在全部有效新委托中的强度。</td></tr><tr><td>L2 多证据共识</td><td>整合生命周期、重挂、订单链、事件响应证据，保留并集与交集等定义。</td><td>不同证据的共同出现和综合强度。</td></tr><tr><td>L3 微观结构情境</td><td>行为证据与价差、队列、深度、订单流、趋势等提交时情境相互作用。</td><td>某种盘口情境下的行为强度。</td></tr><tr><td>L4 股票日窗口状态</td><td>行为证据与前五分钟的价格路径、成交、价差、深度状态结合。</td><td>特定市场状态下的行为强度。</td></tr><tr><td>L5 用途与流动性机制</td><td>做市、主动执行、逆向吸收、撤退、补充等机制代理及组合。</td><td>与某类用途一致的观测代理。</td></tr><tr><td>诊断指标</td><td>4 列市场行为指标，保留总量投影。</td><td>辅助理解样本，不计入 284 列正式因子。</td></tr></tbody></table></div><div class="formula">F<sub>s,d</sub> = Σ（方向内的订单贡献） / N<sub>d</sub><small>N 为股票日窗口内全部有效、去重的新委托数。买卖侧共用分母；具体贡献、窗口状态和特殊组合遵循冻结注册表。浏览器内展示每列的注册身份与来源。</small></div><div class="note"><p>本批因子沿用冻结的 R19 参数，不使用收益标签重新定标。未知证据与真正的零值分开处理；浏览结果时需同时看有限值覆盖率、零值占比和常数截面天数。</p></div></section>
<section id="contract"><div class="section-head"><span class="num">02</span><div><h2>同日收益，日度等权</h2><p class="subtle">因子窗口 [09:30, 09:35)，收益窗口延伸到 [09:44, 09:45)。</p></div></div><div class="flow"><div><b>① 前五分钟</b><p>从有效新委托、成交和盘口事件提取行为因子。</p></div><div><b>② 起点价格</b><p>使用同一交易日 09:35 前最后一笔有效成交价。</p></div><div><b>③ 终点价格</b><p>使用同日 [09:44, 09:45) 的成交量加权平均价。</p></div></div><div class="formula">r = VWAP<sub>[09:44,09:45)</sub> / P<sub>&lt;09:35, last valid</sub> − 1</div><p>收益标签复用已封存的 601 日同口径文件，共 __VALID__ 个有效收益股票日。全部股票日键与本批因子逐日一一对应；每列评价使用该列因子与收益均有限的成对样本。</p><div class="two"><div><h3>IC 与 Rank IC</h3><p>每日横截面分别计算 Pearson 相关和 Spearman 秩相关；至少 30 个成对股票，常数截面不生成有效 IC。汇总对有效日等权，Newey–West 使用 Bartlett lag 1。</p></div><div><h3>分组收益</h3><p>按每日因子平均秩分成 10 或 40 组。相同因子值保持同组，可能出现空组；空组不填零。先算日内组均值，再对有效日期等权。超额收益减去该因子当日成对样本的平均收益。</p></div></div><div class="note warm"><p>这是 601 日历史样本内的观测评价。多个定义共享底层证据，筛选和排名存在多重比较影响。毛收益未扣交易成本；标签起点是价格基准，并不代表可按该价成交，也不等同于可执行的 A 股日内买卖策略。</p></div></section>
<section id="results"><div class="section-head"><span class="num">03</span><div><h2>全部结果放在一起看</h2><p class="subtle">默认按全期 |Rank IC| 排序。切换区间可比较年度、季度和月度表现。</p></div></div><div class="controls"><label>评价区间<select id="global-period"></select></label><label>结果范围<select id="result-scope"><option value="formal">284 列正式因子</option><option value="all">全部 288 列</option><option value="diagnostic">4 列诊断指标</option></select></label><label>排序<select id="result-sort"><option value="rank">|Rank IC|</option><option value="t">|Rank IC NW t|</option><option value="spread">|G10−G1|</option><option value="id">注册顺序</option></select></label><label>检索<input type="search" id="result-search" placeholder="编号、名称、机制"></label></div><p id="result-note" class="small">正在加载完整评价数据…</p><div id="all-results" class="table-scroll scroll-table"></div><div class="download-row"><button id="download-summary">下载当前区间全部结果 CSV</button></div></section>
__EXPLORER__
<section id="evidence"><div class="section-head"><span class="num">05</span><div><h2>数据身份与评价证据</h2><p class="subtle">归档日期为 9 月 16 日；全历史数值检查和收益评价于 9 月 17 日完成。</p></div></div><div class="table-scroll evidence"><table><tbody><tr><th>本次评价</th><td>601 日；284 正式列 + 4 诊断列；股票日键、文件哈希和分组计数通过；601 个因子日抽查复算与现有 IC 代码一致。</td></tr><tr><th>因子数据验收</th><td>601 日全部因子数值和逐日审核已完成，独立输出检查通过。原生产守护进程在最后汇总时超时退出，因此未把原生产运行标记为正常退出。</td></tr><tr><th>冻结参数</th><td><code>40513893b34f31abf82ea5c7e54aa5d3be15456169e05ef0a52cd84f68826f27</code></td></tr><tr><th>收益标签规格</th><td><code>638fa8814eaf79199adc1680500ecf1ec9a3e743ad9b5fbf47344b7cb441172c</code></td></tr><tr><th>评价代码</th><td>复用现有日度 IC、平均秩分组及标准误函数；逐日并行计算，保留完整精度下载数据。</td></tr></tbody></table></div><div class="download-row"><button id="download-proof">下载评价验收 JSON</button><button id="download-alignment">下载收益样本对齐 CSV</button><a href="../assets/raw-bank-2026-09-16/evidence/evaluate.py" target="_blank" rel="noopener">评价脚本</a><a href="../assets/raw-bank-2026-09-16/evidence/factor_preregister.yaml" target="_blank" rel="noopener">冻结因子注册表</a><a href="../assets/raw-bank-2026-09-16/evidence/label_inventory.json" target="_blank" rel="noopener">601 日收益标签清单</a><a href="../assets/raw-bank-2026-09-16/evidence/guard.json" target="_blank" rel="noopener">评价运行资源记录</a></div></section></main><footer><div class="wrap">思瑞投资 · 量化实习成果看板 / 历史样本内评价，原始方向，日度等权 / 无外部图表依赖</div></footer><noscript><p class="no-js">交互图表需要启用 JavaScript；因子定义与评价口径可直接阅读。</p></noscript><script id="report-gzip" type="application/octet-stream">__PAYLOAD__</script><script id="proof-data" type="application/json">__PROOF__</script><script>__JS__</script></body></html>'''
js=(ROOT/'scripts/rawbank_report_view.js').read_text(encoding='utf-8')
template=template.replace('__EXPLORER__',(ROOT/'scripts/rawbank_explorer.html').read_text(encoding='utf-8'))
output=template.replace('__CSS__',css).replace('__PAYLOAD__',payload).replace('__PROOF__',json.dumps(proof,separators=(',',':'))).replace('__VALID__',f"{proof['valid_label_stock_days']:,}").replace('__JS__',js)
output=output.replace('<tr><th>评价代码</th>', '<tr><th>完整样本补充统计</th><td>601 日、288 列；十分组计数与均值逐日对照原评价一致；OLS、精确原值分位数、收益分组诊断和全部成对样本散点密度已完成。业务耗时 145.2 秒，守护进程退出码 0，峰值内存 6.68 GiB，无 OOM。</td></tr><tr><th>评价代码</th>')
output=output.replace('<button id="download-proof">', '<a href="../assets/raw-bank-2026-09-16/evidence/details-result.json" download>补充统计验收</a><a href="../assets/raw-bank-2026-09-16/evidence/details-guard.json" download>补充统计资源记录</a><a href="../assets/raw-bank-2026-09-16/evidence/evaluate_details.py" download>补充统计脚本</a><button id="download-proof">')
finding='<div class="note"><p>全期 |Rank IC| 排名靠前的卖侧深度耗尽后补量 <code>f100_maker_depletion_refill</code>，日均 Rank IC 为 −0.026405，NW t 为 −6.646；但 G10−G1 毛收益为 +0.971bp。相关方向与端点组差值并不一致，需结合完整分组曲线判断，不能仅凭 IC 翻转方向。</p><p>284 列正式因子中有 26 列没有有效 IC 日，浏览器保留这些结果并显示缺失。覆盖率高也不保证横截面有区分度；全期排序不等同于可交易信号排序。</p></div>'
output=output.replace('<p id="result-note"',finding+'<p id="result-note"')
target=ROOT/'content/daily/2026-09-16.show.html'
target.write_text(output,encoding='utf-8')
assert target.stat().st_size<25*1024**2, 'Cloudflare asset exceeds 25 MiB'
assert all(path.stat().st_size<25*1024**2 for path in factor_dir.glob('*.js'))
print('HTML bytes',target.stat().st_size)
