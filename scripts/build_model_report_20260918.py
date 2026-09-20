"""Build the frozen-model research report from existing, read-only run artifacts."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import report_charts as rc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEAL, RUST, BLUE, GRAY, SAND = rc.TEAL, rc.RUST, rc.BLUE, rc.GRAY, rc.SAND
DECILES = [f'D{i}' for i in range(1, 11)]

# Frozen research calendar (decided 2026-08-24): 2024H1 seeds training, then one
# expanding fold per natural month, then the sealed test window.
INITIAL_TRAIN_END = '2024-07-01'


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


def decile_span(deciles):
    """Compact a decile list: consecutive runs become D3–D8."""
    parts, run = [], [deciles[0]]
    for d in deciles[1:]:
        if d == run[-1] + 1:
            run.append(d)
        else:
            parts.append(run)
            run = [d]
    parts.append(run)
    return '、'.join(f'D{r[0]}–D{r[-1]}' if len(r) > 2 else '、'.join(f'D{x}' for x in r) for r in parts)


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def figure(chart_id, title, svg, caption):
    return f'<figure id="{chart_id}"><div class="figure-top"><h3>{title}</h3><button class="enlarge" type="button" aria-label="放大：{title}">放大图表</button></div><div class="chart-scroll">{svg}</div><figcaption>{caption}</figcaption></figure>'


def legend_patch(color, label):
    return Patch(facecolor=color, edgecolor='none', label=label)


def expanding_folds(development_dates):
    """Derive the 15 natural-month validation folds from the development calendar."""
    dates = sorted(development_dates)
    seed = [d for d in dates if d < INITIAL_TRAIN_END]
    months = sorted({d[:7] for d in dates if d >= INITIAL_TRAIN_END})
    folds, trained = [], len(seed)
    for index, month in enumerate(months, start=1):
        window = [d for d in dates if d[:7] == month]
        folds.append({
            'fold': index,
            'month': month,
            'train_start': dates[0],
            'train_end': [d for d in dates if d < window[0]][-1],
            'train_days': trained,
            'validation_start': window[0],
            'validation_end': window[-1],
            'validation_days': len(window),
        })
        trained += len(window)
    return seed, folds


# The pools each portfolio actually ranks within, plus the untraded middle and
# the whole cross-section the headline RankIC is averaged over.
POOLS = [
    ('all', '全体 10 组', tuple(range(1, 11))),
    ('middle', '中段 D3–D8（从不交易）', (3, 4, 5, 6, 7, 8)),
    ('short', '纯空池 D1∪D2', (1, 2)),
    ('long', '纯多池 D9∪D10', (9, 10)),
    ('traded', '三组合合计 D1,D2,D9,D10', (1, 2, 9, 10)),
    ('long_short', '多空池 D1∪D10', (1, 10)),
    ('spaced_control', '对照：等间隔 D1∪D5∪D10', (1, 5, 10)),
]


def spearman(x, y):
    if len(x) < 3:
        return np.nan
    rx = pd.Series(x).rank(method='average').to_numpy()
    ry = pd.Series(y).rank(method='average').to_numpy()
    ax, ay = rx - rx.mean(), ry - ry.mean()
    denominator = math.sqrt(float(ax @ ax) * float(ay @ ay))
    return float((ax @ ay) / denominator) if denominator > 0 else np.nan


def rank_ic_breakdown(predictions):
    """Three readings of the same day's RankIC, all on the correlation scale.

    `contribution` is each decile's additive share of the whole cross-section's
    Spearman, so the ten values sum exactly to the day's RankIC.
    `inner` re-ranks inside one decile alone.
    `pool` restricts the cross-section to the deciles a portfolio actually ranks
    within, then re-ranks — this is the number comparable to the headline 0.0220.
    """
    contributions, inner, pools, counts = [], [], [], []
    for _, full in predictions.groupby('date', sort=True):
        base = full[full.rank_base]
        percentile = base.score.rank(method='average', pct=True)
        decile = np.minimum(10, np.ceil(percentile * 10)).astype(int).to_numpy()
        keep = base.raw_return.notna().to_numpy()
        score, ret, group = base.score.to_numpy()[keep], base.raw_return.to_numpy()[keep], decile[keep]
        rx = pd.Series(score).rank(method='average').to_numpy()
        ry = pd.Series(ret).rank(method='average').to_numpy()
        ax, ay = rx - rx.mean(), ry - ry.mean()
        denominator = math.sqrt(float(ax @ ax) * float(ay @ ay))
        if denominator <= 0:
            continue
        share = (ax * ay) / denominator
        row, local, count = {}, {}, {}
        for k in range(1, 11):
            sel = group == k
            row[k] = float(share[sel].sum())
            count[k] = int(sel.sum())
            local[k] = spearman(score[sel], ret[sel]) if sel.sum() >= 3 else np.nan
        pool = {}
        for key, _, members in POOLS:
            sel = np.isin(group, members)
            pool[key] = spearman(score[sel], ret[sel])
            pool[key + '__count'] = int(sel.sum())
        contributions.append(row)
        inner.append(local)
        pools.append(pool)
        counts.append(count)
    return (pd.DataFrame(contributions), pd.DataFrame(inner),
            pd.DataFrame(pools), pd.DataFrame(counts))


TEMPLATE = ROOT / 'templates/model-report-20260918.html'
STOCK_CONTEXT = ROOT / 'scripts/model_report_20260918_stock_context.json'
# Figure numbers follow the order the template places them, so moving a figure in
# the page is enough — no hand-maintained numbering to drift.
FIGURE_ORDER = re.findall(r'@@([a-z][a-z-]*)@@', TEMPLATE.read_text(encoding='utf-8'))


def title_of(key, name):
    return f'{FIGURE_ORDER.index(key) + 1:02d} · {name}'


def rank_between_within(predictions):
    """Decompose full-cross-section Spearman into between- and within-decile terms."""
    rows = []
    for date, full in predictions.groupby('date', sort=True):
        base = full[full.rank_base & full.raw_return.notna()].copy()
        base['score_rank'] = base.score.rank(method='average')
        base['return_rank'] = base.raw_return.rank(method='average')
        base['decile'] = np.minimum(10, np.ceil(base.score.rank(method='average', pct=True) * 10)).astype(int)
        score_centered = base.score_rank - base.score_rank.mean()
        return_centered = base.return_rank - base.return_rank.mean()
        denominator = math.sqrt(float(score_centered @ score_centered) * float(return_centered @ return_centered))
        between = 0.0
        within = 0.0
        for _, group in base.groupby('decile'):
            between += (len(group) * (group.score_rank.mean() - base.score_rank.mean())
                        * (group.return_rank.mean() - base.return_rank.mean()))
            within += float(((group.score_rank - group.score_rank.mean())
                             * (group.return_rank - group.return_rank.mean())).sum())
        total = float(score_centered @ return_centered) / denominator
        rows.append({'date': date, 'total': total, 'between': between / denominator,
                     'within': within / denominator})
    result = pd.DataFrame(rows)
    assert np.max(np.abs(result.total - result.between - result.within)) < 1e-12
    return result


def moving_block_bootstrap(values, *, block=5, draws=10_000, seed=20260920):
    """Circular moving-block intervals for the daily mean and annualized Sharpe."""
    values = np.asarray(values, dtype=float)
    count = len(values)
    blocks = math.ceil(count / block)
    rng = np.random.default_rng(seed)
    means = np.empty(draws)
    sharpes = np.empty(draws)
    for i in range(draws):
        starts = rng.integers(0, count, size=blocks)
        indices = np.concatenate([(np.arange(start, start + block) % count) for start in starts])[:count]
        sample = values[indices]
        means[i] = sample.mean()
        sharpes[i] = np.sqrt(252) * sample.mean() / sample.std(ddof=1)
    return {
        'method': 'circular_moving_block', 'block_days': block, 'draws': draws, 'seed': seed,
        'mean_return_quantiles': dict(zip(['p025', 'p500', 'p975'], np.quantile(means, [.025, .5, .975]))),
        'sharpe_quantiles': dict(zip(['p025', 'p500', 'p975'], np.quantile(sharpes, [.025, .5, .975]))),
    }


def main():
    report = TEMPLATE.read_text(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    p = args.input
    load = lambda name: json.loads((p / name).read_text(encoding='utf-8'))
    audit = lambda name: json.loads((args.audit / name).read_text(encoding='utf-8'))
    predictions = pd.read_parquet(p / 'test_predictions.parquet')
    saved = pd.read_parquet(p / 'test_daily_metrics.parquet').set_index('date')
    curve = pd.read_parquet(p / 'per_round_metrics.parquet')
    resources = pd.read_parquet(p / 'resource_samples.parquet')
    summary = audit('test_summary.json')
    timing = load('timing_resource_summary.json')
    params = load('effective_parameters.json')
    selection = load('validation_selection_receipt.json')
    dataset = load('dataset_summary.json')
    dist = audit('distribution_audit.json')
    independent = audit('independent_audit_summary.json')
    stock_context = json.loads(STOCK_CONTEXT.read_text(encoding='utf-8'))
    assert len(predictions) == 507460 and not predictions.duplicated(['date', 'code']).any()
    assert int(curve.loc[curve.long_short_sharpe.idxmax(), 'iteration']) == 659
    assert digest(p / 'per_round_metrics.parquet') == selection['curve_sha256']

    seed_dates, folds = expanding_folds(dataset['train_dates'] + dataset['validation_dates'])
    assert len(folds) == 15
    assert folds[-1]['validation_start'] == dataset['validation_dates'][0]
    assert folds[-1]['train_days'] == len(dataset['train_dates'])
    oof_days = sum(f['validation_days'] for f in folds)

    dates, rows, groups, breadth_rows, stockday_rows = [], [], [], [], []
    for date, full in predictions.groupby('date', sort=True):
        dates.append(date)
        valid = full[np.isfinite(full.raw_return)]
        base = full[full.rank_base].copy()
        n = len(base)

        def leg(q, highest):
            k = math.ceil(q * n)
            threshold = base.score.nlargest(k).iloc[-1] if highest else base.score.nsmallest(k).iloc[-1]
            selected = base[base.score.ge(threshold) if highest else base.score.le(threshold)]
            selected = selected[~selected.no_long] if highest else selected[~selected.no_short]
            selected = selected.dropna(subset=['raw_return']).copy()
            return (float(selected.raw_return.mean()) if len(selected) else 0.0), len(selected), selected

        l20, nl20, _ = leg(.2, True)
        s20, ns20, _ = leg(.2, False)
        l10, nl10, long10_selected = leg(.1, True)
        s10, ns10, short10_selected = leg(.1, False)
        ls = l10 - s10 if nl10 and ns10 else 0.0
        for q in (.05, .10, .20, .30):
            long_return, long_count, _ = leg(q, True)
            short_return, short_count, _ = leg(q, False)
            breadth_rows.append({
                'date': date, 'tail_fraction': q, 'long_return': long_return,
                'short_underlying_return': short_return,
                'long_short_return': long_return - short_return,
                'mean_leg_count': (long_count + short_count) / 2,
            })
        for selected, leg_name, sign in ((long10_selected, 'long', 1.0),
                                         (short10_selected, 'short', -1.0)):
            denominator = len(selected)
            for record in selected[['code', 'score', 'raw_return']].to_dict('records'):
                stockday_rows.append({
                    'date': date, 'code': record['code'], 'leg': leg_name,
                    'score': record['score'], 'raw_return': record['raw_return'],
                    'contribution': sign * record['raw_return'] / denominator,
                })
        market = float(base.raw_return.mean())
        percentile = base.score.rank(method='average', pct=True)
        base['decile'] = np.minimum(10, np.ceil(percentile * 10)).astype(int)
        middle = base[(percentile > .2) & (percentile <= .8)].dropna(subset=['raw_return'])
        bottom = base[base.decile == 1].dropna(subset=['raw_return'])
        row = dict(date=date, rank_ic=valid.score.corr(valid.raw_return, method='spearman'), pearson_ic=valid.score.corr(valid.raw_return), pure_long_return=l20, pure_short_return=-s20, long_short_return=ls, long10=l10, short10=-s10, market=market, long_excess=l20 - market, short_excess=market - s20, rank_base_count=n, long10_count=nl10, short10_count=ns10, middle_ic=middle.score.corr(middle.raw_return, method='spearman'), bottom_ic=bottom.score.corr(bottom.raw_return, method='spearman'))
        for key in ['rank_ic', 'pure_long_return', 'pure_short_return', 'long_short_return']:
            assert abs(row[key] - float(saved.loc[date, key])) < 1e-12, (date, key)
        rows.append(row)
        for decile, g in base.groupby('decile'):
            v = g.raw_return.dropna()
            groups.append(dict(date=date, decile=int(decile), mean=float(v.mean()), median=float(v.median()), std=float(v.std(ddof=1)), excess=float(v.mean() - market), count=len(v)))
    daily = pd.DataFrame(rows)
    groupdaily = pd.DataFrame(groups)
    breadth_daily = pd.DataFrame(breadth_rows)
    stockdays = pd.DataFrame(stockday_rows)
    groupstats = groupdaily.groupby('decile')[['mean', 'median', 'std', 'count']].mean()
    groupstats['excess_sharpe'] = groupdaily.groupby('decile').excess.apply(sharpe)
    groupstats['own_sharpe'] = groupdaily.groupby('decile')['mean'].apply(sharpe)
    wide = groupdaily.pivot(index='date', columns='decile', values='mean')
    groupstats['nw_se_bp'] = [rc.newey_west_se(wide[k]) * 1e4 for k in range(1, 11)]

    contribution, inner_ic, pool_ic, decile_counts = rank_ic_breakdown(predictions)
    mean_contribution, mean_inner = contribution.mean(), inner_ic.mean()
    total_ic = float(daily.rank_ic.mean())
    # The decomposition is exact; the whole-universe pool and D1's inner value
    # both reproduce numbers the page already published.
    assert abs(float(mean_contribution.sum()) - total_ic) < 1e-12
    assert abs(float(mean_inner[1]) - float(daily.bottom_ic.mean())) < 1e-12
    assert abs(float(pool_ic['all'].mean()) - total_ic) < 1e-12
    assert abs(float(pool_ic['middle'].mean()) - float(daily.middle_ic.mean())) < 1e-12
    groupstats['rank_ic_contribution'] = [float(mean_contribution[k]) for k in range(1, 11)]
    groupstats['inner_rank_ic'] = [float(mean_inner[k]) for k in range(1, 11)]
    groupstats['inner_rank_ic_std'] = [float(inner_ic[k].std(ddof=1)) for k in range(1, 11)]
    groupstats['inner_rank_ic_ir'] = [sharpe(inner_ic[k]) for k in range(1, 11)]
    groupstats['inner_rank_ic_positive'] = [float((inner_ic[k] > 0).mean()) for k in range(1, 11)]

    pools = []
    for key, label, members in POOLS:
        series = pool_ic[key]
        pools.append({
            'key': key,
            'label': label,
            'deciles': list(members),
            'mean_rank_ic': float(series.mean()),
            'std_rank_ic': float(series.std(ddof=1)),
            'positive_fraction': float((series > 0).mean()),
            'ic_ir': sharpe(series),
            'nw_se': rc.newey_west_se(series),
            'mean_count': float(pool_ic[key + '__count'].mean()),
        })
    pool_by_key = {row['key']: row for row in pools}

    traded_share = float(mean_contribution[[1, 2, 9, 10]].sum() / total_ic)
    middle_share = float(mean_contribution[[3, 4, 5, 6, 7, 8]].sum() / total_ic)
    tail_share = float(mean_contribution[[1, 10]].sum() / total_ic)
    reconstructed = {
        'pure_long': sharpe(wide[[9, 10]].mean(axis=1)),
        'pure_short': sharpe(-wide[[1, 2]].mean(axis=1)),
        'long_short': sharpe(wide[10] - wide[1]),
    }

    rank_decomposition_daily = rank_between_within(predictions)
    rank_decomposition = {
        'total': float(rank_decomposition_daily.total.mean()),
        'between_deciles': float(rank_decomposition_daily.between.mean()),
        'within_deciles': float(rank_decomposition_daily.within.mean()),
    }
    rank_decomposition['between_share'] = rank_decomposition['between_deciles'] / rank_decomposition['total']
    rank_decomposition['within_share'] = rank_decomposition['within_deciles'] / rank_decomposition['total']

    short_underlying = -daily.short10
    long_variance = float(daily.long10.var(ddof=1))
    short_variance = float(short_underlying.var(ddof=1))
    covariance = float(daily.long10.cov(short_underlying))
    long_short_variance = float(daily.long_short_return.var(ddof=1))
    covariance_offset = 2 * covariance
    variance_decomposition = {
        'long_mean_bp': float(daily.long10.mean() * 1e4),
        'short_underlying_mean_bp': float(short_underlying.mean() * 1e4),
        'long_short_mean_bp': float(daily.long_short_return.mean() * 1e4),
        'long_std_bp': float(daily.long10.std(ddof=1) * 1e4),
        'short_underlying_std_bp': float(short_underlying.std(ddof=1) * 1e4),
        'long_short_std_bp': float(daily.long_short_return.std(ddof=1) * 1e4),
        'long_variance_bp2': long_variance * 1e8,
        'short_variance_bp2': short_variance * 1e8,
        'minus_two_covariance_bp2': -covariance_offset * 1e8,
        'long_short_variance_bp2': long_short_variance * 1e8,
        'underlying_leg_correlation': float(daily.long10.corr(short_underlying)),
        'variance_offset_share': covariance_offset / (long_variance + short_variance),
        'zero_covariance_std_bp': math.sqrt(long_variance + short_variance) * 1e4,
        'zero_covariance_sharpe': float(np.sqrt(252) * daily.long_short_return.mean()
                                         / math.sqrt(long_variance + short_variance)),
    }
    assert abs(long_variance + short_variance - covariance_offset - long_short_variance) < 1e-15

    breadth = []
    for fraction, group in breadth_daily.groupby('tail_fraction', sort=True):
        series = group.long_short_return
        breadth.append({
            'tail_fraction': float(fraction), 'mean_return_bp': float(series.mean() * 1e4),
            'std_return_bp': float(series.std(ddof=1) * 1e4), 'sharpe': sharpe(series),
            'mean_leg_count': float(group.mean_leg_count.mean()),
        })

    quadrants = []
    for ic_positive, return_positive, label in [
            (True, True, 'RankIC≥0，组合盈利'), (False, True, 'RankIC<0，组合盈利'),
            (True, False, 'RankIC≥0，组合亏损'), (False, False, 'RankIC<0，组合亏损')]:
        selected = daily[(daily.rank_ic.ge(0) == ic_positive)
                         & (daily.long_short_return.ge(0) == return_positive)]
        quadrants.append({
            'label': label, 'days': len(selected), 'mean_rank_ic': float(selected.rank_ic.mean()),
            'mean_return_bp': float(selected.long_short_return.mean() * 1e4),
            'cumulative_return_sum': float(selected.long_short_return.sum()),
        })

    bootstrap = moving_block_bootstrap(daily.long_short_return)
    monthly_stability = []
    daily_with_month = daily.assign(month=daily.date.str[:7])
    total_return_sum = float(daily.long_short_return.sum())
    for month, group in daily_with_month.groupby('month', sort=True):
        remaining = daily_with_month[daily_with_month.month != month].long_short_return
        monthly_stability.append({
            'month': month, 'days': len(group),
            'return_sum_share': float(group.long_short_return.sum() / total_return_sum),
            'mean_return_bp': float(group.long_short_return.mean() * 1e4),
            'leave_one_month_out_sharpe': sharpe(remaining),
        })

    names = stock_context['stock_names']
    published_codes = set(names)
    top_positive = stockdays.nlargest(10, 'contribution').copy()
    top_negative = stockdays.nsmallest(10, 'contribution').copy()
    assert set(top_positive.code) | set(top_negative.code) <= published_codes
    for frame in (top_positive, top_negative):
        frame['name'] = frame.code.map(names)
    aggregate = stockdays.groupby('code').agg(
        cumulative_contribution=('contribution', 'sum'), selected_days=('date', 'size'),
        long_days=('leg', lambda values: int((values == 'long').sum())),
        short_days=('leg', lambda values: int((values == 'short').sum())),
    ).reset_index()
    aggregate['name'] = aggregate.code.map(names)
    aggregate_positive = aggregate.nlargest(5, 'cumulative_contribution').copy()
    aggregate_negative = aggregate.nsmallest(5, 'cumulative_contribution').copy()
    assert aggregate_positive.name.notna().all() and aggregate_negative.name.notna().all()
    positive_contributions = stockdays.loc[stockdays.contribution > 0, 'contribution'].sort_values(ascending=False)
    concentration = []
    for count in (1, 5, 10, 20, 50, 100):
        concentration.append({
            'top_positive_stockdays': count,
            'share_of_net_cumulative_return': float(positive_contributions.head(count).sum() / total_return_sum),
        })
    concentration_summary = {
        'net_cumulative_return_sum': total_return_sum,
        'selected_stockdays': len(stockdays), 'unique_stocks': int(stockdays.code.nunique()),
        'largest_positive_stockday_share': concentration[0]['share_of_net_cumulative_return'],
        'top_10_positive_stockdays_share': concentration[2]['share_of_net_cumulative_return'],
        'largest_positive_stock_share': float(aggregate_positive.iloc[0].cumulative_contribution / total_return_sum),
    }

    cases = []
    for case in stock_context['cases']:
        match = stockdays[(stockdays.date == case['date']) & (stockdays.code == case['code'])
                          & (stockdays.leg == case['leg'])]
        assert len(match) == 1, case
        observed = match.iloc[0]
        cases.append({
            **case, 'score': float(observed.score), 'raw_return': float(observed.raw_return),
            'contribution': float(observed.contribution),
        })

    extra = dict(rank_ic_positive_fraction=float((daily.rank_ic > 0).mean()), mean_middle_ic=float(daily.middle_ic.mean()), mean_bottom_ic=float(daily.bottom_ic.mean()), mean_rank_base=float(daily.rank_base_count.mean()), ic_ir=sharpe(daily.rank_ic), daily_ic_ls_corr=float(daily.rank_ic.corr(daily.long_short_return)), long_excess_sharpe=sharpe(daily.long_excess), short_excess_sharpe=sharpe(daily.short_excess), market_sharpe=sharpe(daily.market), mean_pearson_ic=float(daily.pearson_ic.mean()), traded_decile_ic_share=traded_share, middle_decile_ic_share=middle_share, extreme_decile_ic_share=tail_share, decile_reconstructed_sharpe=reconstructed)

    diagnostics = {
        'rank_between_within': rank_decomposition,
        'rank_between_within_daily': rank_decomposition_daily.to_dict('records'),
        'variance_decomposition': variance_decomposition,
        'tail_breadth': breadth,
        'rankic_return_quadrants': quadrants,
        'moving_block_bootstrap': bootstrap,
        'monthly_stability': monthly_stability,
        'stockday_concentration': concentration,
        'stockday_concentration_summary': concentration_summary,
        'top_positive_stockdays': top_positive.to_dict('records'),
        'top_negative_stockdays': top_negative.to_dict('records'),
        'top_aggregate_positive_stocks': aggregate_positive.to_dict('records'),
        'top_aggregate_negative_stocks': aggregate_negative.to_dict('records'),
        'real_world_cases': cases,
        'stock_name_snapshot_as_of': stock_context['name_snapshot_as_of'],
        'publication_scope': 'selected attribution only; complete per-stock predictions are not published',
    }
    rank_ic_daily_records = [
        {
            'date': date,
            **{f'contribution_D{k}': float(contribution[k].iloc[i]) for k in range(1, 11)},
            **{f'inner_ic_D{k}': (float(inner_ic[k].iloc[i])
                                  if np.isfinite(inner_ic[k].iloc[i]) else None)
               for k in range(1, 11)},
            **{f'pool_{key}': (float(pool_ic[key].iloc[i])
                               if np.isfinite(pool_ic[key].iloc[i]) else None)
               for key, _, _ in POOLS},
        }
        for i, date in enumerate(dates)
    ]
    evidence = {
        'test_daily': daily.to_dict('records'),
        'deciles': groupstats.reset_index().to_dict('records'),
        'decile_daily': groupdaily.to_dict('records'),
        'decile_rank_ic_daily': rank_ic_daily_records,
        'rank_ic_pools': pools,
        'expanding_folds': folds,
        'extra_analysis': extra,
        'diagnostics': diagnostics,
        'test_summary': summary,
        'training_summary': timing,
        'effective_parameters': params,
        'environment': load('environment.json'),
        'dataset': dataset,
        'selection': selection,
        'model_identity': load('frozen_model_identity.json'),
        'code_identity': load('code_identity.json'),
        'feature_mapping': load('feature_mapping_330.json'),
        'audit': {name: audit(name) for name in [
            'all_test_label_audit.json', 'audit_raw_summary.json', 'provenance_audit.json',
            'distribution_audit.json', 'independent_audit_summary.json',
        ]},
        'validation_curve': curve.to_dict('records'),
        'resource_samples': resources.to_dict('records'),
    }
    mapping_records = evidence['feature_mapping']
    evidence['feature_mapping'] = [r for r in mapping_records if 'model_column' in r]
    evidence['feature_exclusions'] = [r for r in mapping_records if 'excluded_old_columns' in r]
    assert len(evidence['feature_mapping']) == 330
    assert [r['index'] for r in evidence['feature_mapping']] == list(range(330))
    sources = [p / name for name in ['test_predictions.parquet', 'test_daily_metrics.parquet', 'per_round_metrics.parquet', 'resource_samples.parquet', 'effective_parameters.json', 'feature_mapping_330.json', 'timing_resource_summary.json']]
    evidence['source_files'] = [{'name': v.name, 'bytes': v.stat().st_size, 'sha256': digest(v)} for v in sources]
    out = ROOT / 'content/assets/model-report-2026-09-18'
    (out / 'figures').mkdir(parents=True, exist_ok=True)
    data = json.dumps(json_safe(evidence), ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    (out / 'report-data.json').write_text(data, encoding='utf-8')

    plots = {}

    def publish(key, name, fig, caption):
        svg = rc.render(fig, title_of(key, name), key, png_path=out / 'figures' / f'{key}.png')
        (out / 'figures' / f'{key}.svg').write_text(svg, encoding='utf-8')
        plots[key] = (name, svg, caption)

    # 01 — the frozen split, showing the fourteen folds this timing run never touched.
    fig, ax = rc.figure((11.4, 5.6))
    for f in folds:
        y = 16 - f['fold']
        done = f['fold'] == 15
        ax.barh(y, f['train_days'], left=0, height=.62, color=TEAL if done else '#cfdcd7')
        ax.barh(y, f['validation_days'], left=f['train_days'], height=.62, color=RUST if done else '#e3cdc2')
        ax.text(-10, y, f"折 {f['fold']}", ha='right', va='center', fontsize=10.5, color=rc.INK if done else GRAY)
        ax.text(f['train_days'] + f['validation_days'] + 10, y, f"{f['month']}　{f['validation_days']} 日",
                ha='left', va='center', fontsize=10.5, color=rc.INK if done else GRAY)
    ax.barh(0, 176, left=425, height=.62, color=BLUE)
    ax.text(-10, 0, 'test', ha='right', va='center', fontsize=10.5)
    ax.text(425 + 176 + 10, 0, '2025-10-09 — 2026-06-30　176 日', ha='left', va='center', fontsize=10.5)
    ax.axvline(len(seed_dates), color=rc.SPINE, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(len(seed_dates), 16.2, f'2024H1 起始训练 {len(seed_dates)} 日', ha='center', va='bottom', fontsize=10.5, color=GRAY)
    ax.set_xlim(-110, 980)
    ax.set_ylim(-1.0, 17.2)
    ax.set_xlabel('累计交易日')
    ax.set_xticks(list(range(0, 701, 100)))
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    rc.style_axes(ax, grid='x')
    ax.legend(handles=[legend_patch(TEAL, '本次已跑：训练'), legend_patch(RUST, '本次已跑：validation'),
                       legend_patch('#cfdcd7', '尚未运行的 14 折'), legend_patch(BLUE, 'test（一次性）')],
              ncol=4, loc='lower center', bbox_to_anchor=(.5, -.26))
    publish('split', '15 折扩张验证：本次只跑了第 15 折', fig,
            f'冻结的研究日历：2024H1 的 {len(seed_dates)} 日作为起始训练，其后逐自然月扩张验证，2024-07 — 2025-09 共 15 折、{oof_days} 个 validation 交易日；test 为 2025-10-09 — 2026-06-30 的 176 日，425 : 176 即约 7 : 3。本次计时试验按要求只运行最后一折，前 14 折没有运行。')

    iterations = curve.iteration.to_numpy()
    fig, ax = rc.figure((11.4, 4.6))
    for values, color, name in [(curve.long_short_sharpe, TEAL, '多空各 10%'), (curve.pure_long_sharpe, RUST, '纯多 20%'), (curve.pure_short_sharpe, BLUE, '纯空 20%')]:
        ax.plot(iterations, values, color=color, linewidth=1.5, label=name)
    ax.axvline(659, color=rc.INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate('第 659 轮', xy=(659, 1), xytext=(6, -6), xycoords=('data', 'axes fraction'),
                textcoords='offset points', ha='left', va='top', fontsize=10.5, color=rc.INK)
    ax.set_xlabel('训练轮数')
    ax.set_ylabel('validation 年化毛 Sharpe')
    ax.set_xlim(0, 1000)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    rc.nice_ticks(ax, 'x')
    ax.legend(ncol=3, loc='lower center', bbox_to_anchor=(.5, 1.0))
    publish('validation-sharpe', 'validation：按多空 Sharpe 选择 659 轮', fig,
            '完整训练 1000 轮，无 early stopping。竖线只由 validation 多空 Sharpe 确定；不在 test 上选轮。这条曲线只来自第 15 折的 22 个交易日，却要在 1000 个候选轮次中取峰值。')

    fig, ax = rc.figure((5.6, 4.0))
    ax.plot(iterations, curve.validation_mean_rank_ic, color=TEAL, linewidth=1.5)
    ax.axvline(659, color=rc.INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_xlabel('训练轮数')
    ax.set_ylabel('validation 日均 RankIC')
    ax.set_xlim(0, 1000)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    rc.nice_ticks(ax, 'x', count=5)
    publish('validation-ic', 'validation：RankIC 的训练路径', fig,
            '第 659 轮为 0.016604；第 1000 轮为 0.014269。单月路径不构成最终参数选择的充分证据。')

    fig, ax = rc.figure((5.6, 4.0))
    ax.plot(iterations, curve.validation_daily_equal_mse, color=BLUE, linewidth=1.5)
    ax.axvline(659, color=rc.INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_xlabel('训练轮数')
    ax.set_ylabel('标准化目标按日等权 MSE')
    ax.set_xlim(0, 1000)
    rc.style_axes(ax)
    rc.nice_ticks(ax)
    rc.nice_ticks(ax, 'x', count=5)
    publish('validation-mse', 'validation：标准化目标的 MSE', fig,
            'L2 是训练目标；选轮指标为组合 Sharpe。二者不必在同一轮达到最优。MSE 不以 bp 为单位。')

    x = np.arange(len(dates))
    ticks = [i for i, d in enumerate(dates) if i == 0 or dates[i - 1][:7] != d[:7]]
    month_labels = [dates[i][:7] for i in ticks]
    fig, ax = rc.figure((11.4, 4.6))
    for key, name, color, mult in [('long_short_return', '多空：每腿 50%', TEAL, .5), ('pure_long_return', '纯多 20%', RUST, 1), ('pure_short_return', '纯空 20%', BLUE, 1)]:
        ax.plot(x, (np.cumprod(1 + daily[key] * mult) - 1) * 100, color=color, linewidth=1.8, label=name)
    ax.set_xticks(ticks)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel('累计毛收益 %')
    ax.set_xlim(0, len(dates) - 1)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    ax.legend(ncol=3, loc='upper left')
    publish('test-cumulative', 'test：统一总名义敞口后的机械累计收益', fig,
            '多空每日收益先除以 2，再连乘；纯多、纯空按单腿 100%。这是毛收益序列的机械复合，不含现金、保证金、费用及可成交约束，不是账户净值。')

    monthly = pd.DataFrame(summary['monthly_metrics'])
    fig, ax = rc.figure((11.4, 4.6))
    pos = np.arange(len(monthly))
    for i, (column, name, color) in enumerate([('long_short_sharpe', '多空各 10%', TEAL), ('pure_long_sharpe', '纯多 20%', RUST), ('pure_short_sharpe', '纯空 20%', BLUE)]):
        ax.bar(pos + (i - 1) * .27, monthly[column], width=.26, color=color, label=name)
    ax.set_xticks(pos)
    ax.set_xticklabels(monthly.month)
    ax.set_ylabel('月内日收益年化 Sharpe')
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    ax.legend(ncol=3, loc='upper right')
    publish('monthly', 'test：月度 Sharpe 并不均匀', fig,
            '各月只有 14–23 个交易日，短样本年化数值不稳定；2025-11 的高值不代表全年可持续。')

    fig, ax = rc.figure((5.6, 4.2))
    ax.scatter(daily.rank_ic, daily.long_short_return * 1e4, s=20, color=TEAL, alpha=.55, edgecolors='none')
    grid = np.array([daily.rank_ic.min(), daily.rank_ic.max()])
    ax.plot(grid, np.polyval(np.polyfit(daily.rank_ic, daily.long_short_return * 1e4, 1), grid), color=RUST, linewidth=1.4)
    ax.axvline(0, color=rc.SPINE, linewidth=1.0)
    ax.set_xlabel('当日 RankIC')
    ax.set_ylabel('当日多空收益 bp')
    rc.style_axes(ax, grid='both', zero_line=True)
    rc.nice_ticks(ax)
    rc.nice_ticks(ax, 'x', count=5)
    publish('ic-scatter', '同一天的 RankIC 与多空收益', fig,
            f'逐日相关系数 {extra["daily_ic_ls_corr"]:.3f}。相关性强不等于二者成固定比例；收益截距、波动和尾部形状仍会改变 Sharpe。')

    fig, ax = rc.figure((11.4, 4.5))
    quadrant_values = [row['cumulative_return_sum'] * 1e4 for row in quadrants]
    quadrant_labels = [row['label'] + f"\n{row['days']} 天" for row in quadrants]
    bars = ax.bar(np.arange(4), quadrant_values,
                  color=[TEAL if value >= 0 else RUST for value in quadrant_values], width=.64)
    for bar, value in zip(bars, quadrant_values):
        ax.annotate(f'{value:,.0f}bp', xy=(bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 6 if value >= 0 else -15), textcoords='offset points',
                    ha='center', fontsize=10.5)
    ax.set_xticks(np.arange(4))
    ax.set_xticklabels(quadrant_labels)
    ax.set_ylabel('该类日期的多空日收益之和 bp')
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    publish('quadrants', 'RankIC 正负与组合盈亏的四种日期', fig,
            '105 天同时出现 RankIC≥0、组合盈利，贡献 2,850bp；RankIC<0 但组合盈利的 22 天贡献 213bp。'
            '该图使用日收益直接求和，只用于归因，不是复利账户收益。')

    fig, ax = rc.figure((5.6, 4.2))
    ax.bar(x, daily.rank_ic, width=1.0, color=GRAY, alpha=.5)
    ax.plot(x, daily.rank_ic.rolling(20).mean(), color=TEAL, linewidth=1.8, label='20 日滚动均值')
    ax.axhline(total_ic, color=RUST, linewidth=1.2, linestyle=(0, (4, 3)), label=f'全期日均 {total_ic:.4f}')
    ax.set_xticks(ticks[::2])
    ax.set_xticklabels(month_labels[::2])
    ax.set_ylabel('日度 RankIC')
    ax.set_xlim(0, len(dates) - 1)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    ax.legend(loc='upper left')
    publish('daily-ic', 'RankIC 每天有多稳定', fig,
            f'日均 0.02204，日标准差 0.07229；正值日占 {extra["rank_ic_positive_fraction"]:.1%}。年化 ICIR 为 {extra["ic_ir"]:.2f}，不是组合 Sharpe。')

    d = np.arange(1, 11)
    fig, ax = rc.figure((11.4, 5.0))
    ax.errorbar(d, groupstats['mean'] * 1e4, yerr=1.96 * groupstats['nw_se_bp'], fmt='o', color=TEAL,
                markersize=6, capsize=4, elinewidth=1.4, label='日均组平均收益 ± 95% NW 区间')
    ax.plot(d, groupstats['median'] * 1e4, marker='s', markersize=5, linestyle='none', color=RUST, label='日均组中位收益')
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_xlabel('模型分数由低到高 →')
    ax.set_ylabel('收益 bp')
    ax.set_xlim(.4, 10.6)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    ax.legend(ncol=2, loc='upper left')
    rc.annotate_traded(ax, rc.TRADED_ROWS)
    publish('deciles', '十分组的日均收益与 95% 区间', fig,
            '每日在 rank_base 内按分数平均秩分十组，同分同组；先算每组均值/中位数，再对日期等权。误差棒是日均收益的 Newey-West 标准误（Bartlett 核，lag 4）乘 1.96，衡量均值估计精度，不是个股收益范围。本图不做封板过滤，故 D10 与正式多头 10% 的 10.79bp 略有不同。')

    fig, ax = rc.figure((5.6, 4.2))
    ax.bar(d, groupstats['std'] * 1e4, color=BLUE, width=.66)
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_ylabel('个股收益截面标准差 bp')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    publish('dispersion', '两端的个股收益分布更宽', fig,
            '这里是组内个股收益的截面标准差，再对日期取平均；不是组组合每日收益的时间序列波动。二者不可混用。')

    fig, ax = rc.figure((5.6, 4.2))
    ax.bar(d, groupstats['excess_sharpe'], color=[RUST if v < 0 else TEAL for v in groupstats['excess_sharpe']], width=.66)
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_ylabel('超额收益年化 Sharpe')
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    publish('decile-excess', '分组相对全体等权的收益', fig,
            '全体等权基准使用同一天 rank_base 内有有效标签的股票。D1 负值表示跑输基准；不等于裸空 D1 的收益。')

    shown = sorted((pool_by_key[k] for k in ['all', 'middle', 'short', 'long', 'traded', 'long_short']),
                   key=lambda row: row['mean_rank_ic'])
    palette = {'all': GRAY, 'middle': '#cfdcd7', 'short': BLUE, 'long': TEAL, 'traded': SAND, 'long_short': RUST}
    fig, ax = rc.figure((11.4, 4.6))
    pos = np.arange(len(shown))
    ax.barh(pos, [row['mean_rank_ic'] for row in shown], height=.62,
            color=[palette[row['key']] for row in shown],
            xerr=[1.96 * row['nw_se'] for row in shown], capsize=5,
            error_kw=dict(elinewidth=1.3, ecolor=rc.INK))
    for i, row in enumerate(shown):
        ax.annotate(f'{row["mean_rank_ic"]:.5f}　ICIR {row["ic_ir"]:.2f}',
                    xy=(row['mean_rank_ic'] + 1.96 * row['nw_se'], i), xytext=(8, 0),
                    textcoords='offset points', va='center', fontsize=10.5)
    ax.axvline(total_ic, color=rc.INK, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.set_yticks(pos)
    ax.set_yticklabels([f"{row['label']}　{row['mean_count']:,.0f} 只" for row in shown])
    ax.set_xlabel('日均 RankIC')
    ax.set_xlim(0, max(row['mean_rank_ic'] + 1.96 * row['nw_se'] for row in shown) * 1.45)
    rc.style_axes(ax, grid='x')
    rc.nice_ticks(ax, 'x')
    publish('subset-ic', '只看真正交易的那几组，RankIC 是多少', fig,
            f'把横截面限制到该组合实际排序的分组，再重新排名算 Spearman，口径与全体那个 {total_ic:.4f} 完全一致；虚线是全体 10 组的水平。'
            f'多空实际交易的 D1∪D10 为 {pool_by_key["long_short"]["mean_rank_ic"]:.5f}，年化 ICIR {pool_by_key["long_short"]["ic_ir"]:.2f}。'
            '误差棒为日均值的 Newey-West 标准误乘 1.96。去掉中段会把分数范围拉开，本身就会抬高秩相关，这一层机械效应未排除。')

    fig, ax = rc.figure((11.4, 5.0))
    share = groupstats['rank_ic_contribution']
    bars = ax.bar(d, share, color='#cfdcd7', width=.66)
    for k in (1, 2):
        bars[k - 1].set_color(BLUE)
    for k in (9, 10):
        bars[k - 1].set_color(TEAL)
    for k, value in zip(d, share):
        ax.annotate(f'{value / total_ic:.0%}', xy=(k, value), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=10.5)
    ax.axhline(total_ic / 10, color=RUST, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.annotate(f'十组均摊的水平 {total_ic / 10:.5f}', xy=(5.5, total_ic / 10), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=10.5, color=RUST)
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_xlabel('模型分数由低到高 →')
    ax.set_ylabel('对日均 RankIC 的贡献')
    ax.set_xlim(.4, 10.6)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    rc.annotate_traded(ax, rc.TRADED_ROWS)
    publish('ic-contribution', '每一组贡献了多少 RankIC', fig,
            f'把每天的 Spearman 相关按分数分组拆开：十组之和精确等于当天 RankIC，再对日期等权。最低与最高两组合计占 {tail_share:.0%}，策略从不碰的中间六组（D3–D8，占股票数 60%）只占 {middle_share:.0%}，却按全体约 2,875 只股票摊薄了平均值。这是已打开 test 后的分解，不是模型改动依据。')

    fig, ax = rc.figure((11.4, 4.3))
    rank_parts = [rank_decomposition['between_deciles'], rank_decomposition['within_deciles']]
    rank_labels = ['十分组之间', '十分组内部']
    bars = ax.bar(np.arange(2), rank_parts, color=[TEAL, BLUE], width=.58)
    for bar, value in zip(bars, rank_parts):
        ax.annotate(f'{value:.5f}\n{value / rank_decomposition["total"]:.1%}',
                    xy=(bar.get_x() + bar.get_width() / 2, value), xytext=(0, 6),
                    textcoords='offset points', ha='center', fontsize=10.5)
    ax.axhline(rank_decomposition['total'], color=RUST, linewidth=1.2, linestyle=(0, (4, 3)),
               label=f'全体 RankIC {rank_decomposition["total"]:.5f}')
    ax.set_xticks(np.arange(2))
    ax.set_xticklabels(rank_labels)
    ax.set_ylabel('对全体日均 RankIC 的贡献')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    ax.legend(loc='upper right')
    publish('rank-decomposition', '全体 RankIC：组间位置与组内细排的严格分解', fig,
            f'保持全体股票的原始秩不变，用协方差恒等式逐日分解。组间贡献 '
            f'{rank_decomposition["between_share"]:.1%}，组内贡献 {rank_decomposition["within_share"]:.1%}；'
            '两项每天精确加总为当日 RankIC。')

    fig, ax = rc.figure((11.4, 4.4))
    inner_values = groupstats['inner_rank_ic']
    ax.bar(d, inner_values, color=[RUST if v < 0 else TEAL for v in inner_values], width=.66)
    ax.axhline(total_ic, color=rc.INK, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.annotate(f'全体 {total_ic:.4f}', xy=(10.55, total_ic), xytext=(0, 5), textcoords='offset points', ha='right', fontsize=10.5)
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_ylabel('组内 RankIC')
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    publish('inner-ic', '每一组内部还剩多少排序信息', fig,
            '只在该组内部重新排名再算相关。D9 为负，说明模型在这一组内部的细分顺序已经是噪声；D10 有用靠的是整组相对其他组的位置，不是组内谁更靠前。范围收窄本身也会降低相关，不能据此断言中间股票完全没有信息。')

    fig, ax = rc.figure((11.4, 4.4))
    pos = np.arange(3)
    ax.bar(pos - .18, [daily.long10.mean() * 1e4, daily.short10.mean() * 1e4, daily.long_short_return.mean() * 1e4], width=.34, color=TEAL, label='日均收益 bp')
    ax.bar(pos + .18, [daily.long10.std() * 1e4, daily.short10.std() * 1e4, daily.long_short_return.std() * 1e4], width=.34, color=RUST, label='每日收益标准差 bp')
    ax.set_xticks(pos)
    ax.set_xticklabels(['多头最高 10%', '空头最低 10%', '多空各 10%'])
    ax.set_ylabel('bp')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    ax.legend(loc='upper left')
    publish('legs', '多空相减抵消部分共同波动', fig,
            '两篮子原始收益的相关系数为 0.7354。相减后波动为 28.29bp；空头一行已将标的收益取负。该图多空按每腿 100% 的原定义展示。')

    fig, ax = rc.figure((11.4, 4.4))
    variance_values = [
        variance_decomposition['long_variance_bp2'],
        variance_decomposition['short_variance_bp2'],
        variance_decomposition['minus_two_covariance_bp2'],
        variance_decomposition['long_short_variance_bp2'],
    ]
    variance_labels = ['多头方差', '空头标的方差', '−2 × 协方差', '多空方差']
    bars = ax.bar(np.arange(4), variance_values, color=[TEAL, BLUE, RUST, SAND], width=.64)
    for bar, value in zip(bars, variance_values):
        ax.annotate(f'{value:,.0f}', xy=(bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 6 if value >= 0 else -15), textcoords='offset points',
                    ha='center', fontsize=10.5)
    ax.set_xticks(np.arange(4))
    ax.set_xticklabels(variance_labels)
    ax.set_ylabel('日收益方差 bp²')
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    publish('variance-decomposition', '28.29bp 日波动是怎样形成的', fig,
            f'两腿标的收益相关 {variance_decomposition["underlying_leg_correlation"]:.3f}；协方差项抵消了两腿方差和的 '
            f'{variance_decomposition["variance_offset_share"]:.1%}。若只作“协方差为零”的算术对照，日波动为 '
            f'{variance_decomposition["zero_covariance_std_bp"]:.2f}bp、Sharpe 为 {variance_decomposition["zero_covariance_sharpe"]:.2f}；'
            '这不是可实现的替代策略。')

    fig, ax = rc.figure((11.4, 4.6))
    fractions = np.array([row['tail_fraction'] * 100 for row in breadth])
    width = 1.7
    ax.bar(fractions - width / 2, [row['mean_return_bp'] for row in breadth], width=width,
           color=TEAL, label='日均多空收益 bp')
    ax.bar(fractions + width / 2, [row['std_return_bp'] for row in breadth], width=width,
           color=BLUE, label='日波动 bp')
    ax2 = ax.twinx()
    ax2.plot(fractions, [row['sharpe'] for row in breadth], color=RUST, marker='o',
             linewidth=1.7, label='年化毛 Sharpe')
    ax.set_xticks(fractions)
    ax.set_xticklabels([f'两端各 {value:.0f}%' for value in fractions])
    ax.set_ylabel('bp')
    ax2.set_ylabel('Sharpe')
    rc.style_axes(ax)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    rc.nice_ticks(ax, from_zero=True)
    rc.nice_ticks(ax2, from_zero=True)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles1 + handles2, labels1 + labels2, ncol=3, loc='upper right')
    publish('tail-breadth', '两端持仓从 5% 扩到 30%，结果是否消失', fig,
            '固定当前模型和 test，不重新选比例。两端各 5% / 10% / 20% / 30% 的毛 Sharpe 分别为 '
            + ' / '.join(f'{row["sharpe"]:.2f}' for row in breadth)
            + '。5% 到 30% 都为正，说明结果不只依赖一个很窄的切点；这仍是 test 打开后的敏感性诊断。')

    fig, ax = rc.figure((11.4, 4.4))
    concentration_counts = [row['top_positive_stockdays'] for row in concentration]
    concentration_shares = [row['share_of_net_cumulative_return'] * 100 for row in concentration]
    bars = ax.bar(np.arange(len(concentration)), concentration_shares, color=TEAL, width=.64)
    for bar, value in zip(bars, concentration_shares):
        ax.annotate(f'{value:.2f}%', xy=(bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 5), textcoords='offset points', ha='center', fontsize=10.5)
    ax.set_xticks(np.arange(len(concentration)))
    ax.set_xticklabels([f'前 {count}' for count in concentration_counts])
    ax.set_ylabel('占 176 日多空收益日度和的比例')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    publish('stock-concentration', '最大的股票日有没有撑起全部结果', fig,
            f'最大单一正贡献股票日占 {concentration_summary["largest_positive_stockday_share"]:.2%}，'
            f'前 10 个合计占 {concentration_summary["top_10_positive_stockdays_share"]:.2%}。'
            '分母是 176 日多空日收益之和；这里只累计正贡献，因此不是可加总到 100% 的归因瀑布图。')

    fig, ax = rc.figure((11.4, 5.0))
    ax.bar(d - .17, groupstats['own_sharpe'], width=.32, color=SAND, label='该组自身收益年化 Sharpe')
    ax.bar(d + .17, groupstats['excess_sharpe'], width=.32, color=TEAL, label='相对全体等权的超额 Sharpe')
    ax.set_xticks(d)
    ax.set_xticklabels(DECILES)
    ax.set_xlabel('模型分数由低到高 →')
    ax.set_ylabel('年化毛 Sharpe')
    ax.set_xlim(.4, 10.6)
    rc.style_axes(ax, zero_line=True)
    rc.nice_ticks(ax)
    ax.legend(ncol=2, loc='upper left')
    rc.annotate_traded(ax, rc.TRADED_ROWS)
    publish('decile-sharpe', '每一组的年化 Sharpe，与策略实际交易的组', fig,
            f'组自身 Sharpe 用该组每日等权收益的时间序列计算。三个正式组合都只碰两端：纯多买 D9–D10、纯空卖 D1–D2、多空买 D10 卖 D1。用这十组反推为 {reconstructed["pure_long"]:.2f} / {reconstructed["pure_short"]:.2f} / {reconstructed["long_short"]:.2f}，与正式口径的 3.01 / 0.58 / 7.30 只差方向封板过滤。')

    stress_labels = ['原始结果', '取消封板过滤', '缺失标签按 0 计', '个股收益压到 ±1%', '剔除每腿极端 1%', '移除最好 10 个交易日']
    stress = [7.300545039, independent['return_series']['ls_ungated']['sharpe'], dist['diagnostics']['zero_missing_ls']['sharpe'], independent['return_series']['ls_winsor100bp']['sharpe'], dist['diagnostics']['trim_abs_1pct_ls']['sharpe'], 6.21575]
    fig, ax = rc.figure((5.8, 4.4))
    y = np.arange(len(stress))[::-1]
    ax.barh(y, stress, color=[TEAL] + [BLUE] * 5, height=.6)
    for yy, value in zip(y, stress):
        ax.annotate(f'{value:.2f}', xy=(value, yy), xytext=(6, 0), textcoords='offset points', va='center', fontsize=10.5)
    ax.set_yticks(y)
    ax.set_yticklabels(stress_labels)
    ax.set_xlabel('多空年化毛 Sharpe')
    rc.style_axes(ax, grid='x')
    rc.nice_ticks(ax, 'x')
    ax.set_xlim(0, max(stress) * 1.18)
    publish('sensitivity', '排查封板、缺失标签和尾部贡献', fig,
            '同一组已保存预测的事后敏感性分析，不是新模型或可交易选股规则；最后一项显示保留证据中的四舍五入值。')

    fig, ax = rc.figure((5.8, 4.4))
    values = [extra['market_sharpe'], extra['long_excess_sharpe'], extra['short_excess_sharpe']]
    ax.bar(np.arange(3), values, color=[GRAY, TEAL, BLUE], width=.6)
    for i, value in enumerate(values):
        ax.annotate(f'{value:.2f}', xy=(i, value), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=10.5)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(['全体等权', '纯多 20% − 全体', '全体 − 最低 20%'])
    ax.set_ylabel('年化毛 Sharpe')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    publish('market', '相对全体等权后，仍有收益差', fig,
            '这是相对基准诊断，不是 beta 中性化。第三项是空头相对基准的超额收益，不能当作纯空本身的 0.576 Sharpe。')

    times = timing['timings_seconds']
    stage_labels = ['读取因子与准备标签', '对齐、标准化、矩阵', 'Dataset 构建与分箱', '训练剩余（含框架）', '逐轮评价回调', '预测核对与保存', '绘图与报告']
    stage_values = [times['data_read_and_label_prepare'], times['alignment_standardization_matrix'], times['lightgbm_dataset_construct_and_binning'], times['train_call_minus_evaluation_including_framework_overhead'], times['train_internal_per_round_evaluation'], times['post_train_prediction_verification'] + times['model_and_result_save'], times['plot_and_report_seconds']]
    fig, ax = rc.figure((11.4, 4.4))
    y = np.arange(len(stage_values))[::-1]
    ax.barh(y, stage_values, color=[TEAL] + [BLUE] * 6, height=.6)
    for yy, value in zip(y, stage_values):
        ax.annotate(f'{value:,.2f}', xy=(value, yy), xytext=(6, 0), textcoords='offset points', va='center', fontsize=10.5)
    ax.set_yticks(y)
    ax.set_yticklabels(stage_labels)
    ax.set_xlabel('墙钟秒')
    rc.style_axes(ax, grid='x')
    rc.nice_ticks(ax, 'x')
    ax.set_xlim(0, max(stage_values) * 1.14)
    publish('timing', '耗时主要在输入与标签准备', fig,
            '训练剩余 52.47 秒仍包含框架开销，不叫纯算法时间。阶段和整体之间还含少量初始化、调度及统计开销。')

    elapsed = (resources.monotonic_seconds - resources.monotonic_seconds.iloc[0]).to_numpy()
    fig, ax = rc.figure((5.6, 4.2))
    for column, name, color in [('task_memory_current', '任务 cgroup', TEAL), ('process_tree_rss', '进程树 RSS', RUST), ('task_memory_file', '文件缓存', BLUE)]:
        ax.plot(elapsed, resources[column] / 2 ** 30, color=color, linewidth=1.5, label=name)
    ax.set_xlabel('业务启动后秒')
    ax.set_ylabel('GiB')
    ax.set_xlim(0, elapsed.max())
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    ax.legend(loc='upper left')
    publish('memory', '全流程内存轨迹', fig,
            'cgroup 峰值 13.14GiB；RSS 与 cgroup 内存不是同一口径，不能相加。任务上限 60GiB，high=52GiB，swap=0；无新增 OOM 或内存 high 事件。')

    cores = (resources.task_cpu_usage_usec.diff() / resources.monotonic_seconds.diff() / 1e6).to_numpy()
    fig, ax = rc.figure((5.6, 4.2))
    ax.plot(elapsed, cores, color=TEAL, linewidth=1.3)
    ax.axhline(8, color=RUST, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.annotate('num_threads=8', xy=(1, 8), xytext=(-6, 5), xycoords=('axes fraction', 'data'),
                textcoords='offset points', ha='right', fontsize=10.5, color=RUST)
    ax.set_xlabel('业务启动后秒')
    ax.set_ylabel('采样间隔等效核数')
    ax.set_xlim(0, elapsed.max())
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    publish('cpu', 'CPU 使用集中在训练阶段', fig,
            '约每 1 秒采样；训练阶段平均 7.00 核，全流程平均 1.17 核。累计 CPU 配额限流 0.144 秒；一次观察不能证明最优线程数。')

    roundcost = timing['per_100_round_wall_seconds']
    fig, ax = rc.figure((11.4, 4.2))
    values = [r['wall_seconds'] for r in roundcost]
    ax.bar(np.arange(len(values)), values, color=TEAL, width=.66)
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels([str(r['round_end']) for r in roundcost])
    ax.set_xlabel('轮数终点')
    ax.set_ylabel('每 100 轮墙钟秒')
    rc.style_axes(ax)
    rc.nice_ticks(ax, from_zero=True)
    publish('round-speed', '每 100 轮的墙钟耗时', fig,
            '首 100 轮 7.61 秒，后续约 6.23–6.78 秒；没有观察到随轮数不断增加的重复预测开销。')

    rendered = {key: figure(key, title_of(key, name), svg, caption)
                for key, (name, svg, caption) in plots.items()}
    assert set(rendered) == set(FIGURE_ORDER), 'figure set must match the template'

    case_cards = []
    for case in cases:
        source_items = ''.join(
            f'<li><a href="{html.escape(source["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{html.escape(source["label"])}</a></li>'
            for source in case['sources']
        )
        contribution_class = ' loss' if case['contribution'] < 0 else ''
        leg_label = '多头' if case['leg'] == 'long' else '空头'
        case_cards.append(
            f'<article class="case{contribution_class}"><h3>{html.escape(case["name_at_event"])} '
            f'<span class="small">{case["code"]} · {case["date"]}</span></h3>'
            f'<div class="metric">{leg_label}贡献 {case["contribution"] * 1e4:+.2f}bp</div>'
            f'<p>模型分数 {case["score"]:.4f}；09:35—09:45 原始收益 {case["raw_return"]:+.2%}。</p>'
            f'<p><strong>已核对的背景：</strong>{html.escape(case["observed_context"])}</p>'
            f'<p><strong>本页解释：</strong>{html.escape(case["interpretation"])}</p>'
            f'<ul>{source_items}</ul></article>'
        )
    case_studies_html = '<div class="case-grid">' + ''.join(case_cards) + '</div>'

    top_stockday_rows = []
    for direction, frame in (('正贡献', top_positive.head(6)), ('负贡献', top_negative.head(6))):
        for _, row in frame.iterrows():
            top_stockday_rows.append([
                direction, row.date, f'{row["name"]}（{row.code}）',
                '多头' if row.leg == 'long' else '空头', f'{row.raw_return:+.2%}',
                f'{row.contribution * 1e4:+.2f}', f'{row.score:.4f}',
            ])
    aggregate_stock_rows = []
    for direction, frame in (('累计正贡献', aggregate_positive), ('累计负贡献', aggregate_negative)):
        for _, row in frame.iterrows():
            aggregate_stock_rows.append([
                direction, f'{row["name"]}（{row.code}）', f'{row.cumulative_contribution * 1e4:+.2f}',
                int(row.selected_days), int(row.long_days), int(row.short_days),
            ])

    replacement = {
        **rendered,
        'DATA': data.replace('</', '<\\/'),
        'PARAMETERS': html.escape(json.dumps(params, ensure_ascii=False, indent=2)),
        'SEED_DAYS': str(len(seed_dates)),
        'OOF_DAYS': str(oof_days),
        'TRADED_SHARE': f'{traded_share:.0%}',
        'MIDDLE_SHARE': f'{middle_share:.0%}',
        'TAIL_SHARE': f'{tail_share:.0%}',
        'BETWEEN_SHARE': f'{rank_decomposition["between_share"]:.1%}',
        'WITHIN_SHARE': f'{rank_decomposition["within_share"]:.1%}',
        'TOP_STOCK_SHARE': f'{concentration_summary["largest_positive_stock_share"]:.2%}',
        'POOL_ALL': f'{pool_by_key["all"]["mean_rank_ic"]:.5f}',
        'POOL_LS': f'{pool_by_key["long_short"]["mean_rank_ic"]:.5f}',
        'POOL_LS_IR': f'{pool_by_key["long_short"]["ic_ir"]:.2f}',
        'POOL_MIDDLE': f'{pool_by_key["middle"]["mean_rank_ic"]:.5f}',
        'POOL_CONTROL': f'{pool_by_key["spaced_control"]["mean_rank_ic"]:.5f}',
        'POOL_TABLE': table(['池子', '包含的分组', '日均 RankIC', '日标准差', '正值日', '年化 ICIR', '日均只数'],
                            [[row['label'], decile_span(row['deciles']),
                              f'{row["mean_rank_ic"]:.5f}', f'{row["std_rank_ic"]:.5f}',
                              f'{row["positive_fraction"]:.1%}', f'{row["ic_ir"]:.2f}',
                              f'{row["mean_count"]:,.0f}'] for row in pools]),
        'INNER_TABLE': table(['组', '组内日均 RankIC', '日标准差', '正值日', '年化 ICIR', '日均只数'],
                             [[f'D{i}', f'{r["inner_rank_ic"]:.5f}', f'{r["inner_rank_ic_std"]:.5f}',
                               f'{r["inner_rank_ic_positive"]:.1%}', f'{r["inner_rank_ic_ir"]:.2f}',
                               f'{r["count"]:,.1f}'] for i, r in groupstats.iterrows()]),
        'RECON_LONG': f'{reconstructed["pure_long"]:.2f}',
        'RECON_SHORT': f'{reconstructed["pure_short"]:.2f}',
        'RECON_LS': f'{reconstructed["long_short"]:.2f}',
        'FOLD_TABLE': table(['折', 'train 日数', 'train 截止', 'validation 月', 'validation 日数', '本次'],
                            [[f['fold'], f['train_days'], f['train_end'], f['month'], f['validation_days'],
                              '已运行' if f['fold'] == 15 else '未运行'] for f in folds]),
        'CONTRIBUTION_TABLE': table(['组', '日均收益 bp', '±95% NW bp', '对 RankIC 的贡献', '占比', '组内 RankIC', '组自身 Sharpe', '超额 Sharpe'],
                                    [[f'D{i}', f'{r["mean"] * 1e4:.2f}', f'{1.96 * r["nw_se_bp"]:.2f}', f'{r["rank_ic_contribution"]:.5f}', f'{r["rank_ic_contribution"] / total_ic:.1%}', f'{r["inner_rank_ic"]:.5f}', f'{r["own_sharpe"]:.2f}', f'{r["excess_sharpe"]:.2f}'] for i, r in groupstats.iterrows()]),
        'QUADRANT_TABLE': table(
            ['日期类别', '天数', '日均 RankIC', '日均多空收益 bp', '该类日收益之和 bp'],
            [[row['label'], row['days'], f'{row["mean_rank_ic"]:.5f}', f'{row["mean_return_bp"]:.2f}',
              f'{row["cumulative_return_sum"] * 1e4:,.0f}'] for row in quadrants],
        ),
        'TOP_STOCKDAY_TABLE': table(
            ['类型', '日期', '股票', '方向', '个股原始收益', '贡献 bp', '模型分数'], top_stockday_rows,
        ),
        'AGGREGATE_STOCK_TABLE': table(
            ['类型', '股票', '累计贡献 bp', '入选天数', '多头天数', '空头天数'], aggregate_stock_rows,
        ),
        'CASE_STUDIES': case_studies_html,
        'BOOTSTRAP_TABLE': table(
            ['统计量', '点估计', '移动块 2.5%', '移动块中位数', '移动块 97.5%'],
            [
                ['日均多空毛收益 bp', f'{daily.long_short_return.mean() * 1e4:.2f}',
                 f'{bootstrap["mean_return_quantiles"]["p025"] * 1e4:.2f}',
                 f'{bootstrap["mean_return_quantiles"]["p500"] * 1e4:.2f}',
                 f'{bootstrap["mean_return_quantiles"]["p975"] * 1e4:.2f}'],
                ['年化毛 Sharpe', f'{sharpe(daily.long_short_return):.2f}',
                 f'{bootstrap["sharpe_quantiles"]["p025"]:.2f}',
                 f'{bootstrap["sharpe_quantiles"]["p500"]:.2f}',
                 f'{bootstrap["sharpe_quantiles"]["p975"]:.2f}'],
            ],
        ),
        'MONTH_STABILITY_TABLE': table(
            ['排除月份', '该月天数', '该月占收益日度和', '该月日均收益 bp', '排除后 Sharpe'],
            [[row['month'], row['days'], f'{row["return_sum_share"]:.1%}', f'{row["mean_return_bp"]:.2f}',
              f'{row["leave_one_month_out_sharpe"]:.2f}'] for row in monthly_stability],
        ),
        'EXTRA': table(['指标', 'test 结果'], [['RankIC 均值 / 日标准差', f'{daily.rank_ic.mean():.5f} / {daily.rank_ic.std():.5f}'], ['RankIC 正值日', f'{(daily.rank_ic > 0).sum()} / 176（{extra["rank_ic_positive_fraction"]:.1%}）'], ['年化 ICIR', f'{extra["ic_ir"]:.3f}'], ['日均 Pearson IC', f'{extra["mean_pearson_ic"]:.5f}'], ['每日平均进场可选股票', f'{extra["mean_rank_base"]:,.1f}'], ['交易到的四组对 RankIC 的贡献占比', f'{traded_share:.1%}'], ['未交易的中间六组占比', f'{middle_share:.1%}'], ['纯多 20% 相对基准 Sharpe', f'{extra["long_excess_sharpe"]:.3f}'], ['纯空 20% 相对基准 Sharpe', f'{extra["short_excess_sharpe"]:.3f}']]),
        'MONTHLY_TABLE': table(['月份', '天数', 'RankIC', '多空 Sharpe', '纯多 Sharpe', '纯空 Sharpe'], [[m['month'], m['date_count'], f'{m["mean_daily_rank_ic"]:.4f}', f'{m["long_short_sharpe"]:.2f}', f'{m["pure_long_sharpe"]:.2f}', f'{m["pure_short_sharpe"]:.2f}'] for m in summary['monthly_metrics']]),
        'DECILE_TABLE': table(['组', '日均组平均收益 bp', '日均组中位收益 bp', '组内截面标准差 bp', '日均只数'], [[f'D{i}', f'{r["mean"] * 1e4:.2f}', f'{r["median"] * 1e4:.2f}', f'{r["std"] * 1e4:.2f}', f'{r["count"]:,.1f}'] for i, r in groupstats.iterrows()]),
    }
    for key, value in replacement.items():
        report = report.replace('@@' + key + '@@', value)
    assert '@@' not in report, 'unfilled report token'
    (ROOT / 'content/daily/2026-09-18.show.html').write_text(report, encoding='utf-8')
    print(json.dumps(extra, indent=2, ensure_ascii=False))
    print('report_bytes', len(report.encode('utf-8')), 'chart_count', len(plots))


if __name__ == '__main__':
    main()
