"""Published model report must agree with the causal-accounting run artifacts."""
import json
import math
import re
import statistics
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    page = (ROOT / "content/daily/2026-09-18.show.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', page, re.S)
    assert match
    return page, json.loads(match.group(1))


def test_report_is_self_contained_and_registered(report):
    page, data = report
    daily = (ROOT / "content/daily/2026-09-18.md").read_text(encoding="utf-8")
    assert "show_allow_downloads: true" in daily
    assert len(page.encode("utf-8")) < 25 * 1024**2
    assert "<svg" in page and "<script id=\"report-data\"" in page
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://', page)
    assert "09:35" in page and "open_marked" in page and "f97" in page
    assert data == json.loads((ROOT / "content/assets/model-report-2026-09-18/report-data.json").read_text(encoding="utf-8"))


def test_exact_model_identity_and_validation_selection(report):
    _, data = report
    mapping = data["feature_mapping"]
    params = data["effective_parameters"]
    curve = data["validation_curve"]
    selection = data["selection"]
    assert len(mapping) == data["dataset"]["feature_count"] == data["test_summary"]["feature_count"] == 328
    assert not any("f97" in json.dumps(row, ensure_ascii=False).lower() for row in mapping)
    assert sum("f97" in name.lower() for name in data["excluded_old_columns"]) == 2
    assert params["booster_params"]["objective"] == "regression_l2"
    assert params["booster_params"]["device_type"] == "cpu"
    assert params["booster_params"]["num_threads"] == 8
    assert params["actual_rounds"] == len(curve) == 1000
    metric = selection["selection_metric"]
    eligible = [row for row in curve if row[metric] is not None and math.isfinite(row[metric])]
    assert max(eligible, key=lambda row: row[metric])["iteration"] == selection["selected_iteration"]
    assert data["test_summary"]["selected_model_iteration"] == selection["selected_iteration"]
    assert data["test_summary"]["no_training_call"] is True
    assert data["observational_baseline"]["feature_count"] == 330
    assert "baseline/test_summary.json" in data["source_sha256"]


def test_daily_series_reconstructs_published_sharpe_and_ic(report):
    _, data = report
    rows = data["test_daily"]
    assert len(rows) == 176 == data["test_summary"]["test_date_count"]
    assert len({row["date"] for row in rows}) == len(rows)
    returns = [row["long_short_return"] for row in rows]
    computed = math.sqrt(252) * statistics.mean(returns) / statistics.stdev(returns)
    assert computed == pytest.approx(data["test_summary"]["overall_metrics"]["long_short_sharpe"], abs=1e-12)
    ic = [row["rank_ic"] for row in rows if row["rank_ic"] is not None]
    assert statistics.mean(ic) == pytest.approx(data["test_summary"]["overall_metrics"]["mean_daily_rank_ic"], abs=1e-12)
    assert sum(row["long_missing_label_count"] + row["short_missing_label_count"]
               + row["ls_long_missing_label_count"] + row["ls_short_missing_label_count"]
               for row in rows) == data["open_position_rows"]
    assert sum(data["position_status_counts"].values()) == data["position_rows"]
    legs = data["leg_dependence"]["long_short_legs_daily"]
    assert len(legs) == len(rows)
    assert all(leg["date"] == row["date"] and leg["long_contribution"] + leg["short_contribution"] == pytest.approx(row["long_short_return"], abs=1e-12)
               for leg, row in zip(legs, rows))


def test_source_revision_and_input_hashes_are_published(report):
    page, data = report
    paths = data["paths"]
    revision = paths["business_revision"]
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    assert revision in page
    assert paths["train_run_root"] in page and paths["test_run_root"] in page
    assert len(data["source_sha256"]) >= 10
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in data["source_sha256"].values())
    assert "观察性对照" in page and "新盲测" in page
