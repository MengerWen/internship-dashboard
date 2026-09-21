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
    assert len(data['feature_mapping']) == 328
    assert len({r['model_column'] for r in data['feature_mapping']}) == 328
    assert not any('f97' in r['model_column'] for r in data['feature_mapping'])


def test_original_presentation_structure_is_preserved(report):
    page, _ = report
    template = (ROOT / 'templates/model-report-20260918.html').read_text(encoding='utf-8')
    assert re.findall(r'<style[^>]*>.*?</style>', page, re.S)[0] == re.findall(
        r'<style[^>]*>.*?</style>', template, re.S)[0]
    assert re.findall(r'<section id="([^"]+)', page) == re.findall(
        r'<section id="([^"]+)', template)
    assert page.count('<details') == template.count('<details')
    assert page.count('<table') == template.count('<table') + 12
    assert page.count('<button id=') == template.count('<button id=')


def test_frozen_model_identity_and_selection(report):
    _, data = report
    params = data['effective_parameters']['booster_params']
    assert params['objective'] == 'regression_l2'
    assert params['device_type'] == 'cpu'
    assert params['num_threads'] == 8
    assert params['seed'] == 20260918
    assert data['selection']['selected_iteration'] == 718
    assert max(data['validation_curve'], key=lambda r: r['long_short_sharpe'])['iteration'] == 718
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
    assert actual == pytest.approx(7.048473816440077, abs=1e-12)
    assert statistics.mean(r['rank_ic'] for r in rows) == pytest.approx(0.02309910018467606)
    gross100 = math.prod(1 + value / 2 for value in values) - 1
    assert gross100 == pytest.approx(0.11776153068518225, abs=1e-12)
    assert data['extra_analysis']['long_excess_sharpe'] == pytest.approx(6.242725405735008)


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
    assert total == pytest.approx(0.02309910018467606, abs=1e-12)
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
    assert pools['all']['mean_rank_ic'] == pytest.approx(0.02309910018467606, abs=1e-12)
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
    assert '-0.00211' in page
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
    checks = data['audit']
    assert checks['ledger_daily_reconciliation_max_abs'] < 1e-12
    assert checks['entry_unfilled_contribution_max_abs'] == 0
    assert checks['position_status_counts']['open_marked'] == 628
    assert checks['position_status_counts']['entry_unfilled'] == 828
    assert checks['sample_trade_vwap_consistency']['passed'] is True


def test_new_diagnostics_explain_rankic_sharpe_gap(report):
    page, data = report
    diagnostics = data['diagnostics']
    rank = diagnostics['rank_between_within']
    assert rank['between_deciles'] + rank['within_deciles'] == pytest.approx(rank['total'], abs=1e-12)
    assert rank['between_share'] == pytest.approx(0.9760600101827678)
    assert rank['within_share'] == pytest.approx(0.023939989817232155)
    variance = diagnostics['variance_decomposition']
    assert variance['underlying_leg_correlation'] == pytest.approx(0.7313519500598689)
    assert variance['variance_offset_share'] == pytest.approx(0.7274299708887237)
    assert variance['long_short_std_bp'] == pytest.approx(28.54689992727052)
    assert variance['zero_covariance_std_bp'] == pytest.approx(54.678916774348565)
    assert '97.6%' in page and '72.7%' in page


def test_tail_breadth_and_uncertainty_are_published(report):
    _, data = report
    diagnostics = data['diagnostics']
    breadth = diagnostics['tail_breadth']
    assert [row['tail_fraction'] for row in breadth] == [.05, .1, .2, .3]
    assert all(row['sharpe'] > 6 for row in breadth)
    bootstrap = diagnostics['moving_block_bootstrap']
    assert bootstrap['block_days'] == 5 and bootstrap['draws'] == 10_000
    assert bootstrap['sharpe_quantiles']['p025'] == pytest.approx(4.432164374404967)
    assert bootstrap['sharpe_quantiles']['p975'] == pytest.approx(10.467033628026906)


def test_selected_stock_attribution_and_real_world_cases(report):
    page, data = report
    diagnostics = data['diagnostics']
    assert diagnostics['publication_scope'].startswith('selected attribution only')
    concentration = diagnostics['stockday_concentration_summary']
    assert concentration['selected_stockdays'] == 101676
    assert concentration['unique_stocks'] == 2900
    assert concentration['largest_positive_stockday_share'] == pytest.approx(0.0034295996367960727)
    assert concentration['top_10_positive_stockdays_share'] == pytest.approx(0.022591686308078122)
    cases = {(row['date'], row['code']): row for row in diagnostics['real_world_cases']}
    assert cases['2026-05-20', '301139']['contribution'] == pytest.approx(0.0007650853133760605)
    assert cases['2025-12-22', '002188']['contribution'] == pytest.approx(0.00046131205407434723)
    assert cases['2026-04-27', '001234']['contribution'] == pytest.approx(-0.0004896375283556807)
    assert '*ST元道' in page and '中天服务' in page and '泰慕士' in page
    assert '不能证明公告导致' in page
