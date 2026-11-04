import base64
from copy import deepcopy
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_szse683_report as builder
from factor_atlas_comparison import compare_contexts, decode_summary, pair_columns, rank_correlation
from sse683_report import adapt_template


def factor(name, definition=None, value=1, source='old'):
    return dict(metadata=dict(factor_id=name,definition_key=definition or name,projection='buy',source=source),
                periods=[dict(ic=[[value]*7,[value]*7],spread=[[value]*7])])


def test_pair_identity_missing_and_ambiguity():
    left=[factor('a'),factor('renamed','b'),factor('only_sse')]
    right=[factor('a'),factor('b'),factor('only_szse')]
    pairs,a,b=pair_columns(left,right)
    assert pairs==[(0,0,'factor_id'),(1,1,'definition_projection')]
    assert a==['only_sse'] and b==['only_szse']
    with pytest.raises(ValueError,match='歧义'):
        pair_columns([factor('c','a')],[factor('a1','a'),factor('a2','a')])
    with pytest.raises(ValueError,match='不符'):
        pair_columns([factor('a')],[factor('a',source='depth')])


def test_comparison_ties_signs_missing_and_date_binding():
    a=[factor('a',value=0),factor('b',value=1),factor('c',value=1),factor('d',value=None)]
    b=[factor('a',value=0),factor('b',value=-1),factor('c',value=1),factor('d',value=1)]
    left={'full-10m':dict(dates=['2024-01-02'],factors=a)}
    right={'full-10m':dict(dates=['2024-01-02'],factors=b)}
    result=compare_contexts(left,right)['contexts']['full-10m']
    assert [r[-1] for r in result['rows']]==[True,False,True,None]
    assert result['groups'][0][1:4]==[4,3,2]
    assert rank_correlation([(1,4),(1,4),(2,3),(3,1)])==pytest.approx(-1)
    assert rank_correlation([(1,3),(1,4)]) is None
    right['full-10m']['dates']=['2024-01-03']
    with pytest.raises(ValueError,match='日期'):compare_contexts(left,right)


def test_sse_template_replaces_market_identity():
    proof=dict(dates=683,stock_days=1560216,collection_sha256='a'*64,feature_manifest_sha256='b'*64,
        datasets=[dict(id='base-10m',stock_days=1370521),dict(id='increment-10m',stock_days=189695)])
    data={'full-10m':dict(factors=[dict(metadata=dict(scope_sha256='4137a50de897f42939892ad814bd4417e8791823d0fea34eb19db5f1221a6666'))])}
    source=(ROOT/'scripts/szse683_report.html').read_text(encoding='utf-8')
    result=adapt_template(source,proof,data,'sse683-2026-11-04',date(2026,11,4),None,builder.encode,builder.table)
    for text in ('沪市340','1,560,216','1,370,521','189,695','20 深度匹配','scope没有登记定义域'):assert text in result
    for text in ('深市344','1,957,362','237,750','37个签收批次','5b608dd6','szse683-2026-11-01'):assert text not in result


def test_date_occupancy_stops_before_input_read(tmp_path,monkeypatch):
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    daily=tmp_path/'content/daily';daily.mkdir(parents=True)
    (daily/'2026-11-04.md').write_text('其他任务',encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['build','--input','absent.zip','--exchange','XSHG','--collection-sha256','a'*64,'--date','2026-11-04'])
    with pytest.raises(FileExistsError,match='占用'):builder.main()
    assert not (tmp_path/'content/assets').exists()


def test_trial_build_isolated_and_restores_all_bundles(tmp_path,monkeypatch):
    """用合成统计贯通构建断言；此处不代表公司数据的10日业务贯通。"""
    _,baseline=decode_summary(ROOT/'content/assets/szse683-2026-11-01/full-10m/summary.js')
    factors=[]
    for f in baseline['factors']:
        if f['metadata']['source']=='depth' and sum(r['metadata']['source']=='depth' for r in factors)>=20:continue
        row=deepcopy(f)
        row['metadata']['scope_sha256']='4137a50de897f42939892ad814bd4417e8791823d0fea34eb19db5f1221a6666'
        row['distribution']=dict(finite=1000,rows=1000,pairs=950)
        row['periods']=[dict(ic=[[.01,.02,.03,.4,10,.5,.6],[.02,.03,.04,.5,10,.6,.7]],spread=[[.001,.002,.003,.4,10,.5,.6]])]
        factors.append(row)
    assert len(factors)==340
    # 仅把构建器已有只读参照放进测试根，输出另在.local/runs内。
    for name in ('content/daily/2026-09-16.show.html','content/assets/model328-2026-10-18/report-data.json',
                 'scripts/rawbank_explorer.html','scripts/szse683_report.html','scripts/rawbank_report_view.js',
                 'scripts/rawbank_file_downloads.js','scripts/szse683_context.js','scripts/sse683_comparison.js'):
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    source=tmp_path/'input';source.mkdir()
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
        if path.suffix=='.gz':raw=gzip.compress(raw,mtime=0)
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()
    datasets=[]
    for segment in ('full','base'):
        for h in builder.HORIZONS:
            key=segment+'-'+h
            data=dict(dates=baseline['dates'][:10],periods=[dict(id='full')],factors=factors,segment=segment,horizon=h,
                label_alignment=[dict(rows=1000,valid_labels=950)],label_contract={'schema':'test'},statistics_schema=[])
            sha=write(source/key/'summary.json.gz',data)
            datasets.append(dict(id=key,dates=10,stock_days=1000,valid_label_stock_days=950,summary_sha256=sha))
    bundles=[]
    for h in builder.HORIZONS:
        for j,f in enumerate(factors):
            path=f'bundles/{h}/factors/{j:03}.json.gz'
            packet=dict(schema='rawbank-segmented-factor-v1',metadata=f['metadata'],daily_ic=[None]*10,distribution=f['distribution'],
                periods=f['periods'],segments={s:dict(distribution=f['distribution'],period_indexes=[0],slice=[0,10]) for s in ('full','base')})
            bundles.append(dict(path=path,sha256=write(source/path,packet)))
    proof=dict(passed=True,trial=True,exchange='XSHG',dates=10,columns=340,stock_days=1000,collection_sha256='a'*64,
        feature_manifest_sha256='1675c3fcf6c19dd53a4d19b67a2c7e4b67704fcb543e29f964faa246fcb443be',
        datasets=datasets,group_mean_checks=102000,density_count_checks=2040,code_revision='fixture',independent_daily_ic_checks={h:10 for h in builder.HORIZONS})
    sha=write(source/'evaluation-result.json',proof)
    write(source/'consumer-acceptance.json',dict(passed=True,kind='evaluation',guard_exit_code=0,scope_absent=True,source_document_sha256=sha,native_objects_verified=0))
    write(source/'EXPORT_FORMAT.json',dict(schema='szse683-atlas-normalized-export-v1',bundles=bundles))
    write(source/'factor-overlap.json',dict(columns=[f['metadata']['factor_id'] for f in factors],segments={s:dict(mean=[[None]*340 for _ in factors]) for s in ('full','base')}))
    output=tmp_path/'.local/runs/test'
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    monkeypatch.setattr(sys,'argv',['build','--input',str(source),'--exchange','XSHG','--collection-sha256','a'*64,'--date','2026-11-04','--trial','--output-root',str(output),'--html-relative-path','2026-11.04.show/.html'])
    builder.main()
    page=(output/'content/daily/2026-11.04.show/.html').read_text(encoding='utf-8')
    assert '10日试运行' in page and 'value="increment"' not in page
    assert '三个周期均覆盖10日' in page
    assert '../../assets/sse683-2026-11-04/' in page
    assert "'../../assets/'" in page
    assets=output/'content/assets/sse683-2026-11-04'
    assert len(list(assets.glob('*/factors/*.js')))==1020
    assert len(list(assets.glob('*/summary.js')))==6
    assert not (output/'content/daily/2026-11-04.md').exists()
