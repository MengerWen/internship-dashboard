"""Build the frozen-model research report from existing, read-only run artifacts."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEAL, RUST, BLUE, GRAY = '#087b78', '#b24f35', '#446994', '#78837a'


def sharpe(values):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.sqrt(252) * v.mean() / v.std(ddof=1)) if len(v) > 1 and v.std(ddof=1) else None


def digest(p):
    with p.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def svg_chart(title, series, labels=None, scatter=False, unit='', marker=None):
    """Numeric series use real x coordinates; labels only format date/index ticks."""
    w, h, left, right, top, bottom = 760, 380, 78, 22, 35, 75
    points = [(float(x), float(y)) for s in series for x, y in s['points'] if np.isfinite(y)]
    xs, ys = zip(*points)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(min(ys), 0), max(max(ys), 0)
    if xmax == xmin:
        xmax += 1
    span = ymax - ymin or 1
    ymin -= .08 * span
    ymax += .1 * span
    sx = lambda x: left + (x - xmin) / (xmax - xmin) * (w-left-right)
    sy = lambda y: top + (ymax-y) / (ymax-ymin) * (h-top-bottom)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title><rect width="100%" height="100%" fill="#fff"/>']
    for y in np.linspace(ymin, ymax, 6):
        yp = sy(y)
        parts.append(f'<path d="M{left},{yp:.2f} H{w-right}" stroke="#e1e5dd"/><text x="{left-10}" y="{yp+5:.2f}" text-anchor="end">{y:.3f}</text>')
    parts.append(f'<text x="12" y="20">{html.escape(unit)}</text>')
    ticks = np.linspace(xmin, xmax, 5)
    parts.append(f'<path d="M{left},{sy(0):.2f} H{w-right}" stroke="#9aa89e"/>')
    for ti,x in enumerate(ticks):
        label = labels[min(len(labels)-1, max(0, round(x)))] if labels is not None else f'{x:.3g}'
        anchor='start' if ti==0 else ('end' if ti==len(ticks)-1 else 'middle')
        parts.append(f'<text x="{sx(x):.2f}" y="{h-bottom+28}" text-anchor="{anchor}">{html.escape(str(label))}</text>')
    if marker is not None:
        parts.append(f'<path d="M{sx(marker):.2f},{top} V{h-bottom}" stroke="{RUST}" stroke-dasharray="5 4"/><text x="{sx(marker)+6:.2f}" y="25" fill="{RUST}">659 轮</text>')
    for index, s in enumerate(series):
        pts = [(x, y) for x, y in s['points'] if np.isfinite(y)]
        color = s['color']
        if scatter:
            for x, y in pts:
                parts.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="3.4" fill="{color}" opacity=".62"><title>RankIC {x:.5f}；收益 {y:.3f}bp</title></circle>')
        else:
            d = ' '.join(('M' if i == 0 else 'L') + f'{sx(x):.2f},{sy(y):.2f}' for i, (x,y) in enumerate(pts))
            parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        xp = 80 + index * 205
        parts.append(f'<path d="M{xp},{h-16} h20" stroke="{color}" stroke-width="3"/><text x="{xp+27}" y="{h-11}">{html.escape(s["name"])}</text>')
    return ''.join(parts) + '</svg>'


def bars(title, labels, series, unit='', horizontal=False):
    w = 760
    h = max(380, 48 * len(labels) + 95) if horizontal else 400
    left = 250 if horizontal else 75
    right, top, bottom = 30, 38, 72
    vals = [float(v) for s in series for v in s['values'] if v is not None]
    lo, hi = min(0, min(vals)), max(0, max(vals))
    span = hi-lo or 1
    lo, hi = lo-.06*span, hi+.15*span
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title><rect width="100%" height="100%" fill="#fff"/><text x="15" y="22">{html.escape(unit)}</text>']
    if horizontal:
        scale = lambda v: left + (v-lo)/(hi-lo)*(w-left-right)
        for tick in np.linspace(lo,hi,5):
            xp=scale(tick)
            parts.append(f'<path d="M{xp:.2f},{top} V{h-bottom}" stroke="#e1e5dd"/><text x="{xp:.2f}" y="{h-bottom+26}" text-anchor="middle">{tick:.1f}</text>')
        step=(h-top-bottom)/len(labels)
        for i,label in enumerate(labels):
            y=top+i*step
            parts.append(f'<text x="{left-12}" y="{y+step*.55:.2f}" text-anchor="end">{html.escape(label)}</text>')
            for j,s in enumerate(series):
                v=s['values'][i]
                if v is None: continue
                bh=step*.65/len(series)
                parts.append(f'<rect x="{min(scale(0),scale(v)):.2f}" y="{y+j*bh+4:.2f}" width="{abs(scale(v)-scale(0)):.2f}" height="{bh:.2f}" fill="{s["color"]}"><title>{html.escape(label)}：{v:.5f}</title></rect><text x="{scale(v)+6:.2f}" y="{y+j*bh+bh:.2f}">{v:.2f}</text>')
    else:
        scale=lambda v:top+(hi-v)/(hi-lo)*(h-top-bottom)
        for tick in np.linspace(lo,hi,6):
            yp=scale(tick)
            parts.append(f'<path d="M{left},{yp:.2f} H{w-right}" stroke="#e1e5dd"/><text x="{left-10}" y="{yp+5:.2f}" text-anchor="end">{tick:.1f}</text>')
        parts.append(f'<path d="M{left},{scale(0):.2f} H{w-right}" stroke="#9aa89e"/>')
        step=(w-left-right)/len(labels)
        bw=step*.72/len(series)
        for i,label in enumerate(labels):
            xp=left+(i+.5)*step
            parts.append(f'<text x="{xp:.2f}" y="{h-bottom+25}" text-anchor="middle">{html.escape(str(label))}</text>')
            for j,s in enumerate(series):
                v=s['values'][i]
                if v is None:continue
                bx=xp-step*.36+j*bw
                parts.append(f'<rect x="{bx:.2f}" y="{min(scale(0),scale(v)):.2f}" width="{bw-1:.2f}" height="{max(.5,abs(scale(v)-scale(0))):.2f}" fill="{s["color"]}"><title>{html.escape(s["name"])} / {label}：{v:.5f}</title></rect>')
    for j,s in enumerate(series):
        xp=80+j*215
        parts.append(f'<rect x="{xp}" y="{h-23}" width="16" height="12" fill="{s["color"]}"/><text x="{xp+23}" y="{h-12}">{html.escape(s["name"])}</text>')
    return ''.join(parts)+'</svg>'


def figure(chart_id, title, svg, caption):
    return f'<figure id="{chart_id}"><div class="figure-top"><h3>{title}</h3><button class="enlarge" type="button" aria-label="放大：{title}">放大图表</button></div><div class="chart-scroll">{svg}</div><figcaption>{caption}</figcaption></figure>'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    args=parser.parse_args()
    p=args.input
    load=lambda name:json.loads((p/name).read_text(encoding='utf-8'))
    audit=lambda name:json.loads((args.audit/name).read_text(encoding='utf-8'))
    predictions=pd.read_parquet(p/'test_predictions.parquet')
    saved=pd.read_parquet(p/'test_daily_metrics.parquet').set_index('date')
    curve=pd.read_parquet(p/'per_round_metrics.parquet')
    resources=pd.read_parquet(p/'resource_samples.parquet')
    summary=audit('test_summary.json')
    timing=load('timing_resource_summary.json')
    params=load('effective_parameters.json')
    selection=load('validation_selection_receipt.json')
    dataset=load('dataset_summary.json')
    dist=audit('distribution_audit.json')
    independent=audit('independent_audit_summary.json')
    assert len(predictions)==507460 and not predictions.duplicated(['date','code']).any()
    assert int(curve.loc[curve.long_short_sharpe.idxmax(),'iteration'])==659
    assert digest(p/'per_round_metrics.parquet')==selection['curve_sha256']
    dates,rows,groups=[],[],[]
    for date,full in predictions.groupby('date',sort=True):
        dates.append(date)
        valid=full[np.isfinite(full.raw_return)]
        base=full[full.rank_base].copy()
        n=len(base)
        def leg(q,highest):
            k=math.ceil(q*n)
            threshold=base.score.nlargest(k).iloc[-1] if highest else base.score.nsmallest(k).iloc[-1]
            selected=base[base.score.ge(threshold) if highest else base.score.le(threshold)]
            selected=selected[~selected.no_long] if highest else selected[~selected.no_short]
            values=selected.raw_return.dropna()
            return (float(values.mean()) if len(values) else 0.0),len(values)
        l20,nl20=leg(.2,True);s20,ns20=leg(.2,False)
        l10,nl10=leg(.1,True);s10,ns10=leg(.1,False)
        ls=l10-s10 if nl10 and ns10 else 0.0
        market=float(base.raw_return.mean())
        percentile=base.score.rank(method='average',pct=True)
        base['decile']=np.minimum(10,np.ceil(percentile*10)).astype(int)
        middle=base[(percentile>.2)&(percentile<=.8)].dropna(subset=['raw_return'])
        bottom=base[base.decile==1].dropna(subset=['raw_return'])
        row=dict(date=date,rank_ic=valid.score.corr(valid.raw_return,method='spearman'),pearson_ic=valid.score.corr(valid.raw_return),pure_long_return=l20,pure_short_return=-s20,long_short_return=ls,long10=l10,short10=-s10,market=market,long_excess=l20-market,short_excess=market-s20,rank_base_count=n,long10_count=nl10,short10_count=ns10,middle_ic=middle.score.corr(middle.raw_return,method='spearman'),bottom_ic=bottom.score.corr(bottom.raw_return,method='spearman'))
        for key in ['rank_ic','pure_long_return','pure_short_return','long_short_return']:
            assert abs(row[key]-float(saved.loc[date,key]))<1e-12,(date,key)
        rows.append(row)
        for decile,g in base.groupby('decile'):
            v=g.raw_return.dropna()
            groups.append(dict(date=date,decile=int(decile),mean=float(v.mean()),median=float(v.median()),std=float(v.std(ddof=1)),excess=float(v.mean()-market),count=len(v)))
    daily=pd.DataFrame(rows)
    groupdaily=pd.DataFrame(groups)
    groupstats=groupdaily.groupby('decile')[['mean','median','std','count']].mean()
    groupstats['excess_sharpe']=groupdaily.groupby('decile').excess.apply(sharpe)
    extra=dict(rank_ic_positive_fraction=float((daily.rank_ic>0).mean()),mean_middle_ic=float(daily.middle_ic.mean()),mean_bottom_ic=float(daily.bottom_ic.mean()),mean_rank_base=float(daily.rank_base_count.mean()),ic_ir=sharpe(daily.rank_ic),daily_ic_ls_corr=float(daily.rank_ic.corr(daily.long_short_return)),long_excess_sharpe=sharpe(daily.long_excess),short_excess_sharpe=sharpe(daily.short_excess),market_sharpe=sharpe(daily.market),mean_pearson_ic=float(daily.pearson_ic.mean()))
    evidence={'test_daily':daily.to_dict('records'),'deciles':groupstats.reset_index().to_dict('records'),'decile_daily':groupdaily.to_dict('records'),'extra_analysis':extra,'test_summary':summary,'training_summary':timing,'effective_parameters':params,'environment':load('environment.json'),'dataset':dataset,'selection':selection,'model_identity':load('frozen_model_identity.json'),'code_identity':load('code_identity.json'),'feature_mapping':load('feature_mapping_330.json'),'audit':{name:audit(name) for name in ['all_test_label_audit.json','audit_raw_summary.json','provenance_audit.json','distribution_audit.json','independent_audit_summary.json']},'validation_curve':curve.to_dict('records'),'resource_samples':resources.to_dict('records')}
    mapping_records=evidence['feature_mapping']
    evidence['feature_mapping']=[r for r in mapping_records if 'model_column' in r]
    evidence['feature_exclusions']=[r for r in mapping_records if 'excluded_old_columns' in r]
    assert len(evidence['feature_mapping'])==330
    assert [r['index'] for r in evidence['feature_mapping']]==list(range(330))
    sources=[p/name for name in ['test_predictions.parquet','test_daily_metrics.parquet','per_round_metrics.parquet','resource_samples.parquet','effective_parameters.json','feature_mapping_330.json','timing_resource_summary.json']]
    evidence['source_files']=[{'name':v.name,'bytes':v.stat().st_size,'sha256':digest(v)} for v in sources]
    out=ROOT/'content/assets/model-report-2026-09-18'
    out.mkdir(parents=True,exist_ok=True)
    data=json.dumps(json_safe(evidence),ensure_ascii=False,separators=(',',':'),allow_nan=False)
    (out/'report-data.json').write_text(data,encoding='utf-8')
    plots={}
    def line(key,title,s,caption,labels=None,unit='',marker=None,scatter=False):
        plots[key]=figure(key,title,svg_chart(title,s,labels,scatter,unit,marker),caption)
    def bar(key,title,labels,s,caption,unit='',horizontal=False):
        plots[key]=figure(key,title,bars(title,labels,s,unit,horizontal),caption)
    def series(name,values,color,x=None):
        return dict(name=name,color=color,points=list(zip(range(len(values)) if x is None else x,values)))
    def bs(name,values,color):return dict(name=name,values=list(values),color=color)
    iterations=curve.iteration.tolist()
    line('validation-sharpe','01 · validation：按多空 Sharpe 选择 659 轮',[series('多空各 10%',curve.long_short_sharpe,TEAL,iterations),series('纯多 20%',curve.pure_long_sharpe,RUST,iterations),series('纯空 20%',curve.pure_short_sharpe,BLUE,iterations)],'完整训练 1000 轮，无 early stopping。竖线只由 validation 多空 Sharpe 确定；不在 test 上选轮。',unit='年化毛 Sharpe',marker=659)
    line('validation-ic','02 · validation：RankIC 的训练路径',[series('日均 RankIC',curve.validation_mean_rank_ic,TEAL,iterations)],'第 659 轮为 0.016604；第 1000 轮为 0.014269。单月路径不构成最终参数选择的充分证据。',unit='日均 RankIC',marker=659)
    line('validation-mse','03 · validation：标准化目标的 MSE',[series('按日等权 MSE',curve.validation_daily_equal_mse,BLUE,iterations)],'L2 是训练目标；选轮指标为组合 Sharpe。二者不必在同一轮达到最优。MSE 不以 bp 为单位。',unit='标准化目标平方误差',marker=659)
    cumulative=[]
    for key,name,color,mult in [('long_short_return','多空：每腿 50%',TEAL,.5),('pure_long_return','纯多 20%',RUST,1),('pure_short_return','纯空 20%',BLUE,1)]:
        cumulative.append(series(name,(np.cumprod(1+daily[key]*mult)-1)*100,color))
    line('test-cumulative','04 · test：统一总名义敞口后的机械累计收益',cumulative,'多空每日收益先除以 2，再连乘；纯多、纯空按单腿 100%。这是毛收益序列的机械复合，不含现金、保证金、费用及可成交约束，不是账户净值。',dates,unit='累计毛收益 %')
    monthly=pd.DataFrame(summary['monthly_metrics'])
    bar('monthly','05 · test：月度 Sharpe 并不均匀',monthly.month.str[2:], [bs('多空各 10%',monthly.long_short_sharpe,TEAL),bs('纯多 20%',monthly.pure_long_sharpe,RUST),bs('纯空 20%',monthly.pure_short_sharpe,BLUE)],'各月只有 14–23 个交易日，短样本年化数值不稳定；2025-11 的高值不代表全年可持续。',unit='月内日收益年化 Sharpe')
    line('ic-scatter','06 · 同一天的 RankIC 与多空收益',[series('176 个交易日',daily.long_short_return*1e4,TEAL,daily.rank_ic)],f'逐日相关系数 {extra["daily_ic_ls_corr"]:.3f}。相关性强不等于二者成固定比例；收益截距、波动和尾部形状仍会改变 Sharpe。',unit='多空收益 bp；横轴 RankIC',scatter=True)
    line('daily-ic','07 · RankIC 每天有多稳定',[series('日度 RankIC',daily.rank_ic,GRAY),series('20 日滚动均值',daily.rank_ic.rolling(20).mean(),TEAL)],f'日均 0.02204，日标准差 0.07229；正值日占 {extra["rank_ic_positive_fraction"]:.1%}。年化 ICIR 为 {extra["ic_ir"]:.2f}，不是组合 Sharpe。',dates,unit='RankIC')
    labels=[f'D{i}' for i in range(1,11)]
    bar('deciles','08 · 最高分 10% 的均值最突出',labels,[bs('日均组平均收益',groupstats['mean']*1e4,TEAL),bs('日均组中位收益',groupstats['median']*1e4,RUST)],'每日在 rank_base 内按分数平均秩分十组，同分同组；先算每组均值/中位数，再对日期等权。本图不做封板过滤，故 D10 与正式多头 10% 的 10.79bp 略有不同。',unit='收益 bp')
    bar('dispersion','09 · 两端的个股收益分布更宽',labels,[bs('日均组内截面标准差',groupstats['std']*1e4,BLUE)],'这里是组内个股收益的截面标准差，再对日期取平均；不是组组合每日收益的时间序列波动。二者不可混用。',unit='个股收益截面标准差 bp')
    bar('decile-excess','10 · 分组相对全体等权的收益',labels,[bs('组收益 − 当日全体等权',groupstats.excess_sharpe,TEAL)],'全体等权基准使用同一天 rank_base 内有有效标签的股票。D1 负值表示跑输基准；不等于裸空 D1 的收益。',unit='超额收益年化 Sharpe')
    bar('local-ic','11 · 不同分数区间内部的排序信息',['全体有效标签','分数 20%–80%','最低分 10%'],[bs('日均区间内 RankIC',[daily.rank_ic.mean(),daily.middle_ic.mean(),daily.bottom_ic.mean()],TEAL)],'区间选取用进场可选基数的分数秩；区间内再用有效标签算相关。这是已打开 test 后的诊断，范围收窄本身也会降低相关，不能据此断言中间股票完全没有信息。',unit='RankIC')
    bar('legs','12 · 多空相减抵消部分共同波动',['多头最高 10%','空头最低 10%','多空各 10%'],[bs('日均收益 bp',[daily.long10.mean()*1e4,daily.short10.mean()*1e4,daily.long_short_return.mean()*1e4],TEAL),bs('每日收益标准差 bp',[daily.long10.std()*1e4,daily.short10.std()*1e4,daily.long_short_return.std()*1e4],RUST)],'两篮子原始收益的相关系数为 0.7354。相减后波动为 28.29bp；空头一行已将标的收益取负。该图多空按每腿 100% 的原定义展示。',unit='bp')
    stress=[7.300545039,independent['return_series']['ls_ungated']['sharpe'],dist['diagnostics']['zero_missing_ls']['sharpe'],independent['return_series']['ls_winsor100bp']['sharpe'],dist['diagnostics']['trim_abs_1pct_ls']['sharpe'],6.21575]
    bar('sensitivity','13 · 排查封板、缺失标签和尾部贡献',['原始结果','取消封板过滤','缺失标签按 0 计','个股收益压到 ±1%','剔除每腿极端 1%','移除最好 10 个交易日'],[bs('多空 Sharpe',stress,TEAL)],'同一组已保存预测的事后敏感性分析，不是新模型或可交易选股规则；最后一项显示保留证据中的四舍五入值。',unit='年化毛 Sharpe',horizontal=True)
    bar('market','14 · 相对全体等权后，仍有收益差',['全体等权','纯多 20% − 全体','全体 − 最低 20%'],[bs('对应收益序列 Sharpe',[extra['market_sharpe'],extra['long_excess_sharpe'],extra['short_excess_sharpe']],TEAL)],'这是相对基准诊断，不是 beta 中性化。第三项是空头相对基准的超额收益，不能当作纯空本身的 0.576 Sharpe。',unit='年化毛 Sharpe')
    times=timing['timings_seconds']
    bar('timing','15 · 耗时主要在输入与标签准备',['读取因子与准备标签','对齐、标准化、矩阵','Dataset 构建与分箱','训练剩余（含框架）','逐轮评价回调','预测核对与保存','绘图与报告'],[bs('墙钟秒',[times['data_read_and_label_prepare'],times['alignment_standardization_matrix'],times['lightgbm_dataset_construct_and_binning'],times['train_call_minus_evaluation_including_framework_overhead'],times['train_internal_per_round_evaluation'],times['post_train_prediction_verification']+times['model_and_result_save'],times['plot_and_report_seconds']],TEAL)],'训练剩余 52.47 秒仍包含框架开销，不叫纯算法时间。阶段和整体之间还含少量初始化、调度及统计开销。',unit='秒',horizontal=True)
    x=resources.monotonic_seconds-resources.monotonic_seconds.iloc[0]
    line('memory','16 · 全流程内存轨迹',[series('任务 cgroup',resources.task_memory_current/2**30,TEAL,x),series('进程树 RSS',resources.process_tree_rss/2**30,RUST,x),series('文件缓存',resources.task_memory_file/2**30,BLUE,x)],'cgroup 峰值 13.14GiB；RSS 与 cgroup 内存不是同一口径，不能相加。任务上限 60GiB，high=52GiB，swap=0；无新增 OOM 或内存 high 事件。',unit='GiB；横轴业务启动后秒')
    cpu=resources.task_cpu_usage_usec.diff()/resources.monotonic_seconds.diff()/1e6
    line('cpu','17 · CPU 使用集中在训练阶段',[series('采样间隔等效核数',cpu,TEAL,x)],'约每 1 秒采样；训练阶段平均 7.00 核，全流程平均 1.17 核。累计 CPU 配额限流 0.144 秒；一次观察不能证明最优线程数。',unit='等效核数；横轴秒')
    roundcost=timing['per_100_round_wall_seconds']
    bar('round-speed','18 · 每 100 轮的墙钟耗时',[str(r['round_end']) for r in roundcost],[bs('每 100 轮含评价',[r['wall_seconds'] for r in roundcost],TEAL)],'首 100 轮 7.61 秒，后续约 6.23–6.78 秒；没有观察到随轮数不断增加的重复预测开销。',unit='秒；横轴轮数终点')
    report=(ROOT/'templates/model-report-20260918.html').read_text(encoding='utf-8')
    replacement={**plots,'DATA':data.replace('</','<\\/'),'PARAMETERS':html.escape(json.dumps(params,ensure_ascii=False,indent=2)),'EXTRA':table(['指标','test 结果'],[['RankIC 均值 / 日标准差',f'{daily.rank_ic.mean():.5f} / {daily.rank_ic.std():.5f}'],['RankIC 正值日',f'{(daily.rank_ic>0).sum()} / 176（{extra["rank_ic_positive_fraction"]:.1%}）'],['年化 ICIR',f'{extra["ic_ir"]:.3f}'],['日均 Pearson IC',f'{extra["mean_pearson_ic"]:.5f}'],['每日平均进场可选股票',f'{extra["mean_rank_base"]:,.1f}'],['纯多 20% 相对基准 Sharpe',f'{extra["long_excess_sharpe"]:.3f}'],['纯空 20% 相对基准 Sharpe',f'{extra["short_excess_sharpe"]:.3f}']]),'MONTHLY_TABLE':table(['月份','天数','RankIC','多空 Sharpe','纯多 Sharpe','纯空 Sharpe'],[[m['month'],m['date_count'],f'{m["mean_daily_rank_ic"]:.4f}',f'{m["long_short_sharpe"]:.2f}',f'{m["pure_long_sharpe"]:.2f}',f'{m["pure_short_sharpe"]:.2f}'] for m in summary['monthly_metrics']]),'DECILE_TABLE':table(['组','均值 bp','中位数 bp','截面标准差 bp','超额 Sharpe'],[[f'D{i}',f'{r["mean"]*1e4:.2f}',f'{r["median"]*1e4:.2f}',f'{r["std"]*1e4:.2f}',f'{r["excess_sharpe"]:.2f}'] for i,r in groupstats.iterrows()])}
    for key,value in replacement.items():
        report=report.replace('@@'+key+'@@',value)
    assert '@@' not in report,'unfilled report token'
    (ROOT/'content/daily/2026-09-18.show.html').write_text(report,encoding='utf-8')
    print(json.dumps(extra,indent=2))
    print('report_bytes',len(report.encode('utf-8')),'chart_count',len(plots))


if __name__=='__main__':
    main()
