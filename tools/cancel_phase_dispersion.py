"""按交易日分解组内离散程度，并估计组均值的时间序列标准误。"""
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from cancel_phase_diagnostics import average_ranks


def nw_mean_se(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    e = x - x.mean()
    return float(np.sqrt(max(0, (np.dot(e, e) + np.dot(e[1:], e[:-1])) / len(x)**2)))


def daily_group_dispersion(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    group = np.ceil(average_ranks(x) / len(x) * 10).astype(int) - 1
    means, variances = np.full(10, np.nan), np.full(10, np.nan)
    counts = np.bincount(group, minlength=10)
    for g in range(10):
        values = y[group == g]
        if len(values):
            means[g], variances[g] = values.mean(), values.var(ddof=0)
    weights = counts / len(y)
    within = float(np.nansum(weights * variances))
    between = float(np.nansum(weights * (means-y.mean())**2))
    total = float(y.var(ddof=0))
    assert np.isclose(within+between,total,rtol=1e-10,atol=1e-15)
    return means, variances, within, between, total


def enrich_report(raw, assets, save_fig, *, label_raw=None):
    label_raw = raw if label_raw is None else label_raw
    report_path = assets/'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    manifest = json.loads((raw/'input-manifest.json').read_text())
    for item in manifest['files']:
        assert hashlib.sha256((raw/item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
    dates = np.array(report['dates'])
    columns = [f['column'] for f in report['factors']]
    label = 'ret_intraday_vwap_0944_0945_from_d1_0935_last'
    means, variances = np.full((24,601,10),np.nan),np.full((24,601,10),np.nan)
    variance_parts = np.full((24,601,3),np.nan)
    for day_index,date in enumerate(dates):
        panel = pd.read_parquet(raw/f'panel/days/{date}/factors.parquet')
        labels = pd.read_parquet(label_raw/f'labels/intraday_labels/intraday_vwap_0944_0945_from_0935_v1/shards/date={date}.parquet')
        merged = panel.merge(labels[['date','code',label]],on=['date','code'],how='outer',validate='one_to_one',indicator=True)
        assert merged['_merge'].eq('both').all()
        y = merged[label].to_numpy()
        for index,column in enumerate(columns):
            mu,var,within,between,total = daily_group_dispersion(merged[column].to_numpy(),y)
            means[index,day_index],variances[index,day_index] = mu,var
            variance_parts[index,day_index] = within,between,total
        if day_index % 100 == 0:
            print(f'分组离散度已核算 {day_index+1}/601 日',flush=True)
    for index,f in enumerate(report['factors']):
        for p in report['periods']:
            mask = (dates>=p['period_start']) & (dates<=p['period_end'])
            daily_means = means[index,mask]
            mean = np.nanmean(daily_means,axis=0)*10000
            std = np.sqrt(np.nanmean(variances[index,mask],axis=0))*10000
            se = np.array([nw_mean_se(daily_means[:,g]) for g in range(10)])*10000
            parts = variance_parts[index,mask]
            fraction = np.mean(parts[:,0]/parts[:,2])
            spread = daily_means[:,9]-daily_means[:,0]
            stats = f['stats'][p['period']]
            np.testing.assert_allclose(mean, stats['groups_bps'],atol=1e-10,rtol=0)
            np.testing.assert_array_equal(np.isfinite(daily_means).sum(axis=0), stats['group_days'])
            dispersion = dict(within_sd_bps=std.tolist(), nw_se_bps=se.tolist(),
                              ci95_low_bps=(mean-1.96*se).tolist(),ci95_high_bps=(mean+1.96*se).tolist(),
                              within_variance_fraction=float(fraction),between_variance_fraction=float(1-fraction),
                              spread_nw_se_bps=nw_mean_se(spread)*10000)
            assert np.isclose(stats['spread_bps']/dispersion['spread_nw_se_bps'],stats['spread_t_nw'],rtol=1e-10,atol=1e-10)
            stats['dispersion'] = dispersion
        s=f['stats']['2024-2026Q2'];d=s['dispersion'];x=np.arange(1,11);mu=np.array(s['groups_bps'])
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        for ax,error,title,color in zip(axes,[d['within_sd_bps'],np.array(d['nw_se_bps'])*1.96],
                ['组内股票收益：均值 ± 典型日内标准差','组均值估计：95% NW 描述性区间'],['#087b78','#b24f35']):
            ax.errorbar(x,mu,yerr=error,fmt='o-',ms=4,capsize=4,lw=1,color=color)
            ax.axhline(0,color='#243648',lw=.6);ax.set_xticks(x,[f'G{g}' for g in x]);ax.set_ylabel('收益（bp）')
            ax.set_title(title,loc='left',fontsize=11);ax.grid(axis='y',alpha=.15)
        fig.suptitle(f'{f["id"]} · 全部 601 日 · 两图纵轴尺度不同',fontsize=12)
        fig.text(.5,.01,'左：每日组内总体方差的平均值开方；右：组日均收益序列，Newey–West lag 1。左图不是置信区间。',ha='center',fontsize=9)
        fig.tight_layout(rect=[0,.04,1,.96]);save_fig(fig,f['id']+'-errorbars')
    report['audit']['dispersion_checks']=14424
    report['audit']['dispersion_contract']='daily population variance decomposition; RMS within-day SD; daily mean NW lag 1 SE; 1.96 normal multiplier'
    report_path.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    print('已核验 14,424 个日度分组，并生成 24 张误差棒图',flush=True)
