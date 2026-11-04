"""Build the November 1 atlas from nine accepted aggregate datasets."""
import argparse
import base64
from collections import Counter
import csv
from datetime import date
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import re
import zipfile
import os
from daily_show_source import resolve_daily_show_source

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/szse683-2026-11-01'
SOURCES = {'old': '既有行为', 'cancel_buy': '买侧撤单相位', 'cancel_sell': '卖侧撤单相位', 'depth': '深度匹配'}
SEGMENTS = {'full': '合并683日', 'base': '原601日', 'increment': '新增82日'}
HORIZONS = {'10m': '10分钟', 'lunch': '午间', 'close': '收盘'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return base64.b64encode(gzip.compress(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), mtime=0)).decode()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def write_csv(path, head, rows):
    opener = lambda: (io.TextIOWrapper(gzip.GzipFile(filename=str(path),mode='wb',mtime=0),encoding='utf-8-sig',newline='')
        if path.suffix=='.gz' else path.open('w',encoding='utf-8-sig',newline=''))
    with opener() as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def table(head, rows):
    cell = lambda x: html.escape(str(x if x is not None else '—'))
    return '<table><thead><tr>' + ''.join('<th>'+cell(x)+'</th>' for x in head) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+cell(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def median(values):
    values = [x for x in values if x is not None and np.isfinite(x)]
    return float(np.median(values)) if values else None


def fmt(value, digits=5):
    return '—' if value is None or not np.isfinite(value) else f'{value:.{digits}f}'


def category_rows(data):
    result = []
    for source, label in SOURCES.items():
        fs = [f for f in data['factors'] if f['metadata']['source'] == source]
        result.append([label, len(fs), fmt(median([f['distribution']['finite']/f['distribution']['rows']*100 for f in fs]), 2)+'%',
            sum(f['periods'][0]['ic'][1][4]>0 for f in fs),
            fmt(median([abs(f['periods'][0]['ic'][1][0]) if f['periods'][0]['ic'][1][0] is not None else None for f in fs])),
            fmt(median([f['periods'][0]['spread'][0][0]*1e4 if f['periods'][0]['spread'][0][0] is not None else None for f in fs]), 3)])
    return result


CATEGORY_HEAD = ['来源', '列数', '有限值覆盖中位数', '有IC列数', '|Rank IC|中位数', 'G10−G1中位数 / bp']


def overlap_table(overlap, metadata, segment):
    matrix = np.array(overlap['segments'][segment]['mean'], dtype=float)
    rows = []
    keys = list(SOURCES)
    for a, source_a in enumerate(keys):
        ia = [i for i,r in enumerate(metadata) if r['source'] == source_a]
        for source_b in keys[a:]:
            ib = [i for i,r in enumerate(metadata) if r['source'] == source_b]
            values = [abs(matrix[i,j]) for i in ia for j in ib if (source_a!=source_b or i<j) and np.isfinite(matrix[i,j])]
            rows.append([SOURCES[source_a], SOURCES[source_b], len(values), fmt(float(np.median(values)) if values else None),
                fmt(float(np.quantile(values,.95)) if values else None), sum(v>=.8 for v in values)])
    return table(['来源A', '来源B', '有效列对', '|日均相关|中位数', 'P95', '≥0.8列对'], rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--exchange', choices=('XSHE','XSHG'), default='XSHE')
    p.add_argument('--collection-sha256')
    p.add_argument('--date', type=date.fromisoformat)
    p.add_argument('--trial', action='store_true')
    p.add_argument('--output-root', type=Path)
    p.add_argument('--html-relative-path', help='沪市展示文件相对于content/daily的路径')
    a = p.parse_args()
    sse=a.exchange=='XSHG'
    if a.html_relative_path and not sse:p.error('自定义展示路径仅用于沪市')
    if a.trial and not sse:p.error('试运行入口仅用于沪市')
    if sse and (not a.date or not re.fullmatch('[0-9a-f]{64}',a.collection_sha256 or '')):
        p.error('沪市需要发布日期和明确的集合SHA256')
    if a.output_root and not a.trial:p.error('隔离输出目录仅用于试运行')
    if a.trial and (not a.output_root or not a.output_root.resolve().is_relative_to((ROOT/'.local/runs').resolve())):
        p.error('试运行目录必须位于汇报仓库.local/runs内')
    output_root=a.output_root.resolve() if a.trial else ROOT
    slug=f'sse683-{a.date.isoformat()}' if sse else 'szse683-2026-11-01'
    assets=output_root/'content/assets'/slug
    target=output_root/'content/daily'/f'{a.date:%Y-%m.%d}.show.html' if sse else ROOT/'content/daily/2026-11.01.show.html'
    if a.html_relative_path:target=resolve_daily_show_source(output_root/'content/daily',a.html_relative_path)
    markdown=output_root/'content/daily'/f'{a.date.isoformat()}.md' if sse else None
    if sse and (target.exists() or markdown.exists() or assets.exists()):
        raise FileExistsError('沪市发布日期的正文、展示文件或资产目录已存在，须由用户处理占用')
    ncol=340 if sse else 344
    days=10 if a.trial else 683
    segment_days={'full':days,'base':10 if a.trial else 601}
    if not a.trial:segment_days['increment']=82
    segments={k:SEGMENTS[k] for k in segment_days}
    if a.trial:segments.update(full='10日试运行',base='原601日内10日')
    source = zipfile.Path(a.input) if a.input.is_file() else a.input
    proof = json.loads((source/'evaluation-result.json').read_bytes())
    assert proof['passed'] and proof['dates']==days and proof['columns']==ncol
    assert bool(proof.get('trial'))==a.trial
    assert a.trial or proof['stock_days']==(1560216 if sse else 1957362)
    assert proof['collection_sha256']==(a.collection_sha256 if sse else '3837fdfe461bf053eeb1f59d6aef8f6e2d550dfe3c11aac2875cd802b11549f6')
    assert proof['feature_manifest_sha256']==('1675c3fcf6c19dd53a4d19b67a2c7e4b67704fcb543e29f964faa246fcb443be' if sse else '6614fc78927452ea9f45ab6fc7d15f7d9515cef41270a5ab6db3d1d8f9a7b784')
    assert not sse or proof['exchange']=='XSHG'
    assert {r['id'] for r in proof['datasets']}=={s+'-'+h for s in segments for h in HORIZONS}
    acceptance=json.loads((source/'consumer-acceptance.json').read_bytes())
    assert acceptance['passed'] and acceptance['kind']=='evaluation' and acceptance['guard_exit_code']==0 and acceptance['scope_absent']
    assert acceptance['source_document_sha256']==digest((source/'evaluation-result.json').read_bytes())
    export=json.loads((source/'EXPORT_FORMAT.json').read_bytes())
    assert export['schema']=='szse683-atlas-normalized-export-v1' and len(export['bundles'])==ncol*3
    bundle_index={r['path']:r for r in export['bundles']}
    assets.mkdir(parents=True, exist_ok=True)
    old_page = (ROOT/'content/daily/2026-09-16.show.html').read_text(encoding='utf-8')
    old = json.loads(gzip.decompress(base64.b64decode(re.search(r'id="report-gzip"[^>]*>(.*?)</script>',old_page,re.S)[1])))
    previous = json.loads((ROOT/'content/assets/model328-2026-10-18/report-data.json').read_bytes())
    definitions = {**old['definitions'], **previous['definitions']}
    for key in ('f26_aggburst_c', 'f27_childseq_c'):
        number=key.split('_',1)[0]
        definitions[key] = {**definitions[key],
            'description': definitions[key]['description']+' 当前按同侧相邻主动事件归组，连接时间差不超过3.11秒，整数数量门满足10×|Q₂−Q₁|≤min(Q₁,Q₂)；逐单完整观察要求剩余窗口严格大于3.11秒。采用当前v7注册表及冻结参数。',
            'formula': f'Σ（方向内可观察订单的score_v2贡献）/ N；{number}_adjacent_v2。'}
    layers = {**previous['layers']}
    datasets, source_factors, inventory, csv_rows = {}, {}, [], []
    definition_keys=None
    public_proof = {k:v for k,v in proof.items() if k not in ('workers','elapsed_seconds')}
    public_proof['daily_group_positions']=public_proof.pop('group_mean_checks')
    public_proof['consumer_acceptance']={k:v for k,v in acceptance.items() if k!='guard_manifest'}
    for item in proof['datasets']:
        key = item['id']
        raw = (source/key/'summary.json.gz').read_bytes()
        assert digest(raw)==item['summary_sha256']
        data = json.loads(gzip.decompress(raw))
        fs = data['factors']
        keys={f['metadata']['definition_key'] for f in fs}
        if definition_keys is None:
            definition_keys=keys
            definitions={k:definitions[k] for k in sorted(keys)}
            active_layers={f['metadata']['layer'] for f in fs}
            layers={k:v for k,v in layers.items() if k in active_layers}
            assert set(layers)==active_layers
        else:
            assert keys==definition_keys
        source_factors[key] = [dict(f) for f in fs]
        assert len(fs)==ncol and Counter(f['metadata']['source'] for f in fs)==Counter(old=272,cancel_buy=24,cancel_sell=24,depth=20 if sse else 24)
        assert len(data['dates'])==segment_days[data['segment']]
        assert sum(r['rows'] for r in data['label_alignment'])==item['stock_days']
        assert sum(r['valid_labels'] for r in data['label_alignment'])==item['valid_label_stock_days']
        assert len({(f['metadata']['definition_key'],f['metadata']['projection']) for f in fs})==ncol
        out = assets/key
        out.mkdir(parents=True,exist_ok=True)
        for f in fs:
            m = f['metadata']
            assert m['definition_key'] in definitions
            for period, summary in zip(data['periods'],f['periods']):
                csv_rows.append([key,m['factor_id'],m['source'],m['projection'],period['id'],*summary['ic'][0],*summary['ic'][1],*summary['spread'][0]])
            for field in ('index','path','sha256'):
                f.pop(field,None)
        data.update(definitions=definitions,layers=layers,asset_directory=f'{slug}/{data["horizon"]}',dataset_context=key,asset_context=data['horizon'],
            parameter_note='窗口[09:30,09:35)，当前v7定义与冻结逐股票日参数保持原方向。',evaluation_proof=public_proof)
        (out/'summary.js').write_text('window.szseAtlasLoaded('+json.dumps(key)+','+json.dumps(encode(data))+');',encoding='utf-8')
        datasets[key]=data
    for h in HORIZONS:
        out=assets/h/'factors'
        out.mkdir(parents=True,exist_ok=True)
        for j in range(ncol):
            path=f'bundles/{h}/factors/{j:03}.json.gz'
            raw=(source/path).read_bytes()
            assert digest(raw)==bundle_index[path]['sha256']
            packet=json.loads(gzip.decompress(raw))
            assert packet['schema']=='rawbank-segmented-factor-v1' and len(packet['daily_ic'])==days
            for segment in segments:
                key=segment+'-'+h
                f=source_factors[key][j]
                part=packet['segments'][segment]
                assert packet['metadata']==f['metadata'] and part['distribution']==f['distribution']
                assert [{k:packet['periods'][i][k] for k in ('ic','spread')} for i in part['period_indexes']]==f['periods']
                assert part['slice']==[{'full':0,'base':0,'increment':601}[segment],{'full':days,'base':segment_days['base'],'increment':days}[segment]]
            m=packet['metadata'];name=m['definition_key']+'__'+m['projection']
            factor_target=out/(name+'.js')
            factor_target.write_text('window.rawbankFactorLoaded('+json.dumps(name)+','+json.dumps(base64.b64encode(raw).decode())+','+json.dumps(h)+');',encoding='utf-8')
            inventory.append(dict(path=str(factor_target.relative_to(assets)).replace('\\','/'),sha256=digest(factor_target.read_bytes()),bytes=factor_target.stat().st_size))
    full=datasets['full-10m']
    evidence_by_id={r['id']:r for r in proof['datasets']}
    coverage=[]
    for h in HORIZONS:
        merged=evidence_by_id['full-'+h]
        for field in (() if a.trial else ('dates','stock_days','valid_label_stock_days')):
            assert merged[field]==sum(evidence_by_id[s+'-'+h][field] for s in ('base','increment'))
        for segment in segments:
            r=evidence_by_id[segment+'-'+h]
            coverage.append([HORIZONS[h],segments[segment],r['dates'],f'{r["stock_days"]:,}',
                f'{r["valid_label_stock_days"]:,}',f'{r["stock_days"]-r["valid_label_stock_days"]:,}',
                f'{r["valid_label_stock_days"]/r["stock_days"]:.2%}'])
    metadata=[f['metadata'] for f in full['factors']]
    current_old={r['original_column']:r for r in metadata if r['source']=='old'}
    mapping=[]
    for factor in old['factors']:
        m=factor['metadata']; col=m['factor_id']; hit=current_old.get(col)
        if hit:status='列名与方向对应；参数及方法按当前版本，未断言数值等价'
        else:
            candidates=[r for r in metadata if r['source']=='old' and r['definition_key']==col.split('__')[0] and r['projection']==m['projection']]
            hit=candidates[0] if len(candidates)==1 else None
            status='定义身份可对应，score_v2列名与方法改变' if hit else ('旧诊断指标；当前集合未收录' if factor['diagnostic'] else '当前集合未收录')
        mapping.append([col,m['projection'],hit['factor_id'] if hit else '',status])
    assert len(mapping)==288
    exact=sum(r[0] in current_old for r in mapping)
    modified=sum('score_v2' in r[3] for r in mapping)
    missing=288-exact-modified
    write_csv(assets/'column-mapping.csv',['old_column','direction','current_column','mapping_status'],mapping)
    stats=['mean','ordinary_se','nw_se_lag1','nw_t','valid_days','icir','positive_fraction']
    write_csv(assets/'all-context-performance.csv.gz',['context','model_column','source','side','period',*[f'{kind}_{s}' for kind in ('IC','RankIC','G10_G1') for s in stats]],csv_rows)
    overlap=json.loads((source/'factor-overlap.json').read_bytes())
    assert overlap['columns']==[r['factor_id'] for r in metadata]
    write_json(assets/'factor-overlap.json',overlap)
    write_json(assets/'definitions.json',definitions)
    write_json(assets/'evaluation-result.json',public_proof)
    write_json(assets/'factor-assets.json',inventory)
    write_json(assets/'evaluation-contract.json',dict(return_contract=full['label_contract'],statistics_schema=full['statistics_schema'],
        daily_equal=True,min_ic_names=30,nw_kernel='Bartlett',nw_lag=1,ties='average_rank_same_group',missing='not_zero',
        scatter='all_pairs_128x96_density',ols='pooled_intercept_no_independent_t_p',collection_sha256=proof['collection_sha256']))
    comparison=None
    if sse and not a.trial:
        from sse683_report import comparison_data
        comparison=comparison_data(datasets,ROOT)
        write_csv(assets/'market-comparison.csv.gz',
            ['context','sse_column','szse_column','source','match_method',*[m+'_'+v for m in ('sse','szse') for v in comparison['metrics']],'rank_same_sign'],
            ([key,*col,*row] for key,context in comparison['contexts'].items() for col,row in zip(comparison['columns'],context['rows'])))
    downloads={'column-mapping.csv':'text/csv;charset=utf-8','all-context-performance.csv.gz':'application/gzip',
        'factor-overlap.json':'application/json;charset=utf-8','definitions.json':'application/json;charset=utf-8',
        'evaluation-contract.json':'application/json;charset=utf-8','factor-assets.json':'application/json;charset=utf-8'}
    for name,mime in downloads.items():
        raw=(assets/name).read_bytes()
        encoded=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
        (assets/(name+'.js')).write_text('window.rawbankFileLoaded('+json.dumps(name)+','+json.dumps(encoded)+','+json.dumps(mime)+');',encoding='utf-8')
    contexts={}
    all_category=[]
    for h,label in HORIZONS.items():
        base=datasets['base-'+h]['factors'];inc=datasets[('base' if a.trial else 'increment')+'-'+h]['factors']
        for segment in segments:
            key=segment+'-'+h
            contexts[key]=dict(category=table(CATEGORY_HEAD,category_rows(datasets[key])),overlap=overlap_table(overlap,metadata,segment))
            for row in category_rows(datasets[key]):
                indices=[i for i,r in enumerate(metadata) if SOURCES[r['source']]==row[0]]
                pairs=[(base[i]['periods'][0]['ic'][1][0],inc[i]['periods'][0]['ic'][1][0]) for i in indices]
                pairs=[(a,b) for a,b in pairs if a is not None and b is not None]
                same=sum(np.sign(a)==np.sign(b) for a,b in pairs)
                all_category.append([label,segments[segment],*row,f'{same}/{len(pairs)}'])
    css=re.search(r'<style>(.*?)</style>',old_page,re.S)[1]
    css+='\n.context-controls{background:#e7eee8;padding:18px;margin:22px 0}.context-controls p{margin:0;align-self:end}.context-controls select{max-width:100%}.context-controls[aria-busy="true"]{opacity:.7}#context-status{font-size:13px}#context-retry{min-height:40px}td{font-variant-numeric:tabular-nums}::selection{background:#bdd4c9;color:#153e38}input::placeholder{color:#61716f}button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid #b24f35;outline-offset:3px}.hero h1{font-size:clamp(30px,4.2vw,60px)}#definition details{margin-top:18px}@media(max-width:700px){.context-controls{padding:14px}.controls select,.controls input{min-height:44px}.hero h1{font-size:32px}}'
    explorer=(ROOT/'scripts/rawbank_explorer.html').read_text(encoding='utf-8').replace('288 SERIES',f'{ncol} SERIES').replace('全部 6 个层次','全部研究层次')
    explorer=re.sub(r'<div class="eyebrow">.*?</div>','',explorer)
    explorer=explorer.replace('<option value="all">全部 288 列</option><option value="formal">284 列正式因子</option><option value="diagnostic">4 列诊断指标</option>', '<option value="all">全部344列</option><option value="old">既有行为272列</option><option value="phase">撤单相位48列</option><option value="depth">深度匹配24列</option>')
    explorer=explorer.replace('<option value="total">总量诊断</option>','').replace('class="eyebrow" data-key="factor-identity"','class="small" data-key="factor-identity"')
    template=(ROOT/'scripts/szse683_report.html').read_text(encoding='utf-8')
    if sse:
        from sse683_report import adapt_template
        template=adapt_template(template,proof,datasets,slug,a.date,comparison,encode,table,a.trial)
        explorer=explorer.replace('344列','340列').replace('深度匹配24列','深度匹配20列')
    context_js=(ROOT/'scripts/szse683_context.js').read_text(encoding='utf-8')
    if sse:
        context_js=context_js.replace('szse683-2026-11-01',slug)
        if a.trial:context_js=context_js.replace('合并683日','10日试运行').replace('原601日','原601日内10日')
    replacements=dict(CSS=css,MAPPING_NOTE=f'旧288列中，{exact}列可按原始列名与方向对应，{modified}列发生score_v2方法及列名变化，{missing}列未进入当前集合；当前另有72列撤单相位及深度匹配。名称对应仅用于追溯定义，不用于拼接数值。',
        MAPPING_TABLE=table(['旧列名','方向','当前列名','对应说明'],mapping),
        CATEGORY=contexts['full-10m']['category'],CATEGORY_ALL=table(['周期','样本',*CATEGORY_HEAD,'601/82日Rank IC同号列数'],all_category),
        OVERLAP=contexts['full-10m']['overlap'],EXPLORER=explorer,
        COVERAGE_TABLE=table(['收益周期','样本','日期数','因子股票日','有效收益','缺失收益','收益覆盖率'],coverage),
        EVALUATION_NOTE=f'评价正常退出，{acceptance["native_objects_verified"]:,}个输出对象原生回读通过。三个周期均覆盖{days}日；逐日IC独立对照分别为'+ '、'.join(HORIZONS[h]+str(n)+'日' for h,n in proof['independent_daily_ic_checks'].items())+f'；覆盖{proof["group_mean_checks"]:,}个日度十分组位置，逐组保留计数，非空组均值独立复算；{proof["density_count_checks"]:,}列上下文的完整散点计数守恒。',
        REVISION=proof['code_revision'],PAYLOAD=encode(full),PROOF=json.dumps(public_proof,separators=(',',':')),
        CONTEXT_TABLES=json.dumps(contexts,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'),
        JS=(ROOT/'scripts/rawbank_report_view.js').read_text(encoding='utf-8'),
        DOWNLOAD_JS=(ROOT/'scripts/rawbank_file_downloads.js').read_text(encoding='utf-8'),
        CONTEXT_JS=context_js+('\n'+(ROOT/'scripts/sse683_comparison.js').read_text(encoding='utf-8') if sse else ''))
    for key,value in replacements.items():template=template.replace('__'+key+'__',value)
    assert not re.search(r'__[A-Z_]+__',template)
    from add_nav_scrollspy import render, PAPER
    template=render(template,PAPER,target.name)
    asset_prefix=Path(os.path.relpath(output_root/'content/assets',target.parent)).as_posix()+'/'
    template=template.replace('../assets/',asset_prefix)
    if comparison:
        comparison_bytes=len(encode(comparison).encode())+(assets/'market-comparison.csv.gz').stat().st_size+(ROOT/'scripts/sse683_comparison.js').stat().st_size
        assert comparison_bytes<=1024**2
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(template,encoding='utf-8')
    if sse and not a.trial:
        from sse683_report import markdown as render_markdown
        markdown.write_text(render_markdown(a.date,target.relative_to(output_root/'content/daily'),proof,len(comparison['columns'])),encoding='utf-8')
    assert target.stat().st_size<25*1024**2 and all(p.stat().st_size<25*1024**2 for p in assets.rglob('*') if p.is_file())
    print(json.dumps(dict(html_bytes=target.stat().st_size,assets=len(inventory),exact_old_matches=exact,changed=modified,omitted=missing)))


if __name__=='__main__':main()
