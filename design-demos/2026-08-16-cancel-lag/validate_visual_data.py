#!/usr/bin/env python3
"""Fail closed on malformed or inconsistent cancel-lag website data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.data.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "cancel-lag-visual-v2"
    assert payload["source"]["date_count"] == 116
    assert len(payload["dates"]) == 116
    assert payload["dates"] == sorted(payload["dates"])
    assert payload["bin_width_ms"] == 10
    assert payload["heatmap_bin_ms"] == 50

    expected = {
        "sse": {"total": 265_877_449, "max_ms": 6000, "max_value": 19_410.05},
        "szse": {"total": 296_513_087, "max_ms": 3000, "max_value": 16_543.58},
    }
    for market, contract in expected.items():
        data = payload["markets"][market]
        raw = data["daily_average_10ms_0_10s"]
        normalized = data["equal_day_per_million_10ms_0_10s"]
        heatmap = data["daily_per_million_50ms_0_10s"]
        monthly = data["monthly_daily_average_10ms_0_10s"]
        assert data["total_messages"] == contract["total"]
        assert sum(data["daily_totals"]) == contract["total"]
        assert len(raw) == len(normalized) == 1000
        assert len(heatmap) == 116 and all(len(row) == 200 for row in heatmap)
        assert list(monthly) == [f"2026-{month:02d}" for month in range(1, 7)]
        assert all(len(values) == 1000 for values in monthly.values())
        assert max(raw) == contract["max_value"]
        assert raw.index(max(raw)) * 10 == contract["max_ms"]
        assert all(value >= 0 for value in raw)
        assert all(value >= 0 for value in normalized)
        assert all(value >= 0 for row in heatmap for value in row)
        assert any(peak["persistence_days_2x"] == 116 for peak in data["peaks_0_15s"])

    print("visual data validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
