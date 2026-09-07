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


class ReportChecks(unittest.TestCase):
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
            self.assertEqual(len(factor['stats']), 45)
            for period, stats in factor['stats'].items():
                self.assertEqual(sum(stats['group_counts']), stats['paired'], (factor['id'], period))
                self.assertLessEqual(stats['paired'], stats['finite'])
                self.assertLessEqual(stats['finite'], stats['rows'])


if __name__ == '__main__':
    unittest.main()
