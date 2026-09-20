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
    assert len(re.findall(r'<figure id=', page)) == 22
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


def test_expanding_split_is_declared_not_replaced(report):
    """The run is fold 15 of the frozen 15-fold plan, and the page must say so."""
    page, data = report
    folds = data['expanding_folds']
    assert len(folds) == 15
    assert [f['fold'] for f in folds] == list(range(1, 16))
    assert folds[0]['month'] == '2024-07' and folds[-1]['month'] == '2025-09'
    assert sum(f['validation_days'] for f in folds) == 308
    assert folds[-1]['train_days'] == len(data['dataset']['train_dates']) == 403
    assert all(f['train_days'] < folds[i + 1]['train_days'] for i, f in enumerate(folds[:-1]))
    assert '15 折扩张验证' in page
    assert '前 14 折没有运行' in page


def test_rank_ic_decomposes_across_deciles(report):
    """The ten decile contributions must reconstruct the published RankIC exactly."""
    _, data = report
    deciles = data['deciles']
    assert [row['decile'] for row in deciles] == list(range(1, 11))
    total = sum(row['rank_ic_contribution'] for row in deciles)
    assert total == pytest.approx(0.022039952480479963, abs=1e-12)
    assert deciles[0]['inner_rank_ic'] == pytest.approx(data['extra_analysis']['mean_bottom_ic'], abs=1e-12)
    # The traded ends carry most of the signal; the untraded middle dilutes the average.
    assert data['extra_analysis']['middle_decile_ic_share'] < 0.2
    assert data['extra_analysis']['extreme_decile_ic_share'] > 0.6
    rows = len(data['decile_rank_ic_daily'])
    assert rows == 176


def test_pool_rank_ic_uses_the_published_scale(report):
    """Restricting the cross-section must reuse the headline RankIC definition."""
    page, data = report
    pools = {row['key']: row for row in data['rank_ic_pools']}
    # Whole-universe and middle pools must reproduce numbers already published.
    assert pools['all']['mean_rank_ic'] == pytest.approx(0.022039952480479963, abs=1e-12)
    assert pools['middle']['mean_rank_ic'] == pytest.approx(data['extra_analysis']['mean_middle_ic'], abs=1e-12)
    assert pools['all']['deciles'] == list(range(1, 11))
    # The traded long-short pool carries a visibly higher correlation and ICIR.
    assert pools['long_short']['mean_rank_ic'] > 2 * pools['middle']['mean_rank_ic']
    assert pools['long_short']['ic_ir'] > pools['all']['ic_ir']
    assert pools['long_short']['mean_count'] < pools['all']['mean_count'] / 4
    # The mechanical part of that lift is disclosed, not hidden.
    assert 'spaced_control' in pools
    assert '机械效应未排除' in page and '机械的' in page


def test_every_decile_rank_ic_is_a_readable_number(report):
    """The per-decile RankIC must be legible as figures, not only as a chart."""
    page, data = report
    for row in data['deciles']:
        assert row['inner_rank_ic'] is not None
        assert row['inner_rank_ic_ir'] is not None
    # D9's inner ordering is noise; the page states it rather than rounding it away.
    d9 = next(r for r in data['deciles'] if r['decile'] == 9)
    assert d9['inner_rank_ic'] < 0
    assert '−0.00364' in page or '-0.00364' in page
    assert page.count('组内日均 RankIC') == 1
    assert page.count('日均 RankIC') >= 2


def test_decile_view_reconstructs_the_official_portfolios(report):
    """Deciles and the formal legs must agree up to the direction gate."""
    _, data = report
    reconstructed = data['extra_analysis']['decile_reconstructed_sharpe']
    overall = data['test_summary']['overall_metrics']
    assert reconstructed['pure_long'] == pytest.approx(overall['pure_long_sharpe'], abs=.05)
    assert reconstructed['pure_short'] == pytest.approx(overall['pure_short_sharpe'], abs=.05)
    assert reconstructed['long_short'] == pytest.approx(overall['long_short_sharpe'], abs=.1)


def test_figures_are_typeset_not_hand_drawn(report):
    """Charts come from matplotlib and equations from MathML, with readable ticks."""
    page, _ = report
    assert page.count('<math ') >= 5
    assert page.count('-figure_1"') == 22
    assert '<sub>' not in page
    # The old hand-rolled renderer printed every RankIC tick as "0.0".
    assert '>-0.0</text>' not in page


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

