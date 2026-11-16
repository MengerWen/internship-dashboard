"""Build the 11.16 CSI 2000 daily report from the signed aggregate and the 11.9 template."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
from html import escape
import itertools
import json
import math
from pathlib import Path
import re

from build_20261109_fill_rules import ASSET_LIMIT, encode_data, replace


ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / 'content/daily'
OLD_NOTE, OLD_PAGE = DAILY / '2026-11-09.md', DAILY / '2026-11-09.show/.html'
NOTE, PAGE = DAILY / '2026-11-16.md', DAILY / '2026-11-16.show/.html'
SECTION = Path(__file__).with_name('csi2000_base_position_view.html')
TITLE = '中证 2000 底仓做 T：沪深冻结模型基准'
SCHEMA = 'csi2000-base-position-v1'
STAGES = {'oof': 308, 'test_seen': 176, 'test_unseen': 82}
AXES = [('index', 'equal'), ('combined', 'separate'), ('morning', 'close'), ('L', 'A'),
        ('1', '5', '10', '20')]
CONFIGURATIONS = {'-'.join(row) for row in itertools.product(*AXES)}
SOURCE_HASHES = {
    OLD_NOTE: 'f30d3c0d0e50bdbf24ffbf2fff088fccb24b5bea816790fea36c0b1c1c75915a',
    OLD_PAGE: '9bebcb4838d547e5b5f8917eaf3740ffbff7d5170c7ff3a952e6d8649f61dcda',
}


def read_results(path, expected_sha256):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Aggregate SHA-256 differs from its signed receipt')
    return json.loads(raw, parse_constant=lambda value: invalid_number(value))


def invalid_number(value):
    raise ValueError(f'Non-finite result: {value}')


def pack(results):
    dates = results['dates']
    if (results['schema'] != SCHEMA or len(dates) != 566 or dates != sorted(set(dates))
            or (dates[0], dates[-1]) != ('2024-07-01', '2026-10-30')):
        raise ValueError('Wrong schema or evaluation calendar')
    configurations = [r['key'] for r in results['configurations']]
    if len(configurations) != 64 or set(configurations) != CONFIGURATIONS:
        raise ValueError('Expected all 64 distinct model configurations')
    nominal = results['nominal']
    if not math.isfinite(nominal) or nominal <= 0:
        raise ValueError('Invalid initial nominal value')
    if len(results['daily']) != 36_224 or len(results['statistics']) != 192:
        raise ValueError('Invalid result dimensions')
    daily, summaries = {}, {}
    for key in configurations:
        daily[key] = [r for r in results['daily'] if r['config'] == key]
        summaries[key] = [r for r in results['statistics'] if r['config'] == key]
    packed = dict(dates=dates, stages=[], base={}, config={})
    for key, rows in daily.items():
        if [row['date'] for row in rows] != dates:
            raise ValueError(f'Daily coverage differs: {key}')
        stages = [row['stage'] for row in rows]
        if Counter(stages) != STAGES or stages != sorted(stages):
            raise ValueError(f'Segment coverage differs: {key}')
        if packed['stages'] and packed['stages'] != stages:
            raise ValueError('Configurations have different sample boundaries')
        packed['stages'] = stages
        weight = key.split('-')[0]
        bases = []
        compressed = []
        for row in rows:
            base, addition, wealth = (float(row[k]) / nominal for k in ('base', 'addition', 'wealth'))
            if not math.isclose(base + addition, wealth, rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(f'Inconsistent values for {key}/{row["date"]}')
            counts = [row[field] for field in ('selected_sh', 'selected_sz', 'filled')]
            if any(type(n) is not int or n < 0 for n in counts) or counts[2] > sum(counts[:2]):
                raise ValueError(f'Invalid selection counts: {key}/{row["date"]}')
            bases.append(round(base, 11))
            compressed.append([round(addition, 11), *counts])
        if weight in packed['base'] and packed['base'][weight] != bases:
            raise ValueError(f'Base path differs within {weight}')
        packed['base'][weight] = bases
        stats = summaries[key]
        if {row['stage']: row['days'] for row in stats} != STAGES or len(stats) != 3:
            raise ValueError(f'Missing summaries: {key}')
        packed['config'][key] = dict(rows=compressed, statistics=[
            {k: v for k, v in row.items() if k != 'config'} for row in stats
        ])
    return packed


def render(source, data, report_url):
    sections = SECTION.read_text(encoding='utf-8').split('</style>\n', 1)
    style = sections[0] + '</style>\n'
    view = replace(sections[1], '@@RESULTS@@', encode_data(data))
    source = replace(source, '<title>沪深模型基准｜指数对标</title>',
                     '<title>' + TITLE + '</title>\n' + style)
    source = replace(source, '<time datetime="2026-11-09">2026.11.09 · 模型基准</time>',
                     '<time datetime="2026-11-16">2026.11.16 · 模型基准</time>')
    source = replace(source, '<span class="review-edition">指数对标</span>',
                     '<span class="review-edition">中证 2000</span>')
    source = replace(source, '<h1>沪深基准的逐日收益</h1>', '<h1>' + TITLE + '</h1>')
    source = replace(source, '<nav aria-label="本页导航">', '<nav aria-label="本页导航">'
                     '<a href="#csi-base-position">底仓做 T</a>')
    source = replace(source, '<main class="shell">', '<main class="shell">\n' + view)
    source = replace(source, '<h2>对标指数</h2>', '<h2>历史对照 · 原冻结基准</h2>')
    old_end = '</p>\n  </div>\n</header>'
    research = '<p><a href="' + escape(report_url, quote=True) + '" target="_blank" rel="noopener">11.16 研究报告</a></p>'
    source = replace(source, old_end, '</p>\n    ' + research + '\n  </div>\n</header>')
    if len(source.encode()) > ASSET_LIMIT:
        raise ValueError('Compressed report exceeds the single-asset limit')
    return source


def render_note(source, result, report_url, *, published=None):
    source = replace(source, 'date: 2026-11-09', 'date: 2026-11-16')
    publication = ''
    if published is not None:
        stamp = datetime.fromisoformat(published)
        if stamp.tzinfo is None:
            raise ValueError('Published timestamp requires an explicit timezone')
        publication = f'published: "{stamp.isoformat(timespec="seconds")}"\n'
    source = re.sub(r'^published: [^\n]+\n', lambda _: publication, source, count=1, flags=re.M)
    source = replace(source, 'show_source: 2026-11-09.show/.html', 'show_source: 2026-11-16.show/.html')
    source = re.sub(r'^title: [^\n]+', f'title: "{TITLE}"', source, count=1, flags=re.M)
    source = re.sub(r'^summary: [^\n]+',
                    'summary: "两种中证2000底仓与两种沪深排序方式。查看 64 个配置的逐日净值、累计增强和分段统计。"',
                    source, count=1, flags=re.M)
    source = replace(source, '# 沪深日内模型基准：冻结配置与两段测试', '# ' + TITLE)
    row = next(row for row in result['statistics'] if row['config'] == 'index-combined-morning-L-5'
               and row['stage'] == 'test_unseen')
    before = source.index('\n\n全市场前 5%')
    after = source.index('\n\n[模型线复盘', before)
    historical = source[before:after].replace('展示页默认显示主口径，可切回原登记口径。',
                                              '在展示页的历史对照区可切换重算和原登记口径。')
    note = (
        '\n\n在 2024-07-01 至 2026-10-30 的 566 个交易日上，用中证 2000 沪深成分建立指数权重和等权底仓。'
        '成分变化后，等新名单与配套米筐权重齐备再调整。开盘使用截至前一交易日的快照。'
        '持股数量在两次调整间随公司行动衔接，等权仅在共同调整时恢复。\n\n'
        '入选股票使用上一收盘的底仓市值的 10% 做 T。A 的头尾各取 q/2，每股额度仍为 10%。'
        '周转现金零利率，结果为费用前。T 损益逐日盯市且不回投底仓，研究净值与底仓净值均以初始名义规模归一化。\n\n'
        f'指数权重、沪深合并排序、11:30 的 L5 在未看段日均增强为 **{row["mean_bp"]:+.2f} bp**。'
        '展示页可切换底仓、排序、周期、L/A、选股比例及样本段，并查看日期详情。'
        f' [11.16 研究报告]({report_url})\n\n## 11.9 冻结登记与成交重算历史对照'
    )
    return source[:before] + note + historical + source[after:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aggregate', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--report-url', required=True)
    parser.add_argument('--published', help='ISO timestamp of the report’s first Git commit')
    parser.add_argument('--source', type=Path, default=OLD_PAGE)
    parser.add_argument('--source-note', type=Path, default=OLD_NOTE)
    parser.add_argument('--page', type=Path, default=PAGE)
    parser.add_argument('--note', type=Path, default=NOTE)
    args = parser.parse_args()
    sources = {Path(p).resolve() for p in (args.source, args.source_note, *SOURCE_HASHES)}
    targets = {args.page.resolve(), args.note.resolve()}
    if sources & targets or len(targets) != 2:
        parser.error('Output paths must differ from the protected 11.9 sources')
    for path in (args.source.resolve(), args.source_note.resolve()):
        if path not in SOURCE_HASHES or hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_HASHES[path]:
            raise ValueError(f'Template SHA-256 differs: {path.name}')
    result = read_results(args.aggregate, args.sha256)
    data = pack(result)
    payload = render(args.source.read_text(encoding='utf-8'), data, args.report_url)
    note = render_note(args.source_note.read_text(encoding='utf-8'), result, args.report_url, published=args.published)
    args.page.parent.mkdir(parents=True, exist_ok=True)
    args.page.write_text(payload, encoding='utf-8', newline='\n')
    args.note.write_text(note, encoding='utf-8', newline='\n')
    print(f'11.16 HTML {args.page.stat().st_size:,} bytes, {len(data["config"])} configurations')


if __name__ == '__main__':
    main()
