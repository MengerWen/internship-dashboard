"""Evaluate frozen raw-bank daily shards against accepted same-day labels."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib, io, json, os, sys, time, zipfile, gzip
from pathlib import Path
ROOT=Path('/home/wenjie/src/sirui-quant-research')
WORK=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'因子/algobench/src'),str(ROOT/'scripts')]
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import subprocess
from evaluate_open5m_raw_bank import factor_metadata
from algobench.formal_raw_bank_evaluation import quantile_groups,shape_bins,mean_uncertainty
from algobench.interday_count_comparison import daily_cross_sectional_ics
from algobench.depth_match_evaluation import periods, centered_corr
from algobench.depth_match_run import json_safe

registry,formal=factor_metadata()
meta={r['factor_id']:r for r in formal}
metadata=[meta.get(r['factor_id'],{**dict(r),'domain':[0.,1.]}) for r in registry.manifest]
COLUMNS=[r['factor_id'] for r in metadata]
LABEL=registry.return_column
identities=json.loads((WORK/'daily_artifact_identities.json').read_bytes())
inventory=json.loads((WORK/'label_inventory.json').read_bytes())
labels={r['date']:r for r in inventory['days']}
def write_json(path,data):path.write_text(json.dumps(json_safe(data),ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def day_evaluate(entry):
    day=entry['date']
    key='quota/wenjie/'+entry['panel']['path'].split('/home/wenjie/hdd-store/',1)[1]
    raw=subprocess.check_output(['mc','cat',key],timeout=120)
    assert hashlib.sha256(raw).hexdigest()==entry['panel']['file_sha256'],day
    panel=pq.read_table(io.BytesIO(raw)).to_pandas()
    label_raw=(WORK/labels[day]['target_path']).read_bytes()
    assert hashlib.sha256(label_raw).hexdigest()==labels[day]['source_hash'],day
    label=pq.read_table(io.BytesIO(label_raw)).to_pandas()
    for frame in (panel,label):
        frame['date']=frame['date'].astype(str)
        frame['code']=frame['code'].astype(str).str.zfill(6)
        assert not frame.duplicated(['date','code']).any()
    merged=panel[['date','code',*COLUMNS]].merge(label[['date','code',LABEL]],on=['date','code'],how='outer',validate='one_to_one',indicator=True)
    assert merged['_merge'].eq('both').all(),day
    assert len(merged)==entry['rows']
    y=merged[LABEL].to_numpy(float)
    m=pd.DataFrame([dict(formal_column=c,record_id=c,short_alias=c,aggregation='count') for c in COLUMNS])
    ic=daily_cross_sectional_ics(merged[['date','code',*COLUMNS]],merged[['date','code',LABEL]],m,min_names=30,label_columns=[LABEL]).set_index('formal_column')
    results={}
    for record in metadata:
        c=record['factor_id'];x=merged[c].to_numpy(float);finite=np.isfinite(x);pair=finite&np.isfinite(y)
        xx=x[pair];yy=y[pair];n=len(xx)
        health=[len(x),int(finite.sum()),int(np.sum(finite&(x==0))),n,int(len(np.unique(xx)))]
        row=ic.loc[c];ics=[float(row.pearson_ic),float(row.rank_ic)]
        group=[];spreads=[]
        excess=yy-yy.mean() if n else yy
        for k in (10,40):
            ids=quantile_groups(xx,k) if n else np.empty(0,int)
            counts=np.bincount(ids,minlength=k)
            sums=np.bincount(ids,weights=yy,minlength=k)
            esums=np.bincount(ids,weights=excess,minlength=k)
            returns=np.divide(sums,counts,out=np.full(k,np.nan),where=counts>0)
            ereturns=np.divide(esums,counts,out=np.full(k,np.nan),where=counts>0)
            assert counts.sum()==n
            group.extend(np.stack([counts,returns,ereturns],axis=1).tolist())
            spreads.append(returns[-1]-returns[0])
        pct=pd.Series(xx).rank(method='average',pct=True).to_numpy()
        spreads.append(float(yy[pct>.8].mean()-yy[pct<=.2].mean()) if np.any(pct>.8) and np.any(pct<=.2) else np.nan)
        ids,edges=shape_bins(x,record['domain']);counts=np.bincount(ids[ids>=0],minlength=100)
        pi=ids[pair];valid=pi>=0
        pn=np.bincount(pi[valid],minlength=100)
        ps=np.bincount(pi[valid],weights=yy[valid],minlength=100)
        pe=np.bincount(pi[valid],weights=excess[valid],minlength=100)
        bins=np.stack([counts,pn,np.divide(ps,pn,out=np.full(100,np.nan),where=pn>0),np.divide(pe,pn,out=np.full(100,np.nan),where=pn>0)],axis=1)
        under=int(np.sum(finite&(x<record['domain'][0])));over=int(np.sum(finite&(x>record['domain'][1])))
        assert counts.sum()+under+over+(~finite).sum()==len(x)
        results[c]=dict(ic=ics,health=health,groups=group,spreads=spreads,bins=bins,under=under,over=over)
    output=WORK/'days'/f'{day}.npz'
    np.savez_compressed(output,ic=np.array([results[c]['ic'] for c in COLUMNS]),health=np.array([results[c]['health'] for c in COLUMNS]),groups=np.array([results[c]['groups'] for c in COLUMNS]),spreads=np.array([results[c]['spreads'] for c in COLUMNS]),bins=np.array([results[c]['bins'] for c in COLUMNS]),under=np.array([results[c]['under'] for c in COLUMNS]),over=np.array([results[c]['over'] for c in COLUMNS]))
    # One varying factor per day confirms the existing IC routine against numpy/pandas ranks.
    checks=0
    for c in COLUMNS:
        x=merged[c].to_numpy(float);mask=np.isfinite(x)&np.isfinite(y)
        if mask.sum()>=30 and np.ptp(x[mask])>0 and np.ptp(y[mask])>0:
            independent=[centered_corr(x[mask],y[mask]),centered_corr(pd.Series(x[mask]).rank().to_numpy(),pd.Series(y[mask]).rank().to_numpy())]
            np.testing.assert_allclose(results[c]['ic'],independent,atol=1e-12,rtol=1e-10);checks=1;break
    return dict(date=day,rows=len(merged),valid_labels=int(np.isfinite(y).sum()),checks=checks)

def statistics(values):
    r=mean_uncertainty(values,nw_lag=1)
    a=np.asarray(values,float);a=a[np.isfinite(a)];std=float(a.std(ddof=1)) if len(a)>1 else np.nan
    nw=r['newey_west_standard_error'];mean=r['mean']
    return [mean,r['standard_error'],nw,mean/nw if nw>0 else np.nan,len(a),mean/std if std>0 else np.nan,float(np.mean(a>0)) if len(a) else np.nan]

def main():
    start=time.monotonic();(WORK/'days').mkdir(exist_ok=True);(WORK/'factors').mkdir(exist_ok=True)
    receipt=json.loads((WORK/'_IMPORT_VERIFIED.json').read_bytes())
    assert receipt['passed'] and hashlib.sha256((WORK/'labels.zip').read_bytes()).hexdigest()==receipt['zip_sha256']
    with zipfile.ZipFile(WORK/'labels.zip') as archive:archive.extractall(WORK)
    assert len(identities)==len(labels)==601
    assert sorted(labels)==[r['date'] for r in identities]
    alignment=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(day_evaluate,e) for e in identities]
        for future in as_completed(futures):
            alignment.append(future.result())
            write_json(WORK/'progress.json',dict(phase='daily_evaluation',completed=len(alignment),total=601,elapsed=time.monotonic()-start))
            if len(alignment)%25==0:print('days',len(alignment),round(time.monotonic()-start,1),flush=True)
    dates=[r['date'] for r in identities];alignment.sort(key=lambda r:r['date']);write_json(WORK/'label_alignment.json',alignment)
    data=[dict(np.load(WORK/'days'/f'{d}.npz')) for d in dates]
    period_list=periods();masks=[np.array([a<=d<=b for d in dates]) for _,a,b in period_list]
    aggregate=[]
    for i,record in enumerate(metadata):
        daily=np.array([d['ic'][i] for d in data]);health=np.array([d['health'][i] for d in data]);groups=np.array([d['groups'][i] for d in data]);spread=np.array([d['spreads'][i] for d in data]);bins=np.array([d['bins'][i] for d in data])
        summaries=[]
        for mask in masks:
            summaries.append(dict(ic=[statistics(daily[mask,j]) for j in range(2)],spread=[statistics(spread[mask,j]) for j in range(3)],groups=[[statistics(groups[mask,g,j]) for j in (1,2)] for g in range(50)]))
        distribution=dict(rows=int(health[:,0].sum()),finite=int(health[:,1].sum()),zero=int(health[:,2].sum()),pairs=int(health[:,3].sum()),constant_days=int(np.sum(health[:,4]<=1)),under=sum(int(d['under'][i]) for d in data),over=sum(int(d['over'][i]) for d in data))
        shape=[dict(count=int(bins[:,b,0].sum()),paired_count=int(bins[:,b,1].sum()),raw=statistics(bins[:,b,2]),excess=statistics(bins[:,b,3])) for b in range(100)]
        result=dict(metadata=record,diagnostic=record['factor_id'] in registry.diagnostic_factor_ids,distribution=distribution,daily_ic=daily.tolist(),daily_health=health.tolist(),daily_spread=spread.tolist(),periods=summaries,shape=shape)
        write_json(WORK/'factors'/f'{record["factor_id"]}.json',result)
        aggregate.append(result)
        write_json(WORK/'progress.json',dict(phase='summaries',completed=i+1,total=288,elapsed=time.monotonic()-start))
    report=dict(dates=dates,periods=[dict(id=p,start=a,end=b) for p,a,b in period_list],statistics_schema=['mean','ordinary_se','nw_se_lag1','nw_t','valid_days','icir','positive_fraction'],factors=aggregate,label=LABEL,label_contract=inventory['contract'])
    with gzip.open(WORK/'report-data.json.gz','wt',encoding='utf-8',compresslevel=9) as stream:json.dump(json_safe(report),stream,ensure_ascii=False,separators=(',',':'))
    write_json(WORK/'evaluation_result.json',dict(passed=True,dates=601,formal_columns=284,diagnostic_columns=4,stock_days=sum(r['rows'] for r in alignment),valid_label_stock_days=sum(r['valid_labels'] for r in alignment),independent_daily_checks=sum(r['checks'] for r in alignment),factor_registry_sha256=hashlib.sha256((ROOT/'PLAN/factor_preregister_intraday_open5m_raw_bank_v5.yaml').read_bytes()).hexdigest(),label_spec_hash=inventory['label_spec_hash'],elapsed_seconds=time.monotonic()-start,method='Existing daily_cross_sectional_ics, average-rank quantile_groups and Bartlett lag-1 mean_uncertainty; daily-equal returns; 10/40 groups; fixed-domain 100 bins',report_sha256=hashlib.sha256((WORK/'report-data.json.gz').read_bytes()).hexdigest()))
    write_json(WORK/'progress.json',dict(phase='complete',completed=288,total=288,elapsed=time.monotonic()-start))
    print('COMPLETE',round(time.monotonic()-start,1),flush=True)
if __name__=='__main__':main()
