"""Publication contracts for the frozen-model daily report."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    page = (ROOT / "content/daily/2026-09-18.show.html").read_text(encoding="utf-8")
    blob = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', page, re.S)
    assert blob
    return page, json.loads(blob.group(1))


def test_daily_registration_and_self_contained_charts(report):
    page, data = report
    assert (ROOT / "content/daily/2026-09-18.md").exists()
    assert 'show_allow_downloads: true' in (ROOT / "content/daily/2026-09-18.md").read_text(encoding="utf-8")
    assert len(re.findall(r'<figure id=', page)) == 18
    assert '@@' not in page
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://', page)
    assert len(page.encode('utf-8')) < 25 * 1024**2
    assert len(data['feature_mapping']) == 330
    assert len({r['model_column'] for r in data['feature_mapping']}) == 330


def test_frozen_model_identity_and_selection(report):
    _, data = report
    params = data['effective_parameters']['booster_params']
    assert params['objective'] == 'regression_l2'
    assert params['device_type'] == 'cpu'
    assert params['num_threads'] == 8
    assert params['seed'] == 20260918
    assert data['selection']['selected_iteration'] == 659
    assert max(data['validation_curve'], key=lambda r: r['long_short_sharpe'])['iteration'] == 659
    assert data['test_summary']['no_training_call'] is True
    assert data['effective_parameters']['actual_rounds'] == 1000


def test_statistics_recalculate_from_published_daily_series(report):
    import math
    import statistics

    _, data = report
    rows = data['test_daily']
    assert len(rows) == 176
    assert len({row['date'] for row in rows}) == 176
    values = [r['long_short_return'] for r in rows]
    actual = math.sqrt(252) * statistics.mean(values) / statistics.stdev(values)
    assert actual == pytest.approx(7.300545039024522, abs=1e-12)
    assert statistics.mean(r['rank_ic'] for r in rows) == pytest.approx(0.022039952480479963)
    gross100 = math.prod(1 + value / 2 for value in values) - 1
    assert gross100 == pytest.approx(0.12105576246879757)
    assert data['extra_analysis']['long_excess_sharpe'] == pytest.approx(5.954786105002072)


def test_audit_limits_and_label_checks_are_visible(report):
    page, data = report
    assert '这里不能写成“已经证明没有未来数据”' in page
    assert '不是账户净值' in page
    assert '不是组合 Sharpe' in page
    assert '不是 beta 中性化' in page
    checks = data['audit']['all_test_label_audit.json']
    assert checks['rows'] == 507460
    assert checks['valid'] == 505403
    assert max(checks['counts'].values()) == 0

