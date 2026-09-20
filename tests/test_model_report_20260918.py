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
    assert len(re.findall(r'<figure id=', page)) == 27
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
    # D9's estimate stays visible, while the page avoids treating a near-zero point estimate as proof.
    d9 = next(r for r in data['deciles'] if r['decile'] == 9)
    assert d9['inner_rank_ic'] < 0
    assert '−0.00364' in page or '-0.00364' in page
    assert '不能据此证明真实组内能力为负' in page
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
    assert page.count('-figure_1"') == 27
    assert '<sub>' not in page
    # The old hand-rolled renderer printed every RankIC tick as "0.0".
    assert '>-0.0</text>' not in page


def test_explanation_is_split_into_navigable_chapters(report):
    """The RankIC/Sharpe explanation is four chapters, each reachable from the nav."""
    page, _ = report
    order = re.findall(r'<section id="([a-z-]+)"><div class="section-head"><span class="num">(\d\d)', page)
    assert [sid for sid, _ in order] == [
        'setup', 'validation', 'test', 'explain', 'deciles-view',
        'rankic', 'portfolio', 'audit', 'performance', 'evidence',
    ]
    assert [num for _, num in order] == [f'{i:02d}' for i in range(1, 11)]
    nav = re.search(r'<nav class="nav"[^>]*>(.*?)</nav>', page, re.S).group(1)
    assert re.findall(r'href="#([a-z-]+)"', nav) == [sid for sid, _ in order]
    # No chapter may swallow the page again: cap the figures any one of them holds.
    bodies = re.split(r'<section id="[a-z-]+">', page)[1:]
    assert max(body.count('<figure id=') for body in bodies) <= 6


def test_nav_tracks_the_section_being_read(report):
    """Every daily page ships the shared scrollspy; this one styles its active tab."""
    page, _ = report
    assert page.count('<script data-nav-scrollspy>') == 1
    assert '<style data-nav-scrollspy>' in page
    assert '.nav a.active' in page
    assert "classList.toggle('active'" in page


def test_charts_sit_on_the_page_not_on_a_white_card(report):
    """Figures share the page background instead of being framed like pasted images."""
    page, _ = report
    assert '.chart-scroll{overflow-x:auto}' in page
    assert 'background:#fff;border:1px solid #e1e5dd' not in page
    # matplotlib paints a figure patch only when the canvas is opaque.
    assert 'fill: #ffffff' not in page


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


def test_new_diagnostics_explain_rankic_sharpe_gap(report):
    page, data = report
    diagnostics = data['diagnostics']
    rank = diagnostics['rank_between_within']
    assert rank['between_deciles'] + rank['within_deciles'] == pytest.approx(rank['total'], abs=1e-12)
    assert rank['between_share'] == pytest.approx(0.9683911731605613)
    assert rank['within_share'] == pytest.approx(0.03160882683943884)
    variance = diagnostics['variance_decomposition']
    assert variance['underlying_leg_correlation'] == pytest.approx(0.7354066913557537)
    assert variance['variance_offset_share'] == pytest.approx(0.7341976004856114)
    assert variance['long_short_std_bp'] == pytest.approx(28.288075250845683)
    assert variance['zero_covariance_std_bp'] == pytest.approx(54.86860896227923)
    assert '96.8%' in page and '73.4%' in page


def test_tail_breadth_and_uncertainty_are_published(report):
    _, data = report
    diagnostics = data['diagnostics']
    breadth = diagnostics['tail_breadth']
    assert [row['tail_fraction'] for row in breadth] == [.05, .1, .2, .3]
    assert all(row['sharpe'] > 6 for row in breadth)
    bootstrap = diagnostics['moving_block_bootstrap']
    assert bootstrap['block_days'] == 5 and bootstrap['draws'] == 10_000
    assert bootstrap['sharpe_quantiles']['p025'] == pytest.approx(4.5043488285449)
    assert bootstrap['sharpe_quantiles']['p975'] == pytest.approx(11.06356935148117)


def test_selected_stock_attribution_and_real_world_cases(report):
    page, data = report
    diagnostics = data['diagnostics']
    assert diagnostics['publication_scope'].startswith('selected attribution only')
    concentration = diagnostics['stockday_concentration_summary']
    assert concentration['selected_stockdays'] == 100865
    assert concentration['unique_stocks'] == 2900
    assert concentration['largest_positive_stockday_share'] == pytest.approx(0.0033646840916486988)
    assert concentration['top_10_positive_stockdays_share'] == pytest.approx(0.022698709160944346)
    cases = {(row['date'], row['code']): row for row in diagnostics['real_world_cases']}
    assert cases['2026-05-20', '301139']['contribution'] == pytest.approx(0.000770398405830061)
    assert cases['2025-12-22', '002188']['contribution'] == pytest.approx(0.00046616797043302454)
    assert cases['2026-04-27', '001234']['contribution'] == pytest.approx(-0.0004913376586624712)
    assert '*ST元道' in page and '中天服务' in page and '泰慕士' in page
    assert '不能证明公告导致' in page

