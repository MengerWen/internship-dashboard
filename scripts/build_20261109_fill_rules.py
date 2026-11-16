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
REPORT_PAGE = Path('content/daily/2026-11-09.show.html')
DAILY_NOTE = Path('content/daily/2026-11-09.md')
ASSET_LIMIT = 25 << 20


def replace(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f'Expected one page anchor: {before[:120]}')
    return source.replace(before, after, 1)


def comparison_layout(source):
    """Keep scores beside returns and both charts inside their shared dashboard."""
    scores = re.search(r'  <section\b[^>]*\bid="results"[^>]*>.*?</section>\n', source, re.S)
    if scores is None:
        raise ValueError('Missing segmented comparison scores')
    source = replace(source, scores[0], '')
    anchor = '  <figure class="chart-plate" id="signal-figure">'
    source = replace(source, anchor, scores[0] + anchor)
    names = {'absolute': '绝对', 'excess': '超额', 'wealth': '绝对', 'enhancement': '超额'}
    source = re.sub(
        r'(<button\b[^>]*data-return-(?:basis|view)="(absolute|excess|wealth|enhancement)"[^>]*>)[^<]*(</button>)',
        lambda match: match[1] + names[match[2]] + match[3], source)
    return re.sub(r'(<a href="#signal-figure"[^>]*>.*?</a>)(\s*)(<a href="#results"[^>]*>.*?</a>)',
                  r'\3\2\1', source)


def script_json(html, name):
    match = re.search(r'<script type="application/json" id="' + re.escape(name) + r'">\s*(.*?)\s*</script>',
                      html, re.S)
    if match is None:
        raise ValueError(f'Missing page data: {name}')
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
    calendar = script_json(html, 'evaluation-calendar')
    names = re.findall(r'data-index="([a-z0-9]+)"', html)
    if len(names) != 19 or len(set(names)) != 19 or names[0] != 'all':
        raise ValueError('Expected full market and 18 constituent pools')
    days = {day for phase in calendar for day in phase['dates']}
    for account, _ in SERIES:
        exported_days = {day for _, _, day in exports[account]}
        if days != exported_days:
            raise ValueError(f'Export calendar differs: {account}')
    out = {}
    for name in names:
        out[name] = {}
        for phase in calendar:
            stage, dates = phase['id'], phase['dates']
            series = [[exports[account][stage, horizon, day].get(name) for day in dates]
                      for account, horizon in SERIES]
            data = {'signals': [[row['signal'] if row else None for row in lane] for lane in series],
                    'poolMid': [[row['pool_mid'] if row else None for row in lane] for lane in series]}
            if not any(row is not None for lane in series for row in lane):
                raise ValueError(f'Missing constituent data: {name}/{stage}')
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
    payload_pattern = r'(<script type="application/octet-stream" id="fill-data">)[^<]*(</script>)'
    html, count = re.subn(payload_pattern, lambda m: m[1] + encode_data(data) + m[2], html)
    if count != 1:
        raise ValueError('Expected one execution data block')
    carry = re.search(r'<section id="carry-summary"[^>]*>.*?</section>\n', html, re.S)
    opening = re.search(r'^    <p class="fill-intro">.*?</p>', html, re.M)
    if carry is None or opening is None:
        raise ValueError('Missing execution summary or introduction')
    html = replace(html, carry[0], summary_table(summaries))
    return comparison_layout(replace(html, opening[0], intro(report_url)))


def update_note(path, summaries, report_url):
    source = path.read_text(encoding='utf-8')
    revised = []
    for account, market in (('wenjie', '沪市'), ('wangly', '深市')):
        result = {(r['strategy'], r['horizon']): r['main']['mean_bp'] for r in summaries[account]['metrics']
                  if (r['stage'], r['q']) == ('unseen', .05)}
        long = f'{result["L", "morning"]:.2f} / {result["L", "close"]:.2f}'
        combined = f'{result["A", "morning"]:.2f} / {result["A", "close"]:.2f}'
        revised.append(f'{market} L5 为 {long} bp，A5 为 {combined} bp')
    paragraph = ('按 F1–F9 重算后，未看段全市场的日均绝对毛收益按 11:30 / 收盘列出。'
                 + '。'.join(revised).replace('-', '−') + '。'
                 + f' [重算报告]({report_url})')
    current = re.search(r'^按 F1–F9 重算后，[^\n]+', source, re.M)
    if current is None:
        raise ValueError('Missing execution results in the daily note')
    return replace(source, current[0], paragraph)


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
    args.page.write_bytes(page_bytes)
    args.note.write_text(note, encoding='utf-8', newline='\n')
    print(f'{len(page_bytes):,} bytes, {len(adjusted) - 1} constituent pools, four market/horizon series')


if __name__ == '__main__':
    main()
