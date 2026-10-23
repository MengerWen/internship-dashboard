"""约束审阅登记的证据与日点，避免图形默认位置重新变成事实。"""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import quote

import frontmatter

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / 'content/chains.json').read_text(encoding='utf-8'))
        cls.chains = {c['id']: c for c in cls.registry['chains']}
        cls.days = {p.stem: frontmatter.load(p) for p in (ROOT / 'content/journal').glob('????-??-??.md')}

    def test_every_handoff_has_real_endpoints_and_fixed_sources(self):
        seen = set()
        for edge in self.registry['handoffs']:
            pair = (edge['from'], edge['to'])
            self.assertNotIn(pair, seen)
            seen.add(pair)
            for cid, day in zip(pair, [edge['source_date'], edge['date']]):
                self.assertIn(cid, self.chains)
                self.assertIn(day, self.days)
                self.assertIn(cid, [x['id'] if isinstance(x, dict) else x for x in self.days[day]['chains']])
            self.assertLessEqual(edge['source_date'], edge['date'])
            self.assertTrue(edge['source_refs'])
        for owner in [*self.chains.values(), *self.registry['handoffs']]:
            self.assertTrue(owner['source_refs'])
            for ref in owner['source_refs']:
                self.assertRegex(ref['revision'], r'^[a-f0-9]{40}$')
                base = f"https://github.com/MengerWen/{ref['repo']}/"
                if ref['kind'] == 'file':
                    lo, hi = ref['lines']
                    self.assertTrue(1 <= lo <= hi)
                    self.assertEqual(ref['url'], f"{base}blob/{ref['revision']}/{quote(ref['path'], safe='/')}#L{lo}-L{hi}")
                else:
                    self.assertEqual(ref['url'], f"{base}commit/{ref['revision']}")

    def test_uncertain_dates_keep_explanation_in_visible_body(self):
        pending = set()
        for day, post in self.days.items():
            self.assertIn('## 原始依据', post.content)
            for cid, reason in post.get('date_notes', {}).items():
                pending.add((cid, day))
                self.assertIn('## 日期待核', post.content)
                self.assertIn(reason, post.content)
        declared = {(c['id'], day) for c in self.chains.values() for day in c['review']['unreviewed_days']}
        self.assertEqual(pending, declared)

    def test_report_coverage_is_explicit_and_never_a_demo_report(self):
        for chain in self.chains.values():
            self.assertEqual(chain['report_coverage'], 'curated')
            for day in chain['closes_into'].get('daily', []):
                self.assertTrue((ROOT / f'content/daily/{day}.md').exists())
                self.assertNotIn(day, ['2026-07-05', '2026-07-06', '2026-10-10'])


if __name__ == '__main__':
    unittest.main()
