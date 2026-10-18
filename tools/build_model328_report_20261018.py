"""Render the accepted model328 aggregates in the established factor-report shell."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import csv
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import re
import statistics
import sys

from bs4 import BeautifulSoup
import markdown

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/model328-2026-10-18'
DAY = '2026-10-18'
SOURCES = {'old': '老因子', 'cancel_buy': '买侧撤单相位', 'cancel_sell': '卖侧撤单相位', 'depth': '深度匹配'}
LAYERS = {'L1': '基础评分投影', 'L2': '多证据共识', 'L3': '微观结构情境', 'L4': '窗口状态', 'L5': '用途与流动性机制', 'CPH': '撤单相位', 'DM': '深度匹配'}
ACCEPTANCE_SHA = 'fc0f323dca7c222f0ec6dbe44e472447b2e4139aee76c67318d42a71c64bbd83'


def md_table(headers, rows):
    def cell(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|',
                      *['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]])


def write_csv(name, headers, rows):
    with (ASSETS / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([[str(v).lower() if isinstance(v,bool) else v for v in row] for row in rows])


def period_list(days):
    result = [dict(id='full', label='全部601日', start=days[0]['date'], end=days[-1]['date'])]
    for size in ['year', 'quarter', 'month']:
        groups = {}
        for row in days:
            y, m = int(row['date'][:4]), int(row['date'][5:7])
            key = str(y) if size == 'year' else f'{y}Q{(m-1)//3+1}' if size == 'quarter' else row['date'][:7]
            groups.setdefault(key, []).append(row['date'])
        result += [dict(id=k, label=('2026H1' if k == '2026' else k), start=v[0], end=v[-1]) for k, v in groups.items()]
    assert len(result) == 44
    return result


def validate(data, manifest):
    features, days, coverage = manifest['features'], data['days'], data['coverage']
    assert data['source_sha256']['factor-bank/final_acceptance.json'] == ACCEPTANCE_SHA
    assert data['scientific_identity_sha256'] == '8175a4c6a964a93744c0437c5052ecc158dd2975d6e2d210b878e0f8238ea023'
    assert [f['model_column'] for f in features] == data['columns']
    assert len(days) == 601 and len(features) == 328
    assert len({d['date'] for d in days}) == 601
    assert [d['date'] for d in days] == sorted(d['date'] for d in days)
    assert sum(d['rows'] for d in days) == coverage['stock_days'] == 1719612
    assert sum(d['no_l2_facts'] for d in days) == 4999
    for i, f in enumerate(features):
        assert all(isinstance(d['missing'][i], int) and 0 <= d['missing'][i] <= d['rows'] for d in days)
        assert sum(d['missing'][i] for d in days) == coverage['missing_by_column'][f['model_column']]
    fresh = [d for d in days if d['attempt'] in {'production-r03', 'production-r04'} and d['complete_business_timing']]
    values = sorted(d['business_wall_seconds'] for d in fresh)
    assert len(values) == 328
    assert abs(statistics.median(values) - 346.8648029877804) < 1e-9
    assert abs(values[int((len(values)-1)*.95)] - 441.0842488920316) < 1e-9
    assert sum(v > 300 for v in values) == 235
    assert data['computation']['passed'] is True and data['computation']['performance_passed'] is False
    assert data['publication']['complete_tree_equal'] is True


def metadata(research, manifest, old_data):
    sys.path.insert(0, str(research / '因子/algobench/src'))
    from algobench.cancel_phase_registry import parse_cancel_phase_column, cancel_phase_registry_hash
    from algobench.depth_match_registry import depth_match_contract, depth_match_registry_hash
    from algobench.formal_model328_manifest import load_feature_manifest
    load_feature_manifest(research / '因子/algobench/configs/szse_model328_feature_manifest_v1.json')
    assert cancel_phase_registry_hash() == manifest['registry_hashes']['cancel']
    assert depth_match_registry_hash() == manifest['registry_hashes']['depth']
    from cancel_phase_math import report_equations
    from depth_match_math import formulas
    phase_math, depth_math = report_equations(), formulas()
    depth_specs = {f'{s["name"]}_{s["side"]}': s for s in depth_match_contract()['specs']}
    old_by_id = {f['metadata']['factor_id']: f['metadata'] for f in old_data['factors']}
    phase_titles = ['事件对集中度', '跨周期一致性', '交叉拟合总变差', '全委托归一能量', '跨订单集中度', '尖锐事件对集中度', '尖锐跨订单集中度']
    phase_notes = ['比较撤单年龄余数的事件对集中程度。', '从总配对中去掉同一周期内部配对。', '用不同周期子样本交叉检验相位分布的偏离。', '分子保留事件对能量，分母使用全部有效新委托数的平方。', '扣除同一订单内部的全部消息配对。', '使用20ms与50ms核的尖锐组合比较事件对。', '在跨订单消息对上使用尖锐核组合。']
    depth_js = (ROOT / 'tools/depth_match_report_20260907.js').read_text(encoding='utf8')
    import ast
    depth_notes = ast.literal_eval(re.search(r'const notes=(\[.*?\]);', depth_js, re.S).group(1))
    output = []
    for item in manifest['features']:
        f = dict(item)
        col, source = f['original_column'], f['source']
        if source == 'old':
            m = old_by_id[col]
            key = col.split('__')[0]
            d = old_data['definitions'][key]
            f.update(definition=key, layer=m['layer'], title=d['name'], description=d['description'], formula=d['formula'], denominator=m['denominator'], domain=m.get('domain'), math='')
        elif source.startswith('cancel_'):
            s = parse_cancel_phase_column(col)
            number = int(s.family_id[3:5])
            f.update(definition=col, layer='CPH', title=phase_titles[number-1] + f' · T{s.period_ms} / {s.kernel}', description=phase_notes[number-1], formula=f'年龄带[1,10)秒；T={s.period_ms}ms；核={s.kernel}；分母={s.denominator}', denominator=s.denominator, math=phase_math[f'CPH_{number}'], family=s.family_id)
        else:
            s = depth_specs[col]
            number = int(s['name'][2:4])
            f.update(definition=s['name'], layer='DM', title=s['title'], description=depth_notes[number-1], formula=s['formula'], denominator=s['denominator'], math=depth_math[f'DM{number:02}'], parameters=s['parameters'])
        output.append(f)
    assert Counter(f['layer'] for f in output) == Counter(L1=130, L2=8, L3=56, L4=6, L5=56, CPH=48, DM=24)
    return output


def figures(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family': 'Microsoft YaHei', 'axes.unicode_minus': False, 'svg.fonttype': 'path', 'svg.hashsalt': DAY, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#ced3c9', 'text.color': '#243648', 'axes.labelcolor': '#243648', 'xtick.color': '#61716f', 'ytick.color': '#61716f', 'font.size': 10})
    colors = {'old': '#243648', 'cancel_buy': '#087b78', 'cancel_sell': '#b24f35', 'depth': '#61716f'}
    n = data['coverage']['stock_days']
    ranked = sorted(data['features'], key=lambda f: (n-data['coverage']['missing_by_column'][f['model_column']])/n)
    fig, ax = plt.subplots(figsize=(10, 3.5), layout='constrained')
    for source, label in SOURCES.items():
        points = [(i+1, 100*(1-data['coverage']['missing_by_column'][f['model_column']]/n)) for i, f in enumerate(ranked) if f['source'] == source]
        ax.scatter(*zip(*points), s=13, color=colors[source], label=label)
    ax.set(xlabel='按全期有限值覆盖率由低到高排列（328列）', ylabel='有限值覆盖率 / %', ylim=(0, 103))
    ax.axhline(99, color='#ced3c9', linewidth=1, linestyle='--')
    ax.annotate('f96买卖两列：2.2385%', (1, 2.238528), xytext=(45, 25), arrowprops={'arrowstyle': '-', 'color': '#b24f35'}, color='#b24f35')
    ax.legend(frameon=False, ncols=4, loc='center right')
    fig.savefig(ASSETS/'coverage.svg', metadata={'Date': None, 'Title': '328列有限值覆盖率'})
    plt.close(fig)
    rows = [r for r in data['days'] if r['attempt'] in {'production-r03', 'production-r04'} and r['complete_business_timing']]
    fig, ax = plt.subplots(figsize=(10, 3.5), layout='constrained')
    vals = [r['business_wall_seconds'] for r in rows]
    ax.plot(np.arange(len(rows)), vals, color='#087b78', linewidth=1.1)
    for threshold, color in [(300, '#b24f35'), (240, '#61716f')]:
        ax.axhline(threshold, color=color, linestyle='--', linewidth=.8, label=f'{threshold}秒参考线')
    ticks = [0, len(rows)//2, len(rows)-1]
    ax.set_xticks(ticks, [rows[i]['date'] for i in ticks])
    ax.set(xlabel='本次完整执行四来源的新日期，按数据日期排列（328日）', ylabel='单日业务耗时 / 秒', ylim=(0, max(vals)*1.12))
    j = max(range(len(vals)), key=vals.__getitem__)
    ax.annotate('2026-06-26：1,335.13秒', (j, vals[j]), xytext=(-180, 8), textcoords='offset points', color='#b24f35')
    ax.legend(frameon=False, loc='upper left')
    fig.savefig(ASSETS/'timing.svg', metadata={'Date': None, 'Title': '本次328个完整新日期的业务耗时'})
    plt.close(fig)
    for name in ['coverage.svg','timing.svg']:
        path=ASSETS/name
        path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf8').splitlines())+'\n',encoding='utf8')


def build(research, evidence):
    data = json.loads(evidence.read_text(encoding='utf8'))
    manifest_path = research/'因子/algobench/configs/szse_model328_feature_manifest_v1.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    validate(data, manifest)
    old_html = (ROOT/'content/daily/2026-09-16.show.html').read_text(encoding='utf8')
    old = BeautifulSoup(old_html, 'html.parser')
    old_data = json.loads(gzip.decompress(base64.b64decode(old.select_one('#report-gzip').string)))
    data['features'] = metadata(research, manifest, old_data)
    data['periods'], data['sources'], data['layers'] = period_list(data['days']), SOURCES, LAYERS
    data['report_input_sha256'] = hashlib.sha256(evidence.read_bytes()).hexdigest()
    data['feature_manifest_content_sha256'] = manifest['content_sha256']
    data['registry_hashes'] = manifest['registry_hashes']
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS/'report-data.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n', encoding='utf8')
    (ASSETS/'feature-manifest.json').write_bytes(manifest_path.read_bytes())
    n, missing, fs, days = data['coverage']['stock_days'], data['coverage']['missing_by_column'], data['features'], data['days']
    headers = ['model_index', 'model_column', 'definition', 'source', 'direction', 'layer', 'period', 'stock_days', 'finite', 'nan', 'coverage_pct']
    feature_rows = [[f['index'], f['model_column'], f['title'], f['source'], f['direction'], f['layer'], 'full', n, n-missing[f['model_column']], missing[f['model_column']], (n-missing[f['model_column']])/n*100] for f in fs]
    write_csv('factor-coverage.csv', headers, feature_rows)
    write_csv('daily-coverage.csv', ['date', 'stock_days', 'no_l2_facts', 'attempt', 'complete_business_timing', 'business_wall_seconds', 'old_all_nan_rows', 'cancel_buy_all_nan_rows', 'cancel_sell_all_nan_rows', 'depth_all_nan_rows'], [[d['date'], d['rows'], d['no_l2_facts'], d['attempt'], d['complete_business_timing'], d['business_wall_seconds'], *[d['all_nan_rows'][s] for s in SOURCES]] for d in days])
    figures(data)
    depth_features = [f for f in fs if f['source']=='depth' and f['direction']=='buy']
    replacements = {
        'DEPTH_DEFINITIONS': md_table(['定义', '名称', '观察与限制'], [[f['definition'], f['title'], f['description']] for f in depth_features]),
        'YEAR_TABLE': md_table(['数据期', '交易日', '股票日', '无L2事实股票日'], [[y if y!='2026' else '2026上半年', sum(d['date'].startswith(y) for d in days), f"{sum(d['rows'] for d in days if d['date'].startswith(y)):,}", f"{sum(d['no_l2_facts'] for d in days if d['date'].startswith(y)):,}"] for y in ['2024','2025','2026']] + [['合计',601,'1,719,612','4,999']]),
        'FEATURE_APPENDIX': md_table(['索引','正式模型列','有限股票日','NaN股票日','覆盖率'], [[f['index'], '`'+f['model_column']+'`', f"{n-missing[f['model_column']]:,}", f"{missing[f['model_column']]:,}", f"{100*(1-missing[f['model_column']]/n):.6f}%"] for f in fs]),
    }
    source_rows = []
    for source, title in SOURCES.items():
        rates = [100*(1-missing[f['model_column']]/n) for f in fs if f['source']==source]
        source_rows.append([title, len(rates), f'{min(rates):.6f}%', f'{statistics.median(rates):.6f}%', f'{max(rates):.6f}%', f"{sum(d['all_nan_rows'][source] for d in days):,}"])
    replacements['SOURCE_TABLE'] = md_table(['来源','列数','覆盖率最小','中位','最大','来源全列NaN股票日'], source_rows)
    f96 = next(f for f in fs if f['original_column'].startswith('f96_'))
    f96_rows = []
    for y in ['2024','2025','2026']:
        ds = [d for d in days if d['date'].startswith(y)]
        total = sum(d['rows'] for d in ds); m = sum(d['missing'][f96['index']] for d in ds)
        f96_rows.append([y if y!='2026' else '2026上半年', f'{total-m:,}', f'{m:,}', f'{100*(1-m/total):.6f}%'])
    replacements['F96_YEAR_TABLE'] = md_table(['数据期（f96双侧分别相同）','有限股票日','NaN股票日','覆盖率'], f96_rows)
    md = (ROOT/'templates/model328-report-20261018.md').read_text(encoding='utf8')
    for name, value in replacements.items():
        md = md.replace('{{'+name+'}}', value)
    assert not re.search(r'\{\{[A-Z_]+\}\}', md)
    (ROOT/f'content/daily/{DAY}.md').write_text(md, encoding='utf8')
    body = md.split('---', 2)[2]
    body = re.sub(r'^# .*?\n', '', body, count=1, flags=re.M)
    body = body.split('### 附录：')[0]
    rendered = markdown.markdown(body, extensions=['tables','fenced_code'])
    parts = re.split(r'<h2>(.*?)</h2>', rendered)
    preface, sections = parts[0], []
    ids = ['definition','contract','results','factors','performance','evidence']
    for i, anchor in enumerate(ids):
        title, content = parts[1+i*2], parts[2+i*2]
        title = re.sub(r'^\d+\s*', '', title)
        if anchor=='results':content=preface+content+'<!--RESULTS-->'
        if anchor=='factors':content+='<!--ATLAS-->'
        if anchor=='performance':content+='<!--TIMING-->'
        if anchor=='evidence':content+='<!--DOWNLOADS-->'
        sections.append(f'<section id="{anchor}"><div class="section-head"><span class="num">{i+1:02}</span><h2>{title}</h2></div>{content}</section>')
    css = old.style.string.split('.detail-tabs')[0]
    shared_js = next(x.get_text() for x in old.find_all('script') if 'function linePlot' in x.get_text())
    helpers = shared_js[shared_js.index('function csv('):shared_js.index('function options(')]
    plot = shared_js[shared_js.index('function linePlot('):shared_js.index('const rolling=')]
    plot = plot.replace('lo-=pad;hi+=pad;', "lo-=pad;hi+=pad;if(unit==='%'){lo=0;hi=Math.min(100,hi);if(hi===0)hi=1}")
    page = (ROOT/'templates/model328-report-20261018.html').read_text(encoding='utf8')
    script = (ROOT/'tools/model328_report_20261018.js').read_text(encoding='utf8')
    script = script.replace('{{OLD_HELPERS}}',helpers).replace('{{OLD_PLOT}}',plot)
    substitutions = {'OLD_CSS':css, 'SECTIONS':'\n'.join(sections), 'SCRIPT':script,
        'REPORT_GZIP':base64.b64encode(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0)).decode(),
        'MARKDOWN_JSON':json.dumps(md,ensure_ascii=False).replace('</','<\\/')}
    for name,value in substitutions.items():page=page.replace('{{'+name+'}}',value)
    for image_name in ['coverage.svg', 'timing.svg']:
        encoded = base64.b64encode((ASSETS/image_name).read_bytes()).decode()
        page=page.replace(f'src="../assets/model328-2026-10-18/{image_name}"', f'src="data:image/svg+xml;base64,{encoded}" data-zoom="{image_name}"')
    page = re.sub(r'href="\.\./assets/model328-2026-10-18/([^"/]+)"', r'href="#" data-file="\1"', page)
    soup = BeautifulSoup(page,'html.parser')
    soup.select_one('#figure-image')['src']='data:image/svg+xml;base64,'+base64.b64encode((ASSETS/'coverage.svg').read_bytes()).decode()
    for image in soup.select('img[data-zoom]'):
        figure=soup.new_tag('figure')
        button=soup.new_tag('button',attrs={'class':'figure-button','data-zoom':image['alt'],'aria-label':'放大'+image['alt']})
        caption=soup.new_tag('figcaption');caption.string='点击图表放大并下载SVG。'+image['alt']+'；数据来自本批最终验收与计算汇总。'
        parent=image.parent
        image.extract();button.append(image);figure.append(button);figure.append(caption)
        parent.replace_with(figure)
    for t in soup.find_all('table'):
        if t.parent.get('class')!=['table-scroll']:
            wrapper=soup.new_tag('div',attrs={'class':'table-scroll'});t.wrap(wrapper)
    page=str(soup)
    controls = (ROOT/'templates/model328-report-controls-20261018.html').read_text(encoding='utf8')
    for name in ['RESULTS','ATLAS','TIMING','DOWNLOADS']:
        slot=re.search(r'<!--'+name+r'-->(.*?)<!--/'+name+r'-->',controls,re.S).group(1)
        page=page.replace('<!--'+name+'-->',slot)
    sys.path.insert(0,str(ROOT/'scripts'))
    import add_nav_scrollspy as spy
    page=spy.render(page,spy.PAPER,f'{DAY}.show.html')
    (ROOT/f'content/daily/{DAY}.show.html').write_text(page,encoding='utf8')
    print(json.dumps({'dates':len(days),'features':len(fs),'periods':len(data['periods']),'html_bytes':len(page.encode()),'markdown_bytes':len(md.encode()),'input_sha256':data['report_input_sha256']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--research-root',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,default=ROOT/'artifacts/model328-report-2026-10-18/accepted-aggregates.json')
    args=parser.parse_args()
    build(args.research_root,args.evidence)
