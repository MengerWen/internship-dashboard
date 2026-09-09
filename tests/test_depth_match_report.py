"""Check presentation artifacts against accepted data and downloadable evidence."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from xml.etree import ElementTree
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/depth-match-2026-09-07'
WEB = ROOT / 'content/daily/2026-09-07.show.html'
OFFLINE = ROOT / 'content/daily/2026-09-07.html'
BASELINE = '348d4dd6f898d671b0973dac9a5d8265ccc70e2c71191e77cf402e02d8924dfe'
sys.path.insert(0, str(ROOT / 'tools'))
from depth_match_math import formulas


def sha(value):
    return hashlib.sha256(value).hexdigest()


def payload(path, name):
    return re.search(r'<script[^>]*id="' + name + r'"[^>]*>(.*?)</script>', path.read_text(encoding='utf-8'), re.S).group(1)


class DepthMatchReportChecks(unittest.TestCase):
    def test_both_pages_preserve_the_accepted_24_column_601_day_payload(self):
        for path in (WEB, OFFLINE):
            raw = payload(path, 'report-data')
            self.assertEqual(sha(raw.encode()), BASELINE)
            data = json.loads(raw)
            self.assertEqual(len(data['registry']['columns']), 24)
            self.assertEqual(len(data['daily_ic']), 14424)
            self.assertEqual(len({r['period'] for r in data['period_summary']}), 44)
            self.assertEqual({s['side'] for s in data['registry']['specs']}, {'buy', 'sell'})

    def test_all_accepted_inputs_retain_their_recorded_hashes(self):
        audit = json.loads((ASSETS / '2026-09-07-report-build-audit.json').read_text(encoding='utf-8'))
        for name, expected in audit['copied_files'].items():
            self.assertEqual(sha((ASSETS / name).read_bytes()), expected, name)
        self.assertEqual(sha((ASSETS / 'evidence/DM_RESULT.json').read_bytes()), audit['source_result_sha256'])
        self.assertEqual(json.loads((ASSETS / 'evidence/DM_RESULT.json').read_text())['status'], 'accepted')

    def test_offline_figures_are_exact_copies_of_all_120_displayed_images(self):
        figures = json.loads(payload(OFFLINE, 'figure-data'))
        self.assertEqual(len(figures), 120)
        self.assertEqual(json.loads(payload(WEB, 'figure-data')), {})
        for name, encoded in figures.items():
            self.assertEqual(sha(base64.b64decode(encoded, validate=True)), sha((ASSETS / name).read_bytes()), name)

    def test_build_audit_and_reading_parts_contain_the_current_page(self):
        audit = json.loads((ASSETS / '2026-09-07-report-build-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['html_sha256'], sha(WEB.read_bytes()))
        self.assertEqual(audit['offline_html_sha256'], sha(OFFLINE.read_bytes()))
        self.assertEqual(audit['data_sha256'], BASELINE)
        seen = {}
        for part in sorted(ASSETS.glob('*review-part*.zip')):
            with zipfile.ZipFile(part) as archive:
                self.assertIsNone(archive.testzip())
                for item in archive.infolist():
                    self.assertNotIn(item.filename, seen)
                    seen[item.filename] = (item.CRC, item.file_size)
                    if item.filename == 'daily/2026-09-07.show.html':
                        self.assertEqual(archive.read(item), WEB.read_bytes())
        with zipfile.ZipFile(ASSETS / '2026-09-07-depth-match-review.zip') as archive:
            self.assertEqual(seen, {i.filename: (i.CRC, i.file_size) for i in archive.infolist()})
        self.assertIn('assets/depth-match-2026-09-07/evaluation/daily_ic.parquet', seen)

    def test_formula_registry_distinguishes_order_scores_from_daily_entropy(self):
        values = formulas()
        ns = {'m': 'http://www.w3.org/1998/Math/MathML'}
        for i in range(1, 13):
            self.assertIn(f'DM{i:02}', values)
            ElementTree.fromstring(values[f'DM{i:02}'])
        entropy = ElementTree.fromstring(values['DM12'])
        denominators = [''.join(f[1].itertext()) for f in entropy.findall('.//m:mfrac', ns)]
        self.assertEqual(denominators.count('N'), 1)
        self.assertEqual(denominators.count('log(5)'), 1)


if __name__ == '__main__':
    unittest.main()
