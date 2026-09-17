"""Add full-sample distribution, OLS, density plots and daily group diagnostics."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import time

SOURCE = Path('/home/wenjie/.cache/sirui-f40/rawbank-evaluation-20260917-r01')
sys.path.insert(0, str(SOURCE))
import evaluate as base
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from algobench.depth_match_evaluation import ols, QUANTILES

WORK = Path(sys.argv[1])
ENTRIES = base.identities
OFFSETS = np.cumsum([0] + [e['rows'] for e in ENTRIES])


def day_details(index):
    entry = ENTRIES[index]
    day = entry['date']
    key = 'quota/wenjie/' + entry['panel']['path'].split('/home/wenjie/hdd-store/', 1)[1]
    raw = subprocess.check_output(['mc', 'cat', key], timeout=120)
    assert hashlib.sha256(raw).hexdigest() == entry['panel']['file_sha256']
    panel = pq.read_table(io.BytesIO(raw)).to_pandas()
    label_raw = (SOURCE / base.labels[day]['target_path']).read_bytes()
    assert hashlib.sha256(label_raw).hexdigest() == base.labels[day]['source_hash']
    labels = pq.read_table(io.BytesIO(label_raw)).to_pandas()
    for frame in (panel, labels):
        frame['date'] = frame['date'].astype(str)
        frame['code'] = frame['code'].astype(str).str.zfill(6)
    merged = panel[['date', 'code', *base.COLUMNS]].merge(
        labels[['date', 'code', base.LABEL]], on=['date', 'code'],
        how='outer', validate='one_to_one', indicator=True)
    assert merged['_merge'].eq('both').all() and len(merged) == entry['rows']
    xall = merged[base.COLUMNS].to_numpy(float)
    y = merged[base.LABEL].to_numpy(float)
    matrix = np.load(WORK / 'matrix.npy', mmap_mode='r+')
    target = np.load(WORK / 'labels.npy', mmap_mode='r+')
    matrix[OFFSETS[index]:OFFSETS[index + 1]] = xall
    target[OFFSETS[index]:OFFSETS[index + 1]] = y
    diagnostics = np.full((288, 10, 7), np.nan)
    official = np.load(SOURCE / 'days' / (day + '.npz'))['groups'][:, :10]
    for j in range(288):
        valid = np.isfinite(xall[:, j]) & np.isfinite(y)
        x, yy = xall[valid, j], y[valid]
        n = len(yy)
        ids = base.quantile_groups(x, 10) if n else np.empty(0, int)
        ranks = pd.Series(yy).rank(method='average').to_numpy() / n if n else yy
        lo, hi = np.quantile(yy, [.01, .99]) if n else (np.nan, np.nan)
        winsor = np.clip(yy, lo, hi)
        for g in range(10):
            mask = ids == g
            values = yy[mask]
            count = len(values)
            assert count == official[j, g, 0]
            if count:
                mean, win = values.mean(), winsor[mask].mean()
                np.testing.assert_allclose(mean, official[j, g, 1], atol=1e-12, rtol=1e-10)
                diagnostics[j, g] = [count, values.var(ddof=0), ranks[mask].mean(),
                                     np.median(values), win, mean - win, np.mean(values > 0)]
            else:
                diagnostics[j, g, 0] = 0
    np.savez_compressed(WORK / 'days' / (day + '.npz'), diagnostics=diagnostics)
    return day


def density(x, y, bounds):
    xmin, xmax, ymin, ymax = map(float, bounds)
    if xmin == xmax:
        xmax = xmin + 1e-8
    if ymin == ymax:
        ymax = ymin + 1e-8
    counts, _, _ = np.histogram2d(x, y, bins=[128, 96], range=[[xmin, xmax], [ymin, ymax]])
    cells = [[int(a), int(b), int(counts[a, b])] for a, b in zip(*np.nonzero(counts))]
    return dict(bounds=[xmin, xmax, ymin, ymax], bins=[128, 96], cells=cells,
                included=int(counts.sum()), outside=int(len(x) - counts.sum()))


def main():
    start = time.monotonic()
    WORK.mkdir(exist_ok=True)
    (WORK / 'days').mkdir(exist_ok=True)
    matrix = np.lib.format.open_memmap(WORK / 'matrix.npy', mode='w+', dtype='float64', shape=(int(OFFSETS[-1]), 288))
    target = np.lib.format.open_memmap(WORK / 'labels.npy', mode='w+', dtype='float64', shape=(int(OFFSETS[-1]),))
    del matrix, target
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(day_details, i) for i in range(601)}
        for n, future in enumerate(as_completed(futures), 1):
            future.result()
            base.write_json(WORK / 'progress.json', dict(phase='daily_details', completed=n, total=601))
            if n % 25 == 0:
                print('days', n, round(time.monotonic() - start, 1), flush=True)
    matrix = np.load(WORK / 'matrix.npy', mmap_mode='r')
    target = np.load(WORK / 'labels.npy', mmap_mode='r')
    dates = [e['date'] for e in ENTRIES]
    days = np.array([np.load(WORK / 'days' / (d + '.npz'))['diagnostics'] for d in dates])
    periods = base.periods()
    result = {}
    for j, c in enumerate(base.COLUMNS):
        # Materialize one column, rather than sorting the four-GiB matrix in memory.
        x = np.array(matrix[:, j])
        finite = x[np.isfinite(x)]
        paired = np.isfinite(x) & np.isfinite(target)
        xx, yy = x[paired], np.array(target[paired])
        fit = ols(xx, yy)
        assert fit['n'] == len(xx)
        distribution = dict(mean=float(finite.mean()) if len(finite) else np.nan,
                            std=float(finite.std(ddof=1)) if len(finite) > 1 else np.nan,
                            quantiles={str(q): float(np.quantile(finite, q)) if len(finite) else np.nan for q in QUANTILES})
        scatter = {}
        if len(xx):
            scatter['full'] = density(xx, yy, [xx.min(), xx.max(), yy.min(), yy.max()])
            assert scatter['full']['included'] == len(xx) and scatter['full']['outside'] == 0
            scatter['zoom'] = density(xx, yy, [*np.quantile(xx, [.01, .99]), *np.quantile(yy, [.01, .99])])
        summaries = []
        for _, a, b in periods:
            mask = np.array([a <= d <= b for d in dates])
            selected = days[mask, j]
            groups = []
            for g in range(10):
                values = selected[:, g]
                eligible = values[:, 0] > 0
                v = values[eligible]
                means = np.mean(v[:, 1:], axis=0) if len(v) else np.full(6, np.nan)
                groups.append(dict(stock_days=int(v[:, 0].sum()), valid_days=len(v),
                                   typical_within_std=float(np.sqrt(means[0])),
                                   return_percentile=means[1], median_return=means[2],
                                   winsorized_mean=means[3], tail_contribution=means[4], positive_fraction=means[5]))
            summaries.append(groups)
        result[c] = dict(ols=fit, distribution=distribution, scatter=scatter, group_diagnostics=summaries)
        base.write_json(WORK / 'progress.json', dict(phase='full_sample_details', completed=j + 1, total=288))
        if (j + 1) % 24 == 0:
            print('factors', j + 1, round(time.monotonic() - start, 1), flush=True)
    payload = json.dumps(base.json_safe(result), ensure_ascii=False, separators=(',', ':')).encode()
    (WORK / 'details.json.gz').write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    base.write_json(WORK / 'result.json', dict(passed=True, dates=601, columns=288, stock_days=int(OFFSETS[-1]),
                   daily_group_count_and_mean_checks=601 * 288 * 10,
                   full_density_count_checks=288, elapsed_seconds=time.monotonic() - start,
                   original_report_sha256=hashlib.sha256((SOURCE / 'report-data.json.gz').read_bytes()).hexdigest(),
                   details_sha256=hashlib.sha256((WORK / 'details.json.gz').read_bytes()).hexdigest(),
                   script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   group_eligibility='Nonempty daily groups, identical to the original raw-bank evaluation; no return minimum-count change.',
                   density='All finite factor/return pairs enter the full 128x96 histogram; P1/P99 zoom changes axes only; OLS uses all pairs.'))
    base.write_json(WORK / 'progress.json', dict(phase='complete', completed=288, total=288))
    print('COMPLETE', round(time.monotonic() - start, 1), flush=True)


if __name__ == '__main__':
    main()
