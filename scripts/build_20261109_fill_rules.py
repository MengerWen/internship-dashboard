"""Embed the two signed F1–F9 dashboard exports in the 11-09 standalone page."""
from __future__ import annotations

import argparse
import base64
import gzip
from html import escape
import json
import math
from pathlib import Path
import re
from statistics import fmean


SERIES = (('wenjie', 'morning'), ('wenjie', 'close'), ('wangly', 'morning'), ('wangly', 'close'))
PORTFOLIOS = tuple(f'{side}{q}' for side in ('L', 'A') for q in (1, 5, 10, 20))
STAGES = {'development': '开发 OOF', 'seen': '已看测试', 'unseen': '未看测试'}
REPORT_PAGE = Path('content/daily/2026-11-09.show/.html')
DAILY_NOTE = Path('content/daily/2026-11-09.md')
ASSET_LIMIT = 25 << 20


def replace(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f'Expected one page anchor: {before[:120]}')
    return source.replace(before, after, 1)


def script_json(html, name):
    match = re.search(r'<script type="application/json" id="' + re.escape(name) + r'">\s*(.*?)\s*</script>',
                      html, re.S)
    if match is None:
        raise ValueError(f'Missing original page data: {name}')
    return json.loads(match.group(1))


def encode_data(document):
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    return base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode()


def read_export(path, expected, account):
    import hashlib
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected['artifacts']['dashboard']['sha256']:
        raise ValueError(f'Dashboard export digest differs: {account}')
    rows = json.loads(gzip.decompress(payload))
    mapped = {(row['stage'], row['horizon'], row['date']): row['baskets'] for row in rows}
    if len(rows) != len(mapped) or len(rows) != 2 * len(expected['dates']):
        raise ValueError(f'Dashboard export date coverage differs: {account}')
    return mapped


def assemble(html, exports):
    returns = script_json(html, 'return-data')
    names = ['all', *re.findall(r'id="index-data-([a-z0-9]+)"', html)]
    if len(set(names)) != 19:
        raise ValueError('Expected full market and 18 constituent pools')
    out = {}
    for name in names:
        out[name] = {}
        old = script_json(html, 'index-data-' + name) if name != 'all' else None
        for phase in returns['phases']:
            stage, dates = phase['id'], phase['dates']
            series = [[exports[account][stage, horizon, day].get(name) for day in dates]
                      for account, horizon in SERIES]
            data = {'signals': [[row['signal'] if row else None for row in lane] for lane in series],
                    'poolMid': [[row['pool_mid'] if row else None for row in lane] for lane in series]}
            if old and [[point is not None for point in lane] for lane in data['signals']] != [
                    [point is not None for point in lane] for lane in old[stage]['signals']]:
                raise ValueError(f'Index start or market coverage changed: {name}/{stage}')
            for method in ('within', 'intersect'):
                if method == 'intersect' and name == 'all':
                    continue
                data[method] = {}
                for port in PORTFOLIOS:
                    packed = [[row[method][port] if row else None for row in lane] for lane in series]
                    for lane in packed:
                        for point in lane:
                            if point is None:
                                continue
                            gross, selected, filled, net, carry, occupied = point
                            if (not all(map(math.isfinite, (gross, net, occupied))) or occupied < 0
                                    or not 0 <= carry <= filled <= selected):
                                raise ValueError(f'Invalid adjusted daily portfolio: {name}/{stage}/{method}/{port}')
                    data[method][port] = packed
            out[name][stage] = data
    return out


def verify_full_market(bundle, summaries):
    for i, (account, horizon) in enumerate(SERIES):
        for row in summaries[account]['metrics']:
            if row['horizon'] != horizon:
                continue
            port = f'{row["strategy"]}{round(row["q"] * 100)}'
            points = bundle['all'][row['stage']]['within'][port][i]
            actual = fmean(point[0] for point in points) * 10_000
            if (len(points) != row['main']['days']
                    or not math.isclose(actual, row['main']['mean_bp'], rel_tol=0, abs_tol=1e-9)):
                raise ValueError(f'Full market differs from the signed replay: {account}/{horizon}/{port}')


def summary_table(summaries):
    rows = []
    for account, horizon in SERIES:
        for result in summaries[account]['exposures']:
            if result['horizon'] != horizon or result['mode'] != 'main':
                continue
            market = '沪市' if account == 'wenjie' else '深市'
            period = '11:30' if horizon == 'morning' else '收盘'
            stage = result['stage']
            port = f'{result["strategy"]}{round(result["q"] * 100)}'
            side = '多头' if result['side'] == 'long' else '空头'
            counts = result['delays']
            occupation = result['occupied']
            carry = result['carry']
            total = result['selected']
            if sum(counts.values()) != carry:
                raise ValueError('Carry durations do not reconcile')
            cells = (STAGES[stage], side, f'{carry:,}（{carry/total:.2%}）' if total else '0',
                     f'{counts["delay_0"]:,}', f'{counts["delay_1"]:,}', f'{counts["delay_2_5"]:,}',
                     f'{counts["delay_6_plus"]:,}', f'{counts["terminal_lots"]:,}',
                     f'{occupation["p50"]:.2%} / {occupation["p95"]:.2%}')
            hidden = '' if port == 'L5' else ' hidden'
            rows.append(f'<tr data-carry-port="{port}" data-carry-stage="{stage}"{hidden}>'
                        f'<th scope="row">{market} {period}</th>' +
                        ''.join(f'<td>{escape(cell)}</td>' for cell in cells) + '</tr>')
    headings = ('市场与周期', '样本', '腿', '顺延笔数', '当天平仓', '1 日', '2–5 日', '6 日及以上',
                '退市或期末未平', '资金占用中位数 / P95')
    return ('<section id="carry-summary" aria-labelledby="carry-summary-heading">\n'
            '  <h2 id="carry-summary-heading">卖不掉的仓位</h2>\n'
            '  <p>按主口径的全市场组合统计，随上方组合、选股比例和样本段切换。顺延笔数占入选股票日合计，'
            '天数按交易日计算，资金占用按每天 09:35 尚未平掉的旧仓本金占该腿计划资金统计。</p>\n'
            '  <div class="index-rank-table"><table><thead><tr>' +
            ''.join(f'<th scope="col">{h}</th>' for h in headings) + '</tr></thead><tbody>\n' +
            '\n'.join(rows) + '\n</tbody></table></div>\n</section>\n')


def intro(report_url):
    return ('    <p class="fill-intro">主口径先剔除全天停牌、09:35 缺买一或卖一、缺参考、同配置仍有旧仓、'
            '以及已知的风险警示和退市整理股，再按冻结分数选股。进出场只按有对手价的时段成交，'
            '进场未成部分计现金。出场未平的部分在之后的连续竞价中分 60 秒窗口继续处理，'
            '收益记回进场日。模型仍用原标签训练。回放假设候选股票已有底仓，多空组合的空头腿假设可以融券。'
            f' <a href="{escape(report_url, quote=True)}" target="_blank" rel="noopener">成交规则与重算报告</a></p>')


def render(html, data, summaries, report_url):
    names = [name for name in data if name != 'all']
    original = {name: script_json(html, 'index-data-' + name) for name in names}
    html, removed = re.subn(r'<script type="application/json" id="index-data-[a-z0-9]+">.*?</script>\n',
                            '', html, flags=re.S)
    if removed != len(original):
        raise ValueError('Original constituent data could not be moved to the compressed payload')
    encoded = encode_data(data)
    historic = encode_data(original)
    html = replace(html, '  </div>\n</header>\n<main', intro(report_url) + '\n  </div>\n</header>\n<main')
    html = replace(html, '<section id="contract"', summary_table(summaries) + '\n<section id="contract"')
    html = replace(html, '<div class="figure-controls"><div class="index-method-group" role="group" aria-label="收益口径"',
        '<div class="figure-controls"><div class="index-method-group" role="group" aria-label="成交口径">'
        '<button type="button" data-fill-basis="main" aria-pressed="true">主口径</button>'
        '<button type="button" data-fill-basis="original" aria-pressed="false">原登记口径</button></div>'
        '<div class="index-method-group" role="group" aria-label="收益口径"')
    html = replace(html, '    <p id="fee-note"', '    <p id="fill-status" class="chart-foot" role="status" hidden></p>\n    <p id="fee-note"')
    html = replace(html, '<script>\n(() => {', '<script type="application/octet-stream" id="fill-data">' +
        encoded + '</script>\n<script type="application/octet-stream" id="original-index-data">' +
        historic + '</script>\n<script>\n(async () => {')
    html = replace(html, "  let indexData = null;", """  let correction = null;
  let fillBasis = 'main';
  async function readData(id) {
    const zipped = Uint8Array.from(atob(get(id).textContent), value => value.charCodeAt(0));
    const stream = new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).json();
  }
  const originalIndexes = readData('original-index-data').catch(() => null);
  try {
    correction = await readData('fill-data');
  } catch {
    fillBasis = 'original';
    get('fill-status').textContent = '主口径数据读取失败，当前显示原登记口径。';
    get('fill-status').hidden = false;
    document.querySelector('[data-fill-basis="main"]').disabled = true;
  }
  const originalData = await originalIndexes;
  let indexData = correction?.all ?? null;""")
    html = replace(html, "const isExcess = () => returnBasis === 'excess' && indexData !== null;",
        "const isExcess = () => returnBasis === 'excess' && activeIndex !== 'all';\n"
        "  const methodFor = pool => pool === 'all' ? 'within' : activeMethod;")
    html = replace(html, "    if (feeBasis !== 'net' || !Number.isFinite(gross)) return gross;",
        "    if (feeBasis !== 'net' || !Number.isFinite(gross)) return gross;\n"
        "    if (fillBasis === 'main') return correction[pool][phase][methodFor(pool)][port][seriesIndex][dayIndex]?.[3] ?? null;")
    html = replace(html, "const benchmark = !indexData ? null", "const benchmark = activeIndex === 'all' ? null")
    html = replace(html, "returnsByPhase[phase][port][seriesIndex][dayIndex], phase, seriesIndex, dayIndex, port, 'all'",
        "(fillBasis === 'main' ? correction.all[phase].within[port][seriesIndex][dayIndex]?.[0]\n"
        "        : returnsByPhase[phase][port][seriesIndex][dayIndex]), phase, seriesIndex, dayIndex, port, 'all'")
    html = replace(html, "indexed[activeMethod][port]", "indexed[methodFor(activeIndex)][port]")
    html = replace(html, "indexData?.[stage][activeMethod][key]", "indexData?.[stage][methodFor(activeIndex)][key]")
    html = replace(html, "Boolean(indexData && portfolio?.startsWith('L')", "Boolean(activeIndex !== 'all' && indexData && portfolio?.startsWith('L')")
    html = replace(html, "    indexData = activeIndex === 'all' ? null : JSON.parse(get('index-data-' + activeIndex).textContent);",
        "    loadActiveIndex();")
    html = replace(html, "  function switchIndex(tab, keyboard = false) {", """  function loadActiveIndex() {
    indexData = fillBasis === 'main' ? correction[activeIndex]
      : activeIndex === 'all' ? null : originalData?.[activeIndex] ?? null;
  }
  const fillButtons = [...document.querySelectorAll('[data-fill-basis]')];
  function syncFillBasis() {
    fillButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.fillBasis === fillBasis)));
    const adjusted = fillBasis === 'main';
    get('carry-summary').hidden = !adjusted;
    indexTabs.forEach(tab => { tab.disabled = !adjusted && !originalData && tab.dataset.index !== 'all'; });
    const contract = get('contract');
    contract.querySelectorAll('[data-original-fill]').forEach(item => { item.hidden = adjusted; });
    contract.querySelectorAll('[data-main-fill]').forEach(item => { item.hidden = !adjusted; });
    get('indexed-contract').textContent = adjusted
      ? '指数页使用原有月末成分。成分池中间价基准按 F2 过滤后等权，旧仓按成分池自己的全选多头持仓跟踪。A 的超额基准沿用同口径全市场 A。IC 与 RankIC 以符合静态可交易条件的个股计划资金毛收益计算。'
      : originalIndexContract;
  }
  const originalIndexContract = get('indexed-contract').textContent;
  fillButtons.forEach(button => button.addEventListener('click', () => {
    if (button.disabled || button.dataset.fillBasis === fillBasis) return;
    fillBasis = button.dataset.fillBasis;
    if (fillBasis === 'original' && !originalData && activeIndex !== 'all') switchIndex(tabsByIndex.all);
    loadActiveIndex();
    syncFillBasis();
    refreshReturns();
  }));
  syncFillBasis();

  function switchIndex(tab, keyboard = false) {
    if (tab.disabled) return;""")
    html = replace(html, " : '全市场原基准';", " : (fillBasis === 'main' ? '全市场主口径' : '全市场原基准');")
    html = replace(html, "  function refreshIndexCaption() {", """  function refreshIndexCaption() {
    get('carry-summary').querySelectorAll('[data-carry-port]').forEach(row => {
      row.hidden = row.dataset.carryPort !== portfolio || (phaseChoice !== 'all' && row.dataset.carryStage !== phaseChoice);
    });""")
    html = replace(html, '<li>纯多 L 买分数最高的 q。', '<li data-original-fill>纯多 L 买分数最高的 q。')
    html = replace(html, '<li>图表使用对手价绝对毛收益，', '<li data-original-fill>图表使用对手价绝对毛收益，')
    html = replace(html, '<li id="indexed-contract" hidden>',
        '<li data-main-fill>主口径在过滤后的股票池里选股。每腿按入选只数等分资金，'
        '未成交部分留在现金。费用按实际成交金额计算。</li>\n      <li id="indexed-contract" hidden>')
    html = replace(html, '<details class="index-rankings">', '<details class="index-rankings" data-original-rank>')
    html = re.sub(r'(<details class="index-rankings" data-original-rank>\s*<summary>)', r'\1原登记口径 · ', html, count=1)
    return html


def update_note(path, summaries, report_url):
    source = path.read_text(encoding='utf-8')
    old = '以上为对手价绝对毛收益。'
    revised = []
    for account, market in (('wenjie', '沪市'), ('wangly', '深市')):
        result = {(r['strategy'], r['horizon']): r['main']['mean_bp'] for r in summaries[account]['metrics']
                  if (r['stage'], r['q']) == ('unseen', .05)}
        long = f'{result["L", "morning"]:.2f} / {result["L", "close"]:.2f}'
        combined = f'{result["A", "morning"]:.2f} / {result["A", "close"]:.2f}'
        revised.append(f'{market} L5 为 {long} bp，A5 为 {combined} bp')
    suffix = ('\n\n按 F1–F9 重算后，未看段全市场的日均绝对毛收益按 11:30 / 收盘列出。'
              + '。'.join(revised).replace('-', '−') + '。展示页默认显示主口径，可切回原登记口径。'
              + f' [重算报告]({report_url})')
    return replace(source, old, old + suffix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for account in ('wangly', 'wenjie'):
        parser.add_argument('--' + account, type=Path, required=True)
        parser.add_argument('--' + account + '-summary', type=Path, required=True)
    parser.add_argument('--report-url', required=True)
    parser.add_argument('--source', type=Path, default=REPORT_PAGE)
    parser.add_argument('--page', type=Path, default=REPORT_PAGE)
    parser.add_argument('--note', type=Path, default=DAILY_NOTE)
    args = parser.parse_args()
    summaries = {a: json.loads(getattr(args, a + '_summary').read_text(encoding='utf-8'))
                 for a in ('wangly', 'wenjie')}
    for account, summary in summaries.items():
        if summary['account'] != account or summary['schema'] != 'baseline-fill-rules-v1':
            raise ValueError(f'Unexpected summary identity: {account}')
    sources = {a: read_export(getattr(args, a), r, a) for a, r in summaries.items()}
    source = args.source.read_text(encoding='utf-8')
    adjusted = assemble(source, sources)
    verify_full_market(adjusted, summaries)
    page = render(source, adjusted, summaries, args.report_url)
    note = update_note(args.note, summaries, args.report_url)
    page_bytes = page.encode()
    if len(page_bytes) >= ASSET_LIMIT:
        raise ValueError(f'Standalone page exceeds the deployment asset budget: {len(page_bytes)} bytes')
    for name in ('return-data', 'demo-signals', 'fee-data'):
        if script_json(source, name) != script_json(page, name):
            raise ValueError(f'Original page data changed: {name}')
    args.page.write_bytes(page_bytes)
    args.note.write_text(note, encoding='utf-8', newline='\n')
    print(f'{len(page_bytes):,} bytes, {len(adjusted) - 1} constituent pools, four market/horizon series')


if __name__ == '__main__':
    main()
