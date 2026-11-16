"""Populate the original 11.9 comparison layout with the signed CSI 2000 market replay."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import gzip
import hashlib
from html import escape
from itertools import product
import json
from math import isfinite, isclose
from pathlib import Path
import re
import subprocess

from build_20261109_fill_rules import ASSET_LIMIT, comparison_layout, encode_data, replace


ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / 'content/daily'
OLD_NOTE, OLD_PAGE = DAILY / '2026-11-09.md', DAILY / '2026-11-09.show.html'
NOTE, PAGE = DAILY / '2026-11-16.md', DAILY / '2026-11-16.show.html'
SCRIPT = Path(__file__).with_name('csi2000_market_comparison.js')
TEMPLATE_REVISION = '916ed8c3029b7f6cdd38736b3d00f0e43bd9ce81'
TITLE = '中证 2000 底仓做 T：沪深冻结模型基准'
SCHEMA = 'csi2000-market-attribution-v1'
NET_SCHEMA = 'csi2000-market-attribution-v2'
STAGES = {'oof': ('development', '开发 OOF', 308), 'test_seen': ('seen', '已看测试', 176),
          'test_unseen': ('unseen', '未看测试', 82)}
WEIGHTS = ('index', 'equal')
CONFIGURATIONS = {'-'.join(axis) for axis in product(
    WEIGHTS, ('combined', 'separate'), ('morning', 'close'), ('L', 'A'), ('1', '5', '10', '20'))}
SOURCE_HASHES = {
    OLD_NOTE: 'f30d3c0d0e50bdbf24ffbf2fff088fccb24b5bea816790fea36c0b1c1c75915a',
    OLD_PAGE: '9bebcb4838d547e5b5f8917eaf3740ffbff7d5170c7ff3a952e6d8649f61dcda',
}


def template_text(path):
    path = path.resolve()
    if path not in SOURCE_HASHES:
        raise ValueError('Use one of the protected template paths')
    relative = ('content/daily/2026-11-09.show/.html' if path == OLD_PAGE
                else path.relative_to(ROOT).as_posix())
    raw = subprocess.check_output(['git', 'show', TEMPLATE_REVISION + ':' + relative], cwd=ROOT)
    normalized = raw.replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() == SOURCE_HASHES[path]:
        return raw.decode('utf-8')
    # Historic working-copy hashes include Windows CRLF. The Git source is LF.
    if hashlib.sha256(normalized.replace(b'\n', b'\r\n')).hexdigest() != SOURCE_HASHES[path]:
        raise ValueError(f'Template SHA-256 differs: {path.name}')
    return normalized.decode('utf-8')


def read_results(path, expected_sha256):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Market attribution SHA-256 differs from its receipt')
    return json.loads(raw)


def pack(results):
    dates, stages, nominal = (results[k] for k in ('dates', 'stages', 'nominal'))
    expected = [stage for stage, (_, _, count) in STAGES.items() for _ in range(count)]
    if (results['schema'] not in (SCHEMA, NET_SCHEMA) or dates != sorted(set(dates)) or len(dates) != len(expected)
            or (dates[0], dates[-1]) != ('2024-07-01', '2026-10-30') or stages != expected
            or not isfinite(nominal) or nominal <= 0):
        raise ValueError('Invalid market attribution calendar or nominal capital')
    fractions = results.get('trade_fractions', [.1])
    if (fractions not in ([.1], [.1, .2, .3])):
        raise ValueError('Invalid T fraction coverage')
    configurations = {key + ('' if fraction == .1 else f'-t{fraction * 100:g}')
                      for fraction in fractions for key in CONFIGURATIONS}
    if (set(results['series']) != configurations or set(results['base']) != set(WEIGHTS)
            or set(results['initial']) != set(WEIGHTS)):
        raise ValueError('Missing market configurations')
    result = dict(dates=dates, stages=[STAGES[s][0] for s in stages], base={}, initial={}, series={},
                  tradeFractions=[round(fraction * 100) for fraction in fractions])
    for weight in WEIGHTS:
        initial = results['initial'][weight]
        if len(initial) != 2 or any(not isfinite(x) or x <= 0 for x in initial) or not isclose(sum(initial), nominal):
            raise ValueError(f'Invalid initial allocation: {weight}')
        base = results['base'][weight]
        if len(base) != len(dates) or any(len(b) != 2 or any(not isfinite(x) for x in b) for b in base):
            raise ValueError(f'Invalid market base path: {weight}')
        result['base'][weight] = [[round(x / nominal, 12) for x in b] for b in base]
        result['initial'][weight] = [x / nominal for x in initial]
    for key, rows in sorted(results['series'].items()):
        if len(rows) != len(dates):
            raise ValueError(f'Invalid row count: {key}')
        values = []
        for row in rows:
            if len(row) != 6:
                raise ValueError(f'Invalid market attribution row: {key}')
            sh, sz, n_sh, n_sz, f_sh, f_sz = row
            if (not all(isfinite(x) for x in (sh, sz))
                    or any(type(n) is not int or n < 0 for n in (n_sh, n_sz, f_sh, f_sz))
                    or f_sh > n_sh or f_sz > n_sz):
                raise ValueError(f'Invalid market result: {key}')
            values.append([round(sh / nominal, 12), round(sz / nominal, 12), n_sh, n_sz, f_sh, f_sz])
        result['series'][key] = values
    if results['schema'] == NET_SCHEMA:
        if results.get('fees') != dict(buy=.9e-4, sell=5.9e-4) or set(results['trading']) != configurations:
            raise ValueError('Missing actual-fill cost or trading-return contract')
        result['fees'] = results['fees']
        result['trading'] = {}
        for key, rows in results['trading'].items():
            if len(rows) != len(dates) or any(len(row) != 2 or any(
                    len(market) != 3 or not all(isfinite(v) for v in market)
                    or market[0] < 0 or market[2] < 0 for market in row) for row in rows):
                raise ValueError(f'Invalid actual trading amounts: {key}')
            result['trading'][key] = [[[value / nominal for value in market] for market in row] for row in rows]
    return result


def chunk(source, left, right):
    begin = source.index(left)
    return source[begin:source.index(right, begin + len(left))]


def csi_signals(source):
    raw = re.search(r'id="fill-data">\s*(.*?)\s*</script>', source, re.S)
    if raw is None:
        raise ValueError('Signed F1–F9 diagnostics are absent from the template')
    csi = json.loads(gzip.decompress(base64.b64decode(raw.group(1))))['csi2000']
    signals = {}
    for label, _, days in STAGES.values():
        signal = csi[label]['signals']
        if len(signal) != 4 or any(len(lane) != days for lane in signal):
            raise ValueError(f'Invalid CSI 2000 signal coverage: {label}')
        signals[label] = signal
    return signals


def score_bodies():
    keys = ('tradeMean', 'mean', 'cumulative', 'sharpe', 'sharpeThrough', 'drawdown', 'calmar',
            'volatility', 'winRate', 'payoff', 't')
    bands = {'mean', 'sharpe', 'drawdown', 'winRate', 't'}
    sections = []
    for stage, label, days in STAGES.values():
        rows = []
        for lane, (market, name, cycle) in enumerate((
                ('sse', '沪市', '11:30'), ('sse', '沪市', '收盘'),
                ('szse', '深市', '11:30'), ('szse', '深市', '收盘'))):
            cells = []
            for key in keys:
                if key == 'sharpeThrough' and stage == 'development':
                    continue
                span = ' colspan="2"' if key == 'sharpe' and stage == 'development' else ''
                cls = 'score-num score-band-start' if key in bands else 'score-num'
                column = 'sharpe sharpeThrough' if span else key
                cells.append(f'<td class="{cls}" data-metric="{key}" data-score-column="{column}"{span}>—</td>')
            rows.append(f'<tr data-market="{market}" data-lane="{lane}">'
                        f'<th scope="row" data-score-column="stage"><span class="score-stage-label">{label} '
                        f'<small class="score-stage-days">{days} 日</small></span></th>'
                        f'<td class="score-key market-cell" data-score-column="market">{name}</td>'
                        f'<td class="score-key" data-score-column="cycle">{cycle}</td>'
                        + ''.join(cells) + '</tr>')
        sections.append(f'<tbody data-stage-block="{stage}" class="phase-{stage}">\n'
                        + '\n'.join(rows) + '\n</tbody>\n')
    return ''.join(sections)


def comparison_markup(source):
    view = chunk(source, '<section id="compare"', '\n  </div>\n<section id="carry-summary"')
    selectors = (
        '<label>底仓 <select name="weight"><option value="index">指数权重</option>'
        '<option value="equal">等权</option></select></label>\n'
        '      <label>排序 <select name="sorting"><option value="combined">沪深合并排序</option>'
        '<option value="separate">分市场排序</option></select></label>\n      '
    )
    view = replace(view, '<label>组合 <select', selectors + '<label>组合 <select')
    view = replace(view, '<label>阶段 <select',
                   '<label>做 T 比例 <select name="tradeFraction">'
                   '<option value="10">10%</option><option value="20">20%</option>'
                   '<option value="30">30%</option></select></label>\n      <label>阶段 <select')
    view = replace(view, chunk(view, '<div class="figure-controls"><div class="index-method-group"',
                              '<button type="button" class="demo-button is-emphasis" data-enlarge="returns"'),
                   '<div class="figure-controls"><div class="index-method-group" role="group" aria-label="收益视图">'
                   '<button type="button" data-return-view="wealth" aria-pressed="true">研究收益</button>'
                   '<button type="button" data-return-view="enhancement" aria-pressed="false">累计增强</button>'
                   '</div>')
    view = replace(view, chunk(view, '    <p id="fee-note"', '    <div class="curve-legend '), '')
    view = replace(view, chunk(view, '    <p id="pool-reference-note"', '    <div id="return-plot"'),
                   '    <p id="pool-reference-note" class="chart-foot">粗线为底仓加做 T 的研究收益，'
                   '细点线为同市场底仓收益。各市场以自身初始底仓为基准。</p>\n')
    view = replace(view, chunk(view, '    <p id="pool-focus-note"', '  </figure>'),
                   '    <figcaption class="chart-foot">两市收益按证券所属市场归因。'
                   '拖动框选日期，悬浮读数，点击固定。</figcaption>\n')
    view = replace(view, '<h2 id="signal-heading">IC 与 RankIC</h2>',
                   '<h2 id="signal-heading">中证 2000 · 成分池 IC 与 RankIC</h2>')
    view = replace(view, '每个交易日用同市场、同周期的有效股票配对预测分数与对手价毛收益。'
                   '两幅图的日期游标联动。',
                   '诊断沿用 F1–F9 修正的成分池单笔毛收益，与底仓做 T 累计曲线共用日期游标。')
    view = replace(view, chunk(view, '<strong id="index-view-label"', '<div aria-label="沪深基准数值对照"'),
                   '<strong id="index-view-label">中证 2000</strong>\n'
                   '<p class="hint" id="table-status"></p>\n<p class="chart-foot" id="score-note"></p>\n')
    view = replace(view, chunk(view, '<tbody data-stage-block', '</table>\n</div>'), score_bodies())
    view = view.replace('<colgroup><col><col></colgroup>', '<colgroup><col><col><col></colgroup>', 1)
    view = replace(view, '<th scope="colgroup" colspan="2">收益</th>', '<th scope="colgroup" colspan="3">收益</th>')
    view = re.sub(r'(<th\b[^>]*data-score-column="mean"[^>]*>)',
                  '<th class="score-num score-band-start" scope="col" data-score-column="tradeMean">交易日均净收益 bp</th>\\1', view, count=1)
    view = re.sub(r'<p class="hint" id="all-market-note">.*?</p>\n', '', view)
    return view


def comparison_script(source):
    helpers = chunk(source, '  function line(', '  function drawAll()')
    helpers = replace(helpers, "unit === '%' ? 1 : .01", "unit === '%' && !isEnhancement() ? 1 : .01")
    helpers = replace(helpers, "const digits = area.unit === '%' ? 0 : step >= 1 ? 0 : 2;",
                      "const digits = step >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(step)));")
    helpers = replace(helpers, "(isExcess() ? '超额' : '模型')", "returnLabel()")
    helpers = replace(helpers, "wide ? '成分池基准' : '基准'", "'底仓'")
    helpers += chunk(source, '  function detailsTable(', '  function dateNote(')
    selection = chunk(source, '  function refreshSelection()', '  function choose(')
    previous = "const context = kind === 'returns' ? [isExcess(), activeMethod, portfolio, feeBasis, focusedLanes.returns] : [focusedLanes.signal];"
    selection = replace(selection, previous, "const context = [weight, sorting, tradeFraction, view, portfolio, signalMode.value, focusedLanes[kind]];")
    selection = replace(selection, '[activeIndex, selection.index, pinned, ...context]',
                        '[selection.index, pinned, ...context]')
    script = SCRIPT.read_text(encoding='utf-8')
    for key, value in {
        '__CHART_HELPERS__': helpers, '__SELECTION_HELPERS__': selection,
        '__POINTER_HELPERS__': chunk(source, '  function clear()', '  function changeFilters()'),
        '__EXPANSION_HELPERS__': chunk(source, '  function expand(', '  const indexTabs')
    }.items():
        script = replace(script, key, value.strip())
    return script


def render(source, data, report_url):
    prefix = source[:source.index('<header class="shell">')]
    prefix = prefix.replace('../../fonts/', '../fonts/').replace('../../../site/fonts/', '../../site/fonts/')
    prefix = replace(prefix, '<title>沪深模型基准｜指数对标</title>', f'<title>{TITLE}</title>')
    header = f'''<header class="shell">
  <div class="report-meta">
    <time datetime="2026-11-16">2026.11.16 · 模型基准</time>
    <nav aria-label="本页导航"><a href="#compare">沪深收益</a><a href="#signal-figure">IC / RankIC</a><a href="#results">分段成绩</a><a href="#freeze">冻结配置</a><a href="#evidence">登记证据</a></nav>
  </div>
  <div class="report-title">
    <h1>{TITLE}</h1>
    <p>沪市 340 列与深市 344 列，比较中证 2000 成分股的 11:30 和收盘周期。</p>
    <p><a href="{escape(report_url, quote=True)}" target="_blank" rel="noopener">11.16 研究报告</a></p>
  </div>
</header>
<main class="shell">
'''
    contract = '''<section id="contract" aria-labelledby="contract-heading">
  <h2 id="contract-heading">样本与成交口径</h2>
  <ul class="contract-notes">
    <li>底仓使用中证 2000 沪深成分，按指数权重或等权建仓。名单和权重齐备后使用截至前一交易日的快照调仓。</li>
    <li>入选股票的做 T 额度可选该股昨收底仓市值的 10%、20%、30%，各档独立按库存与顺延规则回放。多空各取 q/2，亏盈按当日盯市计入，周转资金零利率。实际成交按买入 0.9 bp、卖出 5.9 bp 扣税费，底仓建仓与调仓同样计费。</li>
    <li>沪深曲线按证券所属市场归集交易现金及持仓市值。初始底仓按两市建仓金额分配，调仓买卖的现金与持仓变动相抵。两市的金额相加可还原合并组合。</li>
  </ul>
</section>
'''
    freeze = chunk(source, '  <section id="freeze"', '</main>')
    freeze = re.sub(r'    <p class="hint">沪市 L1／L20 .*?</p>\n', '', freeze)
    freeze = re.sub(r'    <p class="hint">逐日收益已与两份基准登记核对。.*?</p>\n', '', freeze)
    freeze = freeze.replace('逐日评价。当前表格使用 D20 的绝对 L 与 D23 的 A。', '冻结集成的登记配置。')
    payload = encode_data(dict(data, signal=csi_signals(source)))
    output = (prefix + header + comparison_markup(source) + contract + freeze + '</main>\n'
              + f'<script type="application/octet-stream" id="csi2000-market-data">{payload}</script>\n'
              + '<script>\n' + comparison_script(source) + '\n</script>\n</body>\n</html>\n')
    if len(output.encode()) > ASSET_LIMIT:
        raise ValueError('Comparison exceeds the single asset limit')
    return comparison_layout(output)


def render_note(source, report_url, *, published):
    stamp = datetime.fromisoformat(published)
    if stamp.tzinfo is None:
        raise ValueError('Published timestamp requires an explicit timezone')
    links = source[source.index('[模型线复盘'):].strip()
    return f'''---
title: "{TITLE}"
date: 2026-11-16
published: "{stamp.isoformat(timespec='seconds')}"
stage: model
show_source: 2026-11-16.show.html
summary: "在同一张图比较中证2000沪深底仓做T结果，分段成绩随底仓、排序和组合筛选更新。"
---

# {TITLE}

沪市和深市使用已冻结的 11:30、收盘两个模型集成。评价覆盖 566 个交易日，其中开发段 OOF 308 日、已看测试 176 日、未看测试 82 日。

在中证 2000 沪深成分上分别使用指数权重和等权底仓。可切换沪深合并排序或分市场排序、纯多 L 或多空 A，以及四档选股比例。做 T 比例可选每只入选股票昨收底仓市值的 **10%、20%、30%**，三档分别按实际库存、部分成交和跨日顺延回放，共192组配置；收益曲线和分段成绩同步切换。增量损益逐日盯市。实际买入按成交额扣 0.9 bp，卖出扣 5.9 bp，底仓建仓与调仓同样计费。

**HTML 展示版** 在同一张图比较沪市和深市的两个周期，可切换绝对与超额收益。收益图下方的「分段集成成绩」随口径和筛选更新，再下方为累计 IC／RankIC。绝对收益包含底仓和做 T，超额按做 T 增量计算；市场曲线按该市场的初始底仓金额归一化。 [11.16 研究报告]({report_url})

“交易日均净收益 bp”先用实际进场金额加权每天交易批次的扣费收益率，再对有交易日期等权平均；跨日批次按进场日归属。账户收益与底仓增强另列，净值曲线按日历日逐日盯市。

{links}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aggregate', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--report-url', required=True)
    parser.add_argument('--published', required=True)
    parser.add_argument('--source', type=Path, default=OLD_PAGE)
    parser.add_argument('--source-note', type=Path, default=OLD_NOTE)
    parser.add_argument('--page', type=Path, default=PAGE)
    parser.add_argument('--note', type=Path, default=NOTE)
    args = parser.parse_args()
    from frozen_baseline import protect_outputs
    protect_outputs([args.page, args.note])
    sources = {p.resolve() for p in (args.source, args.source_note, *SOURCE_HASHES)}
    targets = {args.page.resolve(), args.note.resolve()}
    if sources & targets or len(targets) != 2:
        parser.error('Output paths must differ from the protected 11.9 sources')
    results = read_results(args.aggregate, args.sha256)
    if results['schema'] != NET_SCHEMA:
        raise ValueError('11.16 publication requires signed actual-fill tax and trading-return results')
    data = pack(results)
    html = render(template_text(args.source), data, args.report_url)
    from build_20261116_g2_comparison import append_section, append_note
    html = append_section(html)
    note = append_note(render_note(template_text(args.source_note), args.report_url, published=args.published))
    args.page.parent.mkdir(parents=True, exist_ok=True)
    args.page.write_text(html, encoding='utf-8', newline='\n')
    args.note.write_text(note, encoding='utf-8', newline='\n')
    print(f'11.16 HTML {args.page.stat().st_size:,} bytes, {len(data["series"])} configurations')


if __name__ == '__main__':
    main()
