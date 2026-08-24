#!/usr/bin/env python3
"""Validate the frozen SZSE cancel-lag analysis before embedding it."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


EXPECTED_PERIOD_DATES = {"2024": 242, "2025": 243, "2026H1": 116}
QUALITY_FAILURE_FIELDS = (
    "orphan_cancel_count",
    "duplicate_order_id_count",
    "negative_lag_count",
    "off_10ms_grid_count",
    "lag_ge_300s_count",
)


def _nonnegative_finite(values: list[object], *, label: str) -> None:
    if not all(
        isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
        for value in values
    ):
        raise ValueError(f"{label} must contain only finite nonnegative numbers")


def validate(payload: dict[str, object]) -> None:
    study = payload["study"]
    if payload.get("schema_version") != "open5m-cancel-lag-szse-history-analysis-v1":
        raise ValueError("unexpected analysis schema")
    expected_study = {
        "market": "szse",
        "start": "2024-01-02",
        "end": "2026-06-30",
        "date_count": 601,
        "computed_date_count": 485,
        "reused_date_count": 116,
    }
    for key, expected in expected_study.items():
        if study.get(key) != expected:
            raise ValueError(f"study.{key} must be {expected!r}")

    periods = payload["periods"]
    if set(periods) != set(EXPECTED_PERIOD_DATES):
        raise ValueError("period set must be 2024, 2025, and 2026H1")
    for period, expected_dates in EXPECTED_PERIOD_DATES.items():
        row = periods[period]
        if row.get("date_count") != expected_dates:
            raise ValueError(f"{period} must contain {expected_dates} dates")
        frequency = row.get("average_daily_frequency_0_10s")
        if not isinstance(frequency, list) or len(frequency) != 1001:
            raise ValueError(f"{period} raw frequency must have 1001 10ms bins")
        _nonnegative_finite(frequency, label=f"{period} raw frequency")

    daily = payload["daily"]
    dates = [row["date"] for row in daily]
    if len(daily) != 601 or dates != sorted(dates) or len(set(dates)) != 601:
        raise ValueError("daily rows must contain 601 unique sorted dates")

    heatmap = payload["heatmap"]
    if heatmap.get("dates") != dates:
        raise ValueError("heatmap dates must match daily dates")
    if heatmap.get("lag_bins_ms") != list(range(0, 10_001, 50)):
        raise ValueError("heatmap must use the frozen 50ms grid")
    rows = heatmap.get("counts")
    if not isinstance(rows, list) or len(rows) != 601:
        raise ValueError("heatmap must contain 601 rows")
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 201:
            raise ValueError(f"heatmap row {index} must contain 201 bins")
        _nonnegative_finite(row, label=f"heatmap row {index}")

    months = payload["months"]
    if len(months) != 30 or [row["month"] for row in months] != sorted(
        row["month"] for row in months
    ):
        raise ValueError("monthly rows must contain 30 sorted months")
    quality = payload["quality"]
    failures = {field: quality.get(field) for field in QUALITY_FAILURE_FIELDS}
    if any(value != 0 for value in failures.values()):
        raise ValueError(f"quality failures are nonzero: {failures}")
    if quality.get("matched_cancel_messages") != payload["overall"].get(
        "cancel_count"
    ):
        raise ValueError("quality and overall cancel totals must agree")
    if sum(periods[label]["cancel_count"] for label in EXPECTED_PERIOD_DATES) != payload[
        "overall"
    ]["cancel_count"]:
        raise ValueError("period cancel totals must conserve the overall total")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.analysis.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("analysis must be a JSON object")
    validate(payload)
    print(f"validated {args.analysis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
