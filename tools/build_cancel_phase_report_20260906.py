"""Build the offline cancellation-phase report from hash-verified stock-day panels.

Raw inputs live under ignored data/. The compact JSON and generated figures are
committed so the HTML can also be rebuilt with --render-only, without SSH.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/cancel-phase-2026-09-06'
RAW = ROOT / 'data/cancel-phase-2026-09-06/raw'
LABEL = 'ret_intraday_vwap_0944_0945_from_d1_0935_last'
FULL = '2024-2026Q2'
TEAL, RUST, INK = '#087b78', '#b24f35', '#243648'
FAMILY_NAMES = ['事件对集中度', '跨周期一致性', '跨周期交叉拟合偏离', '全委托归一能量',
                '跨订单集中度', '尖峰能量', '跨订单尖峰能量']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def nw_t(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    e = x - x.mean()
    # Bartlett weight at lag 1 is 1/2: gamma0 + 2*(1/2)*gamma1.
    variance = (np.dot(e, e) + np.dot(e[1:], e[:-1])) / len(x)
    return x.mean() / np.sqrt(variance / len(x)) if variance > 0 else np.nan


def daily_deciles(x, y):
    pairs = pd.DataFrame({'x': x, 'y': y}).replace([np.inf, -np.inf], np.nan).dropna()
    means, counts = np.full(10, np.nan), np.zeros(10, dtype=int)
    if len(pairs) >= 30:
        ranks = pairs.x.rank(method='average', pct=True)
        groups = np.ceil(ranks.to_numpy() * 10).astype(int) - 1
        for g in range(10):
            ys = pairs.y.to_numpy()[groups == g]
            counts[g] = len(ys)
            if len(ys):
                means[g] = ys.mean()
    return means, counts


def configure_plots():
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        from matplotlib import font_manager
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.edgecolor': '#b7c1bf', 'text.color': INK, 'axes.labelcolor': INK,
                         'xtick.color': INK, 'ytick.color': INK, 'axes.unicode_minus': False,
                         'figure.facecolor': '#ffffff', 'axes.facecolor': '#ffffff',
                         'savefig.facecolor': '#ffffff'})


def save_fig(fig, name):
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=140, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert('RGB').save(ASSETS / f'{name}.webp', quality=86, method=6)
    return name


def extract():
    manifest = json.loads((RAW / 'input-manifest.json').read_text())
    for f in manifest['files']:
        assert digest(RAW / f['path']) == f['sha256'], f['path']
    print('Input hashes verified', flush=True)
    ev = RAW / 'evaluation'
    summary = pd.read_parquet(ev / 'period_summary.parquet')
    daily = pd.read_parquet(ev / 'daily_ic.parquet')
    spreads = pd.read_parquet(ev / 'decile_spread.parquet').set_index(['date', 'formal_column'])
    corr = pd.read_parquet(ev / 'correlation.parquet').set_index('formal_column')
    columns = corr.columns.tolist()
    alignment = pd.read_parquet(ev / 'label_alignment.parquet')
    dates = sorted(daily.date.unique())
    assert len(dates) == 601 and len(columns) == 24 and len(daily) == 14424
    assert not daily.duplicated(['date', 'formal_column']).any()
    frames = []
    for date in dates:
        f = pd.read_parquet(RAW / f'panel/days/{date}/factors.parquet')
        lp = RAW / f'labels/intraday_labels/intraday_vwap_0944_0945_from_0935_v1/shards/date={date}.parquet'
        lab = pd.read_parquet(lp)
        assert not f.duplicated(['date', 'code']).any()
        assert not lab.duplicated(['date', 'code']).any()
        m = f[['date', 'code'] + columns].merge(lab[['date', 'code', LABEL]],
                                               on=['date', 'code'], how='outer', validate='one_to_one', indicator=True)
        assert m['_merge'].eq('both').all(), date
        valid = lab[['price_d1_0935_last_raw', 'price_d1_vwap_0944_0945_raw', LABEL]].dropna()
        assert np.allclose(valid.iloc[:, 1] / valid.iloc[:, 0] - 1, valid[LABEL], atol=1e-14, rtol=1e-12)
        frames.append(m.drop(columns='_merge'))
    panel = pd.concat(frames, ignore_index=True)
    del frames
    assert len(panel) == 1719612 and panel[LABEL].notna().sum() == 1710977
    periods = summary[['period', 'period_start', 'period_end']].drop_duplicates().to_dict('records')
    byday = {str(d): g for d, g in panel.groupby('date', sort=True)}
    factors, comparison, max_error = [], [], 0.0
    for index, column in enumerate(columns):
        fid = f'F{index+1:02d}'
        family = int(column[3:5])
        period = int(re.search(r'__period_(\d+)ms', column)[1])
        kernel = re.search(r'__kernel_(.*?)__den_', column)[1]
        alias = f'{fid} · {FAMILY_NAMES[family-1]} · T{period} / ' + ('20−50' if kernel.startswith('sharp') else kernel.removeprefix('heat_').removesuffix('ms'))
        means, counts, finite_counts, zero_counts, row_counts = [], [], [], [], []
        for date in dates:
            day = byday[date]
            values = day[column].to_numpy()
            finite_counts.append(int(np.isfinite(values).sum()))
            zero_counts.append(int((values == 0).sum()))
            row_counts.append(len(day))
            mu, n = daily_deciles(day[column], day[LABEL])
            expected = spreads.loc[(date, column)]
            difference = mu[9] - mu[0]
            if np.isfinite(difference):
                max_error = max(max_error, abs(difference - expected.top_minus_bottom_gross))
                assert np.isclose(difference, expected.top_minus_bottom_gross, atol=1e-12, rtol=0)
                assert n[0] == expected.bottom_count and n[9] == expected.top_count
            else:
                assert pd.isna(expected.top_minus_bottom_gross)
            means.append(mu); counts.append(n)
        means, counts = np.array(means), np.array(counts)
        finite_counts, zero_counts, row_counts = map(np.array, (finite_counts, zero_counts, row_counts))
        ds = daily[daily.formal_column.eq(column)].set_index('date').loc[dates]
        stats = {}
        for p in periods:
            mask = (np.array(dates) >= p['period_start']) & (np.array(dates) <= p['period_end'])
            record = summary[summary.formal_column.eq(column) & summary.period.eq(p['period'])].iloc[0]
            spread = means[mask, 9] - means[mask, 0]
            assert np.isclose(nw_t(ds.rank_ic.to_numpy()[mask]), record.t_nw_lag1, atol=1e-10, rtol=1e-10)
            stats[p['period']] = {
                'ic': record.IC, 'rank': record.Rank_IC, 'icir': record.ICIR,
                't': record.t_nw_lag1, 'days': int(record.n_days), 'paired': int(record.sample_count),
                'factor_count': int(record.factor_observations), 'rows': int(row_counts[mask].sum()),
                'finite': int(finite_counts[mask].sum()), 'zeros': int(zero_counts[mask].sum()),
                'groups_bps': np.nanmean(means[mask], axis=0)*10000,
                'group_days': np.isfinite(means[mask]).sum(axis=0),
                'group_counts': counts[mask].sum(axis=0),
                'spread_bps': np.nanmean(spread)*10000, 'spread_t_nw': nw_t(spread),
            }
        finite = panel[column].to_numpy(); finite = finite[np.isfinite(finite)]
        q = np.quantile(finite, [0, .005, .01, .25, .5, .75, .99, .995, 1])
        fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        xdates = pd.to_datetime(dates); r = ds.rank_ic.to_numpy()
        axes[0].plot(xdates, r, lw=.65, color='#a7c9c4', label='每日 Rank IC')
        axes[0].plot(xdates, pd.Series(r).rolling(20, min_periods=10).mean(), lw=1.3, color=TEAL, label='20 日均值（至少 10 日）')
        axes[0].axhline(0, color=INK, lw=.5); axes[0].legend(loc='upper right', ncol=2, fontsize=9)
        axes[0].set_ylabel('Rank IC'); axes[0].set_title(f'{fid} · 每日横截面相关 · 全部 601 日', loc='left')
        axes[1].plot(xdates, np.nancumsum(r), color=TEAL, lw=1.3)
        axes[1].axhline(0, color=INK, lw=.5); axes[1].set_ylabel('累计 Rank IC')
        axes[1].set_xlabel('交易日期 · 累计 IC 为相关系数之和，不是资金净值')
        fig.tight_layout(); save_fig(fig, fid+'-daily')
        monthly = ds.groupby(ds.index.str[:7]).rank_ic.mean()
        fig, ax = plt.subplots(figsize=(10, 3.6)); ax.bar(np.arange(len(monthly)), monthly, color=[TEAL if a>=0 else RUST for a in monthly])
        ax.axhline(0,color=INK,lw=.6); ax.set_xticks(np.arange(len(monthly))[::2], monthly.index[::2], rotation=35, ha='right')
        ax.set_ylabel('月内日均 Rank IC'); ax.set_title(f'{fid} · 30 个月的方向与强度',loc='left')
        fig.tight_layout(); save_fig(fig, fid+'-monthly')
        fig, ax = plt.subplots(figsize=(10, 3.6))
        ax.hist(finite[(finite >= q[1]) & (finite <= q[-2])], bins=60, color=TEAL, alpha=.85)
        ax.set_ylabel('股票日数'); ax.set_xlabel('因子原值 · 横轴只展示 P0.5—P99.5，尾部数单列')
        ax.set_title(f'{fid} · 全区间分布；未把负数截为零', loc='left'); fig.tight_layout()
        save_fig(fig, fid+'-distribution')
        factors.append({'id': fid, 'column': column, 'family': family, 'period': period, 'kernel': kernel,
                        'alias': alias, 'stats': stats, 'quantiles': q,
                        'left_tail': int((finite < q[1]).sum()), 'right_tail': int((finite > q[-2]).sum()),
                        'daily_rank': r, 'daily_n': ds.n.to_numpy()})
        print(f'Aggregated and plotted {fid}/F24', flush=True)
    for left, right in [(0, 16), (1, 17), (2, 18), (3, 19), (20, 22), (21, 23)]:
        a, b = panel[columns[left]].to_numpy(), panel[columns[right]].to_numpy()
        ok = np.isfinite(a) & np.isfinite(b); delta = np.abs(a[ok]-b[ok])
        comparison.append({'a': factors[left]['id'], 'b': factors[right]['id'], 'n': int(ok.sum()),
                           'exact_equal': int((delta == 0).sum()), 'max_abs_diff': delta.max(),
                           'mean_abs_diff': delta.mean(), 'pearson': np.corrcoef(a[ok], b[ok])[0,1]})
    print('Building cross-factor figures', flush=True)
    selected_periods = ['2024','2025','2026H1'] + sorted(p['period'] for p in periods if re.fullmatch(r'202[456]Q[1-4]',p['period']))
    matrix = np.array([[f['stats'][p]['rank'] for p in selected_periods] for f in factors])
    fig, ax = plt.subplots(figsize=(12, 10)); lim=np.nanmax(abs(matrix)); im=ax.imshow(matrix, aspect='auto', cmap='RdBu_r',vmin=-lim,vmax=lim)
    ax.set_xticks(range(len(selected_periods)),selected_periods,rotation=40,ha='right')
    ax.set_yticks(range(24),[f['id'] for f in factors])
    for row in range(24):
        for col in range(len(selected_periods)):
            ax.text(col,row,f'{matrix[row,col]:.3f}',ha='center',va='center',fontsize=8,color='white' if abs(matrix[row,col])>.65*lim else INK)
    ax.set_title('日均 Rank IC：年份 / 半年与季度 · 原始方向，统一色阶',loc='left',pad=14)
    fig.colorbar(im,ax=ax,shrink=.6,label='日均 Rank IC'); fig.tight_layout(); save_fig(fig,'period-heatmap')
    fig,ax=plt.subplots(figsize=(10,8)); im=ax.imshow(corr.to_numpy(),vmin=-1,vmax=1,cmap='RdBu_r')
    ax.set_xticks(range(24),[f['id'] for f in factors],rotation=90,fontsize=8)
    ax.set_yticks(range(24),[f['id'] for f in factors],fontsize=8)
    ax.set_title('因子值 Pearson 相关 · 汇集股票日，逐对有效样本',loc='left',pad=14)
    fig.colorbar(im,ax=ax,shrink=.7); fig.tight_layout();save_fig(fig,'correlation')
    fig,axes=plt.subplots(1,2,figsize=(12,9),sharey=True)
    for i,f in enumerate(factors):
        s=f['stats'][FULL]; se=abs(s['rank']/s['t']) if s['t'] else 0
        axes[0].errorbar(s['rank'],i,xerr=1.96*se,fmt='o',ms=4,color=TEAL,capsize=2)
        axes[1].barh(i,s['spread_bps'],color=TEAL if s['spread_bps']>=0 else RUST)
    for ax in axes: ax.axvline(0,color=INK,lw=.7);ax.grid(axis='x',alpha=.12)
    axes[0].set_yticks(range(24),[f['id'] for f in factors]);axes[0].invert_yaxis()
    axes[0].set_title('日均 Rank IC ± 1.96 × NW 标准误');axes[0].set_xlabel('描述性区间 · lag 1 · 未校正多重比较')
    axes[1].set_title('日均 G10 − G1 毛收益');axes[1].set_xlabel('基点（bp） · 保持因子原始方向')
    fig.tight_layout();save_fig(fig,'overview')
    pre_path=ROOT/'content/daily/2026-08-24.show.html'
    pre=json.loads(re.search(r'<script type="application/json" id="visual-data">(.*?)</script>',pre_path.read_text(encoding='utf-8'),re.S)[1])
    h=np.array(pre['heatmap']['counts'],dtype=float)[:,:200]
    cancel_counts=np.array([d['cancel_count'] for d in pre['daily']])
    assert pre['heatmap']['dates']==[d['date'] for d in pre['daily']]
    normalized=h/cancel_counts[:,None]*1e6
    pdts=np.array(pre['heatmap']['dates'])
    fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True,sharey=True)
    for ax,(p,color) in zip(axes,zip(['2024','2025','2026H1'],[INK,TEAL,RUST])):
        mask=np.char.startswith(pdts,p[:4]);y=normalized[mask].mean(axis=0)
        ax.bar(np.arange(200)*.05,y,width=.045,color=color)
        ax.text(.985,.8,f'{p} · {mask.sum()} 日',transform=ax.transAxes,ha='right',color=color)
        ax.set_ylabel('每百万撤单');ax.grid(axis='y',alpha=.12)
    axes[0].set_title('预检：每日先除以全部匹配撤单数，再对交易日等权平均',loc='left',pad=12)
    axes[-1].set_xlabel('撤单等待时间（秒） · 50ms 分箱，展示 [0,10s)');fig.tight_layout();save_fig(fig,'inspiration-periods')
    fig,ax=plt.subplots(figsize=(12,4.8));im=ax.imshow(normalized.T,origin='lower',aspect='auto',extent=[0,601,0,10],norm=LogNorm(vmin=max(normalized[normalized>0].min(),1),vmax=normalized.max()),cmap='viridis')
    ax.axvline(242,color='white',lw=.7);ax.axvline(485,color='white',lw=.7)
    ax.set_xticks([0,242,485,600],['2024-01-02','2025-01-02','2026-01-05','2026-06-30'])
    ax.set_ylabel('撤单等待时间（秒）');ax.set_title('预检：601 日时间差分布 · 50ms 分箱，统一对数色阶',loc='left')
    fig.colorbar(im,ax=ax,label='每百万匹配撤单');fig.tight_layout();save_fig(fig,'inspiration-heatmap')
    fig,axes=plt.subplots(2,1,figsize=(12,5),sharex=True)
    months=pre['months']; xx=np.arange(len(months))
    axes[0].plot(xx,[m['quantiles_ms']['0.5']/1000 for m in months],color=TEAL,marker='o',ms=3)
    axes[0].set_ylabel('中位数（秒）');axes[0].set_title('预检：等待时间中位数与 5.5—6.5 秒频带的月度变化',loc='left')
    axes[1].plot(xx,[m['share_5_5_6_5s']*100 for m in months],color=RUST,marker='o',ms=3)
    axes[1].set_ylabel('频带占比（%）');axes[1].set_xticks(xx[::2],[m['month'] for m in months][::2],rotation=35,ha='right')
    fig.tight_layout();save_fig(fig,'inspiration-months')
    payload={'schema':1,'dates':dates,'periods':periods,'factors':factors,'comparisons':comparison,
             'redundancy':json.loads((ev/'redundancy.json').read_text()),
             'precheck':{'study':pre['study'],'quality':pre['quality'],
                         'periods':{k:{x:v[x] for x in ['cancel_count','date_count','mode_ms','quantiles_ms','share_5_5_6_5s']} for k,v in pre['periods'].items()}},
             'audit':{'verified_input_files':len(manifest['files']),'result_sha256':manifest['result_sha256'],
                      'precheck_sha256':digest(pre_path),'run_root':manifest['run_root'],
                      'business_revision':manifest['business_revision'],'evaluation_revision':manifest['evaluation_revision'],
                      'max_decile_spread_abs_error':max_error,'rows':len(panel),
                      'valid_labels':int(panel[LABEL].notna().sum()),'alignment_missing_keys':int(alignment.missing_keys.sum()),
                      'alignment_duplicate_keys':int(alignment.duplicate_keys.sum()),'group_checks':601*24}}
    (ASSETS/'report.json').write_text(json.dumps(clean(payload),ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    (ASSETS/'input-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return payload


def render():
    from PIL import Image
    raw=(ASSETS/'report.json').read_text(encoding='utf-8')
    template=(ROOT/'tools/templates/cancel-phase-20260906.html').read_text(encoding='utf-8')
    # Intrinsic dimensions reserve layout space before lazy images decode.
    def dimensions(match):
        tag = match.group(0)
        name = re.search(r'data-plot="([^"]+)"', tag)
        detail = re.search(r'id="detail-(daily|monthly|distribution)"', tag)
        stem = name[1] if name else ('F01-' + detail[1] if detail else None)
        if stem:
            with Image.open(ASSETS / (stem + '.webp')) as picture:
                width, height = picture.size
            tag = tag[:-1] + f' width="{width}" height="{height}">'
        return tag
    template = re.sub(r'<img\b[^>]*>', dimensions, template)
    figures={p.stem:base64.b64encode(p.read_bytes()).decode() for p in sorted(ASSETS.glob('*.webp'))}
    html=template.replace('__REPORT_DATA__',raw.replace('</','<\\/')).replace('__FIGURE_DATA__',json.dumps(figures))
    assert '__REPORT_DATA__' not in html and '__FIGURE_DATA__' not in html
    (ROOT/'content/daily/2026-09-06.html').write_text(html,encoding='utf-8')
    # The site discovers .show.html companions; figures remain external there.
    web=template.replace('__REPORT_DATA__',raw.replace('</','<\\/')).replace('__FIGURE_DATA__','{}')
    web=web.replace('data-offline="true"','data-offline="false"')
    (ROOT/'content/daily/2026-09-06.show.html').write_text(web,encoding='utf-8')
    print(f'Wrote offline HTML: {len(html.encode()):,} bytes; web HTML: {len(web.encode()):,} bytes')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--render-only',action='store_true');args=parser.parse_args()
    ASSETS.mkdir(parents=True,exist_ok=True)
    if not args.render_only:
        configure_plots();extract()
    render()
