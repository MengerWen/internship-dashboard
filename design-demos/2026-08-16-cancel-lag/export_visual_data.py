#!/usr/bin/env python3
"""Derive compact website data from the frozen cancel-lag histograms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


MARKETS = ("sse", "szse")
BIN_MS = 10
MAIN_END_MS = 10_000
PEAK_END_MS = 15_000
HEATMAP_BIN_MS = 50


def _dense_daily(path: Path, end_ms: int) -> tuple[str, np.ndarray, int]:
    frame = pd.read_parquet(path, columns=("date", "lag_bin_ms", "cancel_message_count"))
    date = str(frame["date"].iloc[0])
    total = int(frame["cancel_message_count"].sum())
    dense = np.zeros(end_ms // BIN_MS, dtype=np.int64)
    selected = frame.loc[frame["lag_bin_ms"].lt(end_ms)]
    indices = selected["lag_bin_ms"].to_numpy(dtype=np.int64) // BIN_MS
    dense[indices] = selected["cancel_message_count"].to_numpy(dtype=np.int64)
    return date, dense, total


def _local_baseline(counts: np.ndarray, index: int) -> float:
    outer = 25  # +/-250ms
    inner = 8   # exclude +/-80ms around the candidate
    lo = max(0, index - outer)
    hi = min(len(counts), index + outer + 1)
    values = np.concatenate((counts[lo:max(lo, index - inner)], counts[min(hi, index + inner + 1):hi]))
    if values.size == 0:
        return 1.0
    return max(float(np.median(values)), 1.0)


def _peak_width(counts: np.ndarray, index: int, baseline: float) -> tuple[int, int]:
    threshold = baseline + (float(counts[index]) - baseline) * 0.5
    lo = index
    hi = index
    limit = 50  # never merge structures more than 500ms away
    while lo > max(0, index - limit) and counts[lo - 1] >= threshold:
        lo -= 1
    while hi + 1 < min(len(counts), index + limit + 1) and counts[hi + 1] >= threshold:
        hi += 1
    return lo * BIN_MS, hi * BIN_MS


def _peaks(
    aggregate_counts: np.ndarray,
    daily_counts: list[np.ndarray],
    daily_totals: list[int],
    dates: list[str],
    total_messages: int,
) -> list[dict[str, object]]:
    candidates: list[tuple[float, int, float]] = []
    for index, value in enumerate(aggregate_counts):
        baseline = _local_baseline(aggregate_counts, index)
        lo = max(0, index - 3)
        hi = min(len(aggregate_counts), index + 4)
        if value < aggregate_counts[lo:hi].max() or value < baseline * 2:
            continue
        candidates.append((float(value - baseline), index, baseline))

    selected: list[tuple[int, float]] = []
    for _, index, baseline in sorted(candidates, reverse=True):
        if any(abs(index - chosen) < 12 for chosen, _ in selected):
            continue
        selected.append((index, baseline))
        if len(selected) == 10:
            break

    rows: list[dict[str, object]] = []
    for index, baseline in selected:
        width_start, width_end = _peak_width(aggregate_counts, index, baseline)
        persistent = 0
        monthly: dict[str, list[float]] = {}
        for date, counts, daily_total in zip(dates, daily_counts, daily_totals, strict=True):
            lo = max(0, index - 5)
            hi = min(len(counts), index + 6)
            peak_value = float(counts[lo:hi].max())
            daily_baseline = _local_baseline(counts, index)
            persistent += int(peak_value >= daily_baseline * 2)
            month = date[:7]
            monthly.setdefault(month, []).append(
                peak_value / daily_total * 1_000_000 if daily_total else 0.0
            )
        rows.append(
            {
                "center_ms": index * BIN_MS,
                "half_prominence_interval_ms": [width_start, width_end],
                "daily_average_count": round(float(aggregate_counts[index]) / len(dates), 2),
                "market_share": round(float(aggregate_counts[index]) / total_messages, 8),
                "local_baseline_daily_average": round(baseline / len(dates), 2),
                "local_ratio": round(float(aggregate_counts[index]) / baseline, 2),
                "persistence_days_2x": persistent,
                "persistence_rate_2x": round(persistent / len(dates), 4),
                "monthly_per_million": {
                    month: round(float(np.mean(values)), 3) for month, values in sorted(monthly.items())
                },
            }
        )
    return rows


def build_payload(root: Path) -> dict[str, object]:
    result = json.loads((root / "OPEN5M_CANCEL_LAG_RESULT.json").read_text(encoding="utf-8"))
    market_payload: dict[str, object] = {}
    expected_dates: list[str] | None = None

    for market in MARKETS:
        daily_paths = sorted((root / f"daily/market={market}").glob("date=*.parquet"))
        dates: list[str] = []
        daily_main: list[np.ndarray] = []
        daily_peak: list[np.ndarray] = []
        daily_totals: list[int] = []
        for path in daily_paths:
            date, peak_counts, total = _dense_daily(path, PEAK_END_MS)
            dates.append(date)
            daily_peak.append(peak_counts)
            daily_main.append(peak_counts[: MAIN_END_MS // BIN_MS])
            daily_totals.append(total)
        if expected_dates is None:
            expected_dates = dates
        elif dates != expected_dates:
            raise ValueError("SSE and SZSE daily date grids differ")

        aggregate = pd.read_parquet(root / f"aggregate/delta_t_{market}_10ms.parquet")
        full_counts = aggregate["cancel_message_count"].to_numpy(dtype=np.int64)
        total_messages = int(full_counts.sum())
        main_counts = full_counts[: MAIN_END_MS // BIN_MS]
        peak_counts = full_counts[: PEAK_END_MS // BIN_MS]

        daily_matrix = np.vstack(daily_main)
        totals = np.asarray(daily_totals, dtype=np.float64)
        normalized = (daily_matrix / totals[:, None] * 1_000_000).mean(axis=0)
        heatmap = daily_matrix.reshape(len(dates), -1, HEATMAP_BIN_MS // BIN_MS).sum(axis=2)
        heatmap = heatmap / totals[:, None] * 1_000_000

        months = sorted({date[:7] for date in dates})
        monthly: dict[str, list[float]] = {}
        for month in months:
            mask = np.asarray([date.startswith(month) for date in dates])
            monthly[month] = np.round(daily_matrix[mask].mean(axis=0), 2).tolist()

        market_payload[market] = {
            "total_messages": total_messages,
            "daily_average_10ms_0_10s": np.round(main_counts / len(dates), 2).tolist(),
            "equal_day_per_million_10ms_0_10s": np.round(normalized, 4).tolist(),
            "daily_per_million_50ms_0_10s": np.round(heatmap, 3).tolist(),
            "monthly_daily_average_10ms_0_10s": monthly,
            "daily_totals": daily_totals,
            "peaks_0_15s": _peaks(
                peak_counts, daily_peak, daily_totals, dates, total_messages
            ),
        }

    assert expected_dates is not None
    return {
        "schema_version": "cancel-lag-visual-v2",
        "source": {
            "run_id": result["run_id"],
            "business_revision": result["business_revision"],
            "date_hash": result["date_hash"],
            "universe_hash": result["universe_hash"],
            "start": result["start"],
            "end": result["end"],
            "date_count": len(expected_dates),
        },
        "bin_width_ms": BIN_MS,
        "heatmap_bin_ms": HEATMAP_BIN_MS,
        "dates": expected_dates,
        "markets": market_payload,
        "definitions": {
            "daily_average": "aggregate count at each native 10ms bin divided by 116 accepted trading days",
            "equal_day_per_million": "mean across days of bin count divided by that market-day total matched cancels, times one million",
            "heatmap": "five adjacent native bins combined to 50ms, normalized within each market-day per million matched cancels",
            "peak_baseline": "median aggregate count in +/-250ms excluding +/-80ms around the candidate",
            "peak_persistence": "day counted when the maximum within +/-50ms is at least 2x that day's local baseline",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build_payload(args.root), ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
