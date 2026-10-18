"""Build the 328-column performance atlas with the September 16 implementation."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import csv
import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import add_nav_scrollspy
from model328_definitions import metadata as describe_features

DAY = '2026-10-18'
ASSETS = ROOT / 'content/assets/model328-2026-10-18'
LAYERS = {'L1':'基础评分投影','L2':'多证据共识','L3':'微观结构情境','L4':'窗口状态','L5':'用途与流动性机制','CPH':'撤单相位','DM':'深度匹配'}
SOURCE_NAMES = {'old':'老因子256列','phase':'撤单相位48列','depth':'深度匹配24列'}


def fmt(v, digits=6):
    return f'{v:+.{digits}f}' if v is not None and math.isfinite(v) else '—'


def number(v, scale=1., digits=3):
    return fmt(v * scale, digits) if v is not None else '—'


def table(headers, rows):
    clean = lambda x: str(x).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| '+' | '.join(map(clean,headers))+' |', '|'+ '|'.join(['---']*len(headers))+'|',
                      *['| '+' | '.join(map(clean,row))+' |' for row in rows]])


def csv_file(path, headers, rows):
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(headers);writer.writerows(rows)


def brief(f, period=0):
    s=f['periods'][period];m=f['metadata']
    return [m['definition_key'], '买' if m['projection']=='buy' else '卖', fmt(s['ic'][0][0]),
            fmt(s['ic'][1][0]), number(s['ic'][1][3]), number(s['spread'][0][0],1e4),
            number(s['spread'][0][3]), int(s['ic'][1][4])]


def build(research, input_root):
    source=input_root/'report-data.json.gz'
    proof=json.loads((input_root/'evaluation-result.json').read_bytes())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==proof['report_sha256']
    data=json.loads(gzip.decompress(source.read_bytes()))
    factors=data['factors']; assert len(factors)==328 and len(data['dates'])==601 and len(data['periods'])==44
    assert proof['passed'] and proof['columns']==328 and proof['stock_days']==1719612
    assert proof['independent_daily_ic_checks']==601 and proof['daily_group_checks']==601*328*10
    assert proof['factor_acceptance_sha256']=='fc0f323dca7c222f0ec6dbe44e472447b2e4139aee76c67318d42a71c64bbd83'
    old_html=(ROOT/'content/daily/2026-09-16.show.html').read_text(encoding='utf-8')
    old=BeautifulSoup(old_html,'html.parser')
    old_data=json.loads(gzip.decompress(base64.b64decode(old.select_one('#report-gzip').string)))
    manifest_path=research/'因子/algobench/configs/szse_model328_feature_manifest_v1.json'
    manifest=json.loads(manifest_path.read_bytes())
    assert [r['metadata']['factor_id'] for r in factors]==[r['model_column'] for r in manifest['features']]
    descriptions=describe_features(research,manifest,old_data)
    definitions={}
    for f,d in zip(factors,descriptions):
        m=f['metadata'];key=m['definition_key']
        definitions[key]={'name':d['title'],'description':d['description'],'formula':d['formula'], 'math':d.get('math','')}
        assert len(f['periods'])==44 and len(f['daily_ic'])==len(f['daily_health'])==601
        assert f['distribution']['rows']==1719612
        assert f['details']['ols']['n']==f['distribution']['pairs']
        full=f['details']['scatter'].get('full')
        assert not full or full['included']==f['distribution']['pairs'] and full['outside']==0
    valid=[f for f in factors if f['periods'][0]['ic'][1][0] is not None]
    ranked=sorted(valid,key=lambda f:abs(f['periods'][0]['ic'][1][0]),reverse=True)
    significant=[f for f in valid if f['periods'][0]['ic'][1][3] is not None and abs(f['periods'][0]['ic'][1][3])>=2]
    opposite=[f for f in valid if f['periods'][0]['spread'][0][0] is not None and f['periods'][0]['ic'][1][0]*f['periods'][0]['spread'][0][0]<0]
    strongest=ranked[0];s=strongest['periods'][0]
    headline=(f"全期 |Rank IC| 最高的是{definitions[strongest['metadata']['definition_key']]['name']}"
              f"（{'买侧' if strongest['metadata']['projection']=='buy' else '卖侧'}）：{fmt(s['ic'][1][0])}，"
              f"NW t={number(s['ic'][1][3])}；G10−G1 为 {number(s['spread'][0][0],1e4)} bp。")
    yearly_comment=('同一列在2024、2025、2026年上半年的Rank IC分别为'
        +'、'.join(fmt(strongest['periods'][p]['ic'][1][0]) for p in [1,2,3])
        +'，G10−G1分别为'+'、'.join(number(strongest['periods'][p]['spread'][0][0],1e4) for p in [1,2,3])
        +' bp。年度相关方向保持一致，端点组差却发生变化；相关排序与两端收益需要分别判断。')
    scope_options='<option value="all">全部 328 列</option><option value="old">老因子 256 列</option><option value="phase">撤单相位 48 列</option><option value="depth">深度匹配 24 列</option>'
    ASSETS.mkdir(parents=True,exist_ok=True);(ASSETS/'factors').mkdir(exist_ok=True);(ASSETS/'evidence').mkdir(exist_ok=True)
    file_rows=[]
    for index,f in enumerate(factors,1):
        m=f['metadata'];alias=m['definition_key']+'__'+m['projection']
        packed=base64.b64encode(gzip.compress(json.dumps(f,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),compresslevel=9,mtime=0)).decode()
        path=ASSETS/'factors'/(alias+'.js')
        path.write_text('window.rawbankFactorLoaded('+json.dumps(alias)+','+json.dumps(packed)+');',encoding='utf-8')
        assert path.stat().st_size<25*1024**2
        file_rows.append({'path':'factors/'+path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        if index%64==0:print('factor assets',index,328,flush=True)
    slim={**data,'factors':[{k:f[k] for k in ('metadata','diagnostic','distribution')}|{'periods':[{k:p[k] for k in ('ic','spread')} for p in f['periods']]} for f in factors],
          'definitions':definitions,'layers':LAYERS,'asset_directory':ASSETS.name,
          'parameter_note':'窗口 [09:30,09:35)。老因子使用逐股票日六核及结构参数 v2；撤单相位和深度匹配沿用各自冻结定义。全部统计由本批新因子重新计算。',
          'evaluation_proof':proof}
    (ASSETS/'report-data.json').write_text(json.dumps(slim,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    (ASSETS/'feature-manifest.json').write_bytes(manifest_path.read_bytes())
    for name in ['evaluation-result.json','guard.json','resource-summary.json','benchmark-summary.json','label-alignment.json']:
        if (input_root/name).exists():(ASSETS/'evidence'/name).write_bytes((input_root/name).read_bytes())
    (ASSETS/'evidence/factor-assets.json').write_text(json.dumps(file_rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    headers=['model_column','definition','source','side','period','IC','Rank_IC','ICIR','Rank_NW_t','G10_minus_G1','spread_NW_t','IC_valid_days']
    summary_rows=[]
    for f in factors:
        for p,v in zip(data['periods'],f['periods']):
            m=f['metadata'];summary_rows.append([m['factor_id'],m['definition_key'],m['source'],m['projection'],p['id'],v['ic'][0][0],v['ic'][1][0],v['ic'][1][5],v['ic'][1][3],v['spread'][0][0],v['spread'][0][3],v['ic'][1][4]])
    csv_file(ASSETS/'all-period-performance.csv',headers,summary_rows)
    csv_file(ASSETS/'label-alignment.csv',['date','stock_days','valid_labels','panel_sha256','label_sha256'],[[r[k] for k in ['date','rows','valid_labels','panel_sha256','label_sha256']] for r in data['label_alignment']])
    head=['定义','方向','日均 IC','日均 Rank IC','Rank NW t','G10−G1 bp','组差 NW t','IC有效日']
    source_tables=[];source_rows=[]
    for key,label in SOURCE_NAMES.items():
        fs=[f for f in factors if f['metadata']['source'].startswith('cancel_')] if key=='phase' else [f for f in factors if f['metadata']['source']==key]
        vs=sorted([f for f in fs if f['periods'][0]['ic'][1][0] is not None],key=lambda f:abs(f['periods'][0]['ic'][1][0]),reverse=True)
        source_rows.append([label,len(fs),len(vs),fmt(vs[0]['periods'][0]['ic'][1][0]),vs[0]['metadata']['definition_key'],'买' if vs[0]['metadata']['projection']=='buy' else '卖'])
        top=vs[0];v=top['periods'][0]
        source_tables.append('### '+label+'\n\n'+table(head,[brief(f) for f in vs[:5]])
            +'\n\n该来源 |Rank IC| 最高的一列为 `'+top['metadata']['definition_key']+'`'
            +('买侧' if top['metadata']['projection']=='buy' else '卖侧')+'，日均Rank IC为'+fmt(v['ic'][1][0])
            +'，G10−G1为'+number(v['spread'][0][0],1e4)+' bp，组差NW t为'+number(v['spread'][0][3])
            +'。这两项统计分别描述全横截面排序和两端均值差；完整组形状与有效日数见逐因子明细。')
    year_rows=[]
    for p in [1,2,3]:
        ordered=sorted([f for f in factors if f['periods'][p]['ic'][1][0] is not None],key=lambda f:abs(f['periods'][p]['ic'][1][0]),reverse=True)
        f=ordered[0];year_rows.append([data['periods'][p]['id'],*brief(f,p)])
    resource=json.loads((input_root/'resource-summary.json').read_bytes()) if (input_root/'resource-summary.json').exists() else {}
    replacements={
        'HEADLINE':headline,'YEARLY_COMMENT':yearly_comment,'VALID_LABELS':f"{proof['valid_label_stock_days']:,}",'VALID_COLUMNS':str(len(valid)),
        'NO_IC_COLUMNS':str(328-len(valid)),'RAW_T_COLUMNS':str(len(significant)), 'OPPOSITE_COLUMNS':str(len(opposite)),
        'TOP_TABLE':table(head,[brief(f) for f in ranked[:20]]),
        'SOURCE_TABLE':table(['来源','列数','有IC列数','最高绝对值的Rank IC','对应定义','方向'],source_rows),
        'SOURCE_DETAILS':'\n\n'.join(source_tables),'YEAR_TABLE':table(['区间',*head],year_rows),
        'STABILITY_TABLE':table(['定义','方向','2024 Rank IC','2024组差bp','2025 Rank IC','2025组差bp','2026H1 Rank IC','2026H1组差bp'],
            [[f['metadata']['definition_key'],'买' if f['metadata']['projection']=='buy' else '卖',
              *[value for p in [1,2,3] for value in [fmt(f['periods'][p]['ic'][1][0]),number(f['periods'][p]['spread'][0][0],1e4)]]] for f in ranked[:10]]),
        'ALL_TABLE':table(['索引',*head],[[f['metadata']['index'],*brief(f)] for f in factors]),
        'RUN_SECONDS':f"{resource.get('业务墙钟秒',proof['elapsed_seconds']):.2f}",'CODE_REVISION':proof['code_revision'],
        'REPORT_SHA256':proof['report_sha256'],'RESOURCE_TABLE':table(['指标','实测'],[[k,v] for k,v in resource.items()]),
    }
    md=(ROOT/'templates/model328-report-20261018.md').read_text(encoding='utf-8')
    for key,value in replacements.items():md=md.replace('{{'+key+'}}',value)
    assert '{{' not in md
    (ROOT/f'content/daily/{DAY}.md').write_text(md,encoding='utf-8')
    old.title.string='深市328因子｜分组定标后的601日收益表现'
    old.select_one('meta[name="description"]')['content']='328列新因子的601日完整收益评价：日度IC/Rank IC、44区间、10/40分组收益、OLS、散点密度与原值分布。'
    old.select('.mast span')[1].string='研究归档 2026.10.18 · 新参数全期评价'
    old.select_one('h1').clear();old.select_one('h1').append(BeautifulSoup('分组定标之后，<br><em>328列因子与后续收益</em>','html.parser'))
    old.select_one('.subtitle').string='601 日 · 每一列的相关与分组收益'
    old.select_one('.lead').string='用逐股票日六核及结构参数v2重算老因子，与撤单相位、深度匹配共同组成328列。逐列观察与同日短窗口收益的关系，保留全部日度、分期、分组与完整样本诊断。'
    old.select_one('.hero-note strong').string='328'
    old.select_one('.hero-note small').string='256 老因子 + 48 撤单相位 + 24 深度匹配'
    definition=old.select_one('#definition')
    definition.select('tbody tr')[-1].decompose()
    definition.select_one('tbody').append(BeautifulSoup('<tr><td>CPH 撤单相位</td><td>7族、2周期、heat/sharp核，买卖独立；按事件对、跨周期、跨订单或全部委托数平方归一。</td><td>撤单年龄余数的集中、跨周期相干与跨样本偏离。</td></tr><tr><td>DM 深度匹配</td><td>12种定义分别投影买卖侧，涉及一档/两档数量、执行确认、价格空间、撤余量和持续性。</td><td>订单提交量与提交前可见深度的匹配及后续可观测证据。</td></tr>','html.parser'))
    definition.select_one('.formula').replace_with(BeautifulSoup('<div class="formula">256 + 24 + 24 + 24 = 328<small>老因子保留冻结模型清单中的256列，按注册公式投影；买卖通常共用全部有效去重新委托分母。撤单相位使用各自事件对、周期对、跨订单对或全部委托数平方等分母；深度匹配以全部有效去重新委托为分母。每列的具体公式和身份见浏览器。</small></div>','html.parser'))
    definition.select_one('.note').clear();definition.select_one('.note').append(BeautifulSoup('<p>本批老因子使用逐股票日六核参数与结构参数v2，72列新族使用各自冻结定义。本页对新面板重新计算全部收益统计。601日结果属于历史样本内描述，分组定标使用全期行为数据；不能将此页称为严格样本外检验。</p>','html.parser'))
    contract=old.select_one('#contract')
    direct=contract.find_all('p',recursive=False)[0]
    direct.string=f"收益标签沿用9月16日同口径的封存文件，共{proof['valid_label_stock_days']:,}个有效收益股票日。601日因子与标签股票日键一一对应；逐列使用因子与收益均有限的成对样本。"
    results=old.select_one('#results')
    for e in results.select('.note'):e.decompose()
    note=BeautifulSoup('<div class="note"><p>'+html.escape(headline)+'</p><p>'+html.escape(yearly_comment)+'</p><p>'+f'328列中，{len(valid)}列具有有效IC；{328-len(valid)}列无有效IC日。{len(significant)}列的原始 |Rank IC NW t|≥2，尚未做多重比较调整。{len(opposite)}列的Rank IC与G10−G1均值方向相反，应结合分组曲线判断。'+'</p></div>','html.parser')
    results.select_one('#result-note').insert_before(note)
    for selector in ['#result-scope','#factor-scope']:
        old.select_one(selector).clear();old.select_one(selector).append(BeautifulSoup(scope_options,'html.parser'))
    old.select_one('#factors .eyebrow').string='FACTOR ATLAS · 328 SERIES'
    old.select_one('#layer-filter option').string='全部 7 个层次'
    evidence=old.select_one('#evidence');evidence.clear()
    evidence.append(BeautifulSoup('<div class="section-head"><span class="num">05</span><div><h2>数据身份与收益评价证据</h2><p class="subtle">2026年10月18日 · 新参数328列 · 完整601日</p></div></div>'
        +'<div class="table-scroll evidence"><table><tbody>'
        +''.join('<tr><th>'+html.escape(str(k))+'</th><td>'+html.escape(str(v))+'</td></tr>' for k,v in [
            ('评价范围','601日、328列、1,719,612股票日、44区间；原始方向、日度等权'),
            ('结果核对','全部601日面板和标签完整SHA、唯一股票日键通过；每日一列IC独立对照601次；10/40分组计数逐日守恒；1,971,280个十分组位置保留诊断，非空组均值独立归约通过；328列全配对密度计数通过'),
            ('因子参数','逐股票日六核参数、结构参数v2；328列冻结清单 '+manifest['content_sha256']),
            ('标签规格',proof['label_spec_hash']),('评价代码',proof['code_revision']),
            ('完整聚合结果SHA-256',proof['report_sha256']),('完整业务命令',f"{resource.get('业务墙钟秒',proof['elapsed_seconds']):.2f}秒；其中统计主体{proof['elapsed_seconds']:.2f}秒；资源详见下载凭证")])
        +'</tbody></table></div><div class="download-row"><button id="download-proof">下载评价验收 JSON</button><button id="download-alignment">下载收益样本对齐 CSV</button>'
        +'<a href="../assets/model328-2026-10-18/all-period-performance.csv" download>下载全部328列×44区间 CSV</a>'
        +'<a href="../assets/model328-2026-10-18/evidence/guard.json" download>运行资源凭证</a>'
        +'<a href="../assets/model328-2026-10-18/evidence/benchmark-summary.json" download>4/8/16进程对照</a>'
        +'<a href="../assets/model328-2026-10-18/feature-manifest.json" download>328列冻结清单</a></div>','html.parser'))
    old.select_one('#report-gzip').string=base64.b64encode(gzip.compress(json.dumps(slim,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0)).decode()
    old.select_one('#proof-data').string=json.dumps(proof,ensure_ascii=False,separators=(',',':'))
    for script in old.find_all('script'):
        if 'function linePlot' in script.get_text():script.string=(ROOT/'scripts/rawbank_report_view.js').read_text(encoding='utf-8')
    old.select_one('footer .wrap').string='思瑞投资 · 2026-10-18 / 新参数因子历史样本内评价 / 原始方向、日度等权、未扣成本'
    old.style.string=old.style.string+'\n.num{opacity:.85}.chart-note{font-size:12px}.hero-note small{max-width:280px}.formula math{margin-top:18px}\n'
    page=ROOT/f'content/daily/{DAY}.show.html';page.write_text(str(old),encoding='utf-8')
    add_nav_scrollspy.patch(page,add_nav_scrollspy.PAGES[page.name])
    assert page.stat().st_size<25*1024**2
    validation={'columns':328,'dates':601,'periods':44,'valid_ic_columns':len(valid),'no_ic_columns':328-len(valid),
                'raw_rank_nw_t_ge_2_columns':len(significant),'opposite_rank_and_spread_columns':len(opposite),
                'factor_asset_count':len(file_rows),'source_report_sha256':proof['report_sha256'],'page_bytes':page.stat().st_size}
    (ROOT/'artifacts/model328-report-2026-10-18/validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--research-root',type=Path,required=True);parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args();build(args.research_root.resolve(),args.input.resolve())
