"""Verify all directional report records and the preserved total baseline."""
import hashlib
import json
from pathlib import Path
import re
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/cancel-phase-2026-09-06'


class DirectionReportChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ASSETS / 'report.json').read_text(encoding='utf-8'))

    def test_total_values_match_the_accepted_baseline(self):
        encoded = json.dumps(self.data['factors'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         '569938b96484d2a434709be2819888c2bbd8d753c87d8cc68c6132529cc3296d')

    def test_both_directions_have_all_periods_diagnostics_and_figures(self):
        self.assertEqual(set(self.data['directions']), {'buy', 'sell'})
        for side, data in self.data['directions'].items():
            self.assertEqual(data['direction'], side)
            self.assertEqual(data['dates'], self.data['dates'])
            self.assertEqual(data['periods'], self.data['periods'])
            self.assertEqual(data['audit']['rows'], 1719612)
            self.assertEqual(data['audit']['valid_labels'], 1710977)
            self.assertEqual(data['audit']['execution']['status'], 'complete')
            self.assertTrue(data['audit']['execution']['total_comparison']['nan_masks_equal'])
            self.assertEqual([f['id'] for f in data['factors']], [f'F{i:02d}' for i in range(1, 25)])
            for f in data['factors']:
                self.assertEqual(len(f['stats']), 45)
                self.assertEqual(len(f['daily_ic']), 601)
                self.assertEqual(len(f['daily_rank']), 601)
                self.assertLess(f['diagnosis']['max_ic_abs_error'], 1e-12)
                self.assertLess(f['diagnosis']['max_rank_abs_error'], 1e-12)
                self.assertEqual(f['diagnosis']['ols']['n'], f['stats']['2024-2026Q2']['paired'])
                for stats in f['stats'].values():
                    self.assertEqual(sum(stats['group_counts']), stats['paired'])
                    self.assertLessEqual(stats['paired'], stats['finite'])
                    self.assertLessEqual(stats['finite'], stats['rows'])
                    np.testing.assert_allclose(stats['groups_bps'], stats['diagnosis_groups']['mean_bps'], atol=1e-10)
                    d = stats['dispersion']
                    np.testing.assert_allclose((np.array(d['ci95_low_bps']) + d['ci95_high_bps']) / 2,
                                               stats['groups_bps'], atol=1e-10)
                for suffix in ('daily', 'monthly', 'distribution', 'scatter', 'errorbars'):
                    self.assertTrue((ASSETS / side / f'{f["id"]}-{suffix}.webp').is_file())

    def test_web_and_offline_embed_the_same_complete_direction_data(self):
        for name in ('2026-09-06.html', '2026-09-06.show.html'):
            html = (ROOT / 'content/daily' / name).read_text(encoding='utf-8')
            payload = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S)[1]
            self.assertEqual(json.loads(payload), self.data)


if __name__ == '__main__':
    unittest.main()
