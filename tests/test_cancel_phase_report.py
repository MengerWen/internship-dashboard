"""Check reporting math against ties, missing labels and sealed summary evidence."""
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cancel_report', ROOT / 'tools/build_cancel_phase_report_20260906.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
from cancel_phase_diagnostics import average_ranks, correlation, fit_ols
from cancel_phase_dispersion import daily_group_dispersion, nw_mean_se


class ReportChecks(unittest.TestCase):
    def test_daily_variance_decomposition_separates_known_group_structure(self):
        x = np.arange(100)
        y = x//10 + np.tile([-1, 1], 50)
        means, variances, within, between, total = daily_group_dispersion(x, y)
        np.testing.assert_allclose(means, np.arange(10))
        np.testing.assert_allclose(variances, 1)
        self.assertAlmostEqual(within, 1)
        self.assertAlmostEqual(between, 8.25)
        self.assertAlmostEqual(total, 9.25)

    def test_newey_west_se_uses_the_daily_sequence(self):
        self.assertAlmostEqual(nw_mean_se([1, 2, 3, 4]), .625)
    def test_average_ranks_handle_ties_without_using_input_order(self):
        np.testing.assert_array_equal(average_ranks([7, 1, 7, 4, 1]), [4.5, 1.5, 4.5, 3, 1.5])
        self.assertAlmostEqual(correlation([1, 2, 3], [6, 4, 2]), -1)

    def test_ols_includes_intercept_and_drops_only_nonfinite_pairs(self):
        fit = fit_ols(np.array([1, 2, 3, np.nan, 4]), np.array([5, 3, 1, 100, -1]))
        self.assertEqual(fit['n'], 4)
        self.assertAlmostEqual(fit['intercept'], 7)
        self.assertAlmostEqual(fit['slope'], -2)
        self.assertAlmostEqual(fit['r2'], 1)
        self.assertAlmostEqual(fit['rmse'], 0)
    def test_ties_are_kept_together_instead_of_forcing_equal_groups(self):
        means, counts = report.daily_deciles(np.ones(40), np.arange(40))
        self.assertEqual(counts.sum(), 40)
        self.assertEqual(np.count_nonzero(counts), 1)
        self.assertEqual(counts[5], 40)
        self.assertTrue(np.isnan(means[0]) and np.isnan(means[9]))

    def test_missing_labels_are_removed_before_ranking(self):
        y = np.arange(40, dtype=float)
        y[30:] = np.nan
        means, counts = report.daily_deciles(np.arange(40), y)
        np.testing.assert_array_equal(counts, np.full(10, 3))
        self.assertEqual(means[9] - means[0], 27)

    def test_final_payload_matches_601_day_acceptance(self):
        data = json.loads((report.ASSETS / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['factors']), 24)
        self.assertEqual(len(data['dates']), 601)
        self.assertEqual(len(data['periods']), 45)
        self.assertEqual(data['audit']['rows'], 1719612)
        self.assertEqual(data['audit']['valid_labels'], 1710977)
        self.assertEqual(data['audit']['group_checks'], 14424)
        self.assertLessEqual(data['audit']['max_decile_spread_abs_error'], 1e-12)
        self.assertAlmostEqual(max(abs(f['stats'][report.FULL]['rank']) for f in data['factors']), .004559803585265306)
        self.assertAlmostEqual(max(abs(f['stats'][report.FULL]['t']) for f in data['factors']), 1.68135678590385)
        for factor in data['factors']:
            audit = factor['diagnosis']
            self.assertLess(audit['max_ic_abs_error'], 1e-12)
            self.assertLess(audit['max_rank_abs_error'], 1e-12)
            self.assertAlmostEqual(sum(factor['daily_ic']), audit['daily_ic_sum'])
            self.assertAlmostEqual(sum(factor['daily_rank']), audit['daily_rank_sum'])
            self.assertEqual(audit['ols']['n'], factor['stats'][report.FULL]['paired'])
            self.assertEqual(audit['scatter_point_count'], audit['ols']['n'])
            self.assertAlmostEqual(audit['ols']['r2'], audit['ols']['r'] ** 2)
            self.assertEqual(len(factor['stats']), 45)
            for period, stats in factor['stats'].items():
                self.assertEqual(sum(stats['group_counts']), stats['paired'], (factor['id'], period))
                self.assertLessEqual(stats['paired'], stats['finite'])
                self.assertLessEqual(stats['finite'], stats['rows'])
                dispersion = stats['dispersion']
                self.assertAlmostEqual(dispersion['within_variance_fraction']+dispersion['between_variance_fraction'],1)
                self.assertGreaterEqual(dispersion['within_variance_fraction'],0)
                self.assertLessEqual(dispersion['within_variance_fraction'],1)
                np.testing.assert_allclose((np.array(dispersion['ci95_low_bps'])+dispersion['ci95_high_bps'])/2,stats['groups_bps'],atol=1e-10)
                self.assertAlmostEqual(stats['spread_bps']/dispersion['spread_nw_se_bps'],stats['spread_t_nw'])
                g = stats['diagnosis_groups']
                np.testing.assert_allclose(g['mean_bps'], stats['groups_bps'], atol=1e-10)
                np.testing.assert_allclose(np.array(g['winsor_bps'])+g['tail_bps'], g['mean_bps'], atol=1e-10)

    def test_f22_keeps_return_magnitude_and_rank_evidence_distinct(self):
        data = json.loads((report.ASSETS / 'report.json').read_text(encoding='utf-8'))
        f = next(f for f in data['factors'] if f['id'] == 'F22')
        s = f['stats'][report.FULL]
        self.assertGreater(s['rank'], 0)
        self.assertLess(s['ic'], 0)
        self.assertLess(s['rank_x_return'], 0)
        self.assertLess(s['spread_bps'], 0)
        self.assertEqual(s['positive_rank_negative_spread_days'], 112)
        self.assertGreater(s['diagnosis_groups']['rank_pct'][9], s['diagnosis_groups']['rank_pct'][0])


if __name__ == '__main__':
    unittest.main()
