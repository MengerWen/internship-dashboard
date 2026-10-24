"""冻结来源与正式日卡双向核对，不能只检查挑选过的摘录。"""
import gzip
import json
from pathlib import Path
import unittest

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/journal-review/rebuild-2026-10-21'


class RebuiltCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads((SOURCE / 'source-register.json').read_text(encoding='utf-8'))
        cls.ledger = json.loads(gzip.decompress((SOURCE / 'dispositions.json.gz').read_bytes()))
        cls.chains = {x['id']: x for x in json.loads((ROOT / 'content/chains.json').read_text(encoding='utf-8'))['chains']}
        cls.days = {p.stem: frontmatter.load(p) for p in (ROOT / 'content/journal').glob('????-??-??.md')}

    def test_every_research_source_day_and_chain_has_a_real_card(self):
        docs = {x['id']: x for x in self.register['documents']}
        for day, source in self.register['days'].items():
            self.assertIn(day, self.days)
            points = {x['id'] for x in self.days[day]['chains']}
            required = {c for s in source['sessions'] for c in s['chains']}
            required.update(c for fid in source['documents'] if docs[fid]['disposition'] == 'primary' for c in docs[fid]['chains'])
            self.assertFalse(required - points, (day, required - points))
            self.assertIn(f'days/{day}.md', self.days[day].content)
        self.assertNotIn('2026-09-30', self.register['days'])

    def test_all_frozen_sources_have_explicit_destinations_without_private_text(self):
        for key, count in self.register['counts'].items():
            if key not in self.ledger:  # 来源发现状态、缺失正文数等摘要不是账本条目。
                continue
            rows = self.ledger[key]
            self.assertEqual(len(rows), count)
            self.assertEqual(len(rows), len({x['id'] for x in rows}))
            self.assertTrue(all(x['destination'] for x in rows))
        for row in self.ledger['files']:
            self.assertNotIn('path', row)
            for destination in row['destination']:
                if destination.startswith('chain:'):
                    self.assertIn(destination[6:], self.chains)
        self.assertEqual(len(self.ledger['session_files']), 961)
        self.assertEqual(len(self.ledger['directory_exclusions']), 354)

    def test_v4_to_v9_are_research_with_individual_sessions_and_reports(self):
        day = self.register['days']['2026-10-14']
        ids = {x['id'] for x in day['sessions']}
        expected = ['01a1394c-ef5b-71d0-9f54-46dc98f07403', '01a1394f-7625-7e21-bc90-73250f612ce9',
                    '01a13960-2f1c-7180-922d-29166930cc0d', '01a13961-3394-7252-82bb-a8a090b75aa4',
                    '01a13964-b9d0-7632-9dad-b25d98832876', '01a13975-a3c3-7812-8d46-0eb270430790']
        self.assertTrue(all('codex:' + sid in ids for sid in expected))
        for version in range(4, 10):
            reports = [x for x in self.register['documents'] if x['path'].startswith(f'reports/2026-10/2026-10-14-V{version}') and '可行性' in x['title']]
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]['write_dates'], ['2026-10-14'])
            self.assertEqual(reports[0]['stage'], '构思（研究材料）')
        self.assertIn('没有运行真实L2预检', self.days['2026-10-14'].content)

    def test_new_chain_spans_follow_actual_points_and_preserve_confirmed_stop_date(self):
        for chain in self.chains.values():
            actual = sorted(d for d, p in self.days.items() if chain['id'] in {x['id'] for x in p['chains']})
            self.assertEqual(chain['review']['days'], len(actual))
            self.assertEqual(chain['review']['span'], [actual[0], actual[-1]])
        cross_stock = self.chains['cross-stock-sync']
        self.assertNotIn('2026-09-11', cross_stock['review']['unreviewed_days'])
        self.assertEqual(cross_stock['fate'], 'dropped')
        self.assertIn('9 月 11 日 17:29 的原始用户消息', cross_stock['fate_note'])
        self.assertFalse(self.days['2026-08-04'].get('date_notes'))
        self.assertIn('8月11日有明确的改数补丁', self.days['2026-08-04'].content)


if __name__ == '__main__':
    unittest.main()
