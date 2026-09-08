"""独立复算横截面相关，并分解收益幅度、排名与尾部贡献。"""
import numpy as np


def average_ranks(values):
    """稳定排序后给相同原值赋平均秩，秩从 1 开始。"""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind='stable')
    sorted_values = values[order]
    starts = np.r_[0, np.flatnonzero(sorted_values[1:] != sorted_values[:-1]) + 1]
    ends = np.r_[starts[1:], len(values)]
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.repeat((starts + ends + 1) / 2, ends - starts)
    return ranks


def correlation(x, y):
    a, b = np.asarray(x) - np.mean(x), np.asarray(y) - np.mean(y)
    scale = np.sqrt(np.dot(a, a) * np.dot(b, b))
    return float(np.dot(a, b) / scale) if scale else np.nan


def diagnose_day(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    rx, ry = average_ranks(x), average_ranks(y)
    groups = np.ceil(rx / len(rx) * 10).astype(int) - 1
    bounds = np.quantile(y, [.01, .99])
    clipped = np.clip(y, *bounds)
    fields = {k: np.full(10, np.nan) for k in ('rank_pct', 'median_bps', 'winsor_bps', 'tail_bps', 'positive_pct', 'mean_bps')}
    for g in range(10):
        selected = groups == g
        if selected.any():
            fields['rank_pct'][g] = np.mean(ry[selected] / len(y)) * 100
            fields['median_bps'][g] = np.median(y[selected]) * 10000
            fields['winsor_bps'][g] = np.mean(clipped[selected]) * 10000
            fields['tail_bps'][g] = np.mean(y[selected] - clipped[selected]) * 10000
            fields['positive_pct'][g] = np.mean(y[selected] > 0) * 100
            fields['mean_bps'][g] = np.mean(y[selected]) * 10000
    return dict(n=len(x), ic=correlation(x, y), rank=correlation(rx, ry),
                rounded_rank=correlation(average_ranks(np.round(x, 12)), ry),
                rank_x_return=correlation(rx, y), groups=fields)


def fit_ols(x, y):
    """完整成对样本上拟合含截距 OLS；收益保留小数单位。"""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    xc, yc = x - x.mean(), y - y.mean()
    slope = float(np.dot(xc, yc) / np.dot(xc, xc))
    intercept = float(y.mean() - slope * x.mean())
    r = correlation(x, y)
    return dict(n=len(x), slope=slope, intercept=intercept, r=r, r2=r*r,
                rmse=float(np.sqrt(np.mean((yc - slope*xc)**2))),
                x_quantiles=np.quantile(x, [0, .005, .5, .995, 1]),
                y_quantiles=np.quantile(y, [0, .005, .5, .995, 1]))
