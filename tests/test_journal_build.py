import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build import Builder


class JournalBuildTests(unittest.TestCase):
    def make_fixture(self, root):
        content = root / "content"
        (content / "journal/_evidence").mkdir(parents=True)
        (content / "chains.json").write_text(json.dumps({"tracks": [{"id": "t", "stage": "missing"}],
            "chains": [{"id": "a", "track": "t", "review": {"unreviewed_days": ["2026-06-23"]}}],
            "handoffs": []}), encoding="utf-8")
        (content / "journal/2026-06-23.md").write_text(
            '---\nheadline: 一句话\nheadline_source: written\nchains: [a, absent]\ndate_notes: {a: 首次入库日晚于自述日, absent: 不存在的链}\nreports_covering: [2026-01-01]\n---\n正文独有文字', encoding="utf-8")
        for day in ("2026-06-23", "2026-06-24"):
            (content / f"journal/_evidence/{day}.json").write_text(json.dumps({"date": day,
                "repos": [{"repo": "r", "commits": 123, "items": [{"subject": "</script>证据"}]}],
                "plans": ([{"title": "当天计划"}] if day == "2026-06-23" else []), "suggest": {"chains": ["a"]}}), encoding="utf-8")
        return content

    def test_authoritative_chains_fallback_validation_and_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = self.make_fixture(root)
            builder = Builder()
            builder.out_dir = root / "out"
            with patch("build.ROOT", root), patch("build.CONTENT_DIR", content), patch("subprocess.run", side_effect=AssertionError("不得采集外仓")):
                builder.build_journal()
                builder.build_index_pages()
            first, missing = builder.journal_entries
            self.assertEqual(first["chains"], ["a"])
            self.assertEqual(first["chain_confidence"], {"a": "inferred"})
            self.assertEqual(first["date_notes"], {"a": "首次入库日晚于自述日"})
            self.assertEqual(builder.journal_evidence["2026-06-23"]["reports_covering"], [])
            self.assertEqual(missing["chains"], [])  # suggest 不参与构建。
            self.assertEqual(missing["headline_source"], "commit")
            self.assertEqual(missing["total_commits"], 123)
            self.assertEqual(first["highlights"], ["当天计划"])
            self.assertEqual(missing["highlights"], ["</script>证据"])
            self.assertTrue(first["has_body"])
            self.assertIsNone(builder.chains["tracks"][0]["stage"])
            self.assertEqual(builder.chains["chains"][0]["start"], "2026-06-23")
            self.assertEqual(len(builder.warnings), 5)
            self.assertEqual(first["chain_notes"]["a"], {"note": "", "outcome": "landed", "outcome_note": ""})
            page = (builder.out_dir / "_index-pages/journal-2026-06-23.html").read_text(encoding="utf-8")
            self.assertIn("正文独有文字", page)
            self.assertIn("../#/journal/2026-06-23", page)
            self.assertIn("&lt;/script&gt;", page)
            (builder.out_dir / "index.html").write_text('<body><!-- INLINE_DATA --></body>', encoding="utf-8")
            builder.inline_offline_data({})
            inline = (builder.out_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('id="journal-ev-2026-06-23"', inline)
            self.assertIn("<\\/script>", inline)
            self.assertIn('id="journal-body-2026-06-23"', inline)

    def test_chain_notes_outcome_inheritance_and_search(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = self.make_fixture(root)
            registry = json.loads((content / "chains.json").read_text(encoding="utf-8"))
            registry["chains"][0].update(fate="dropped", fate_note="被批量方案取代")
            (content / "chains.json").write_text(json.dumps(registry), encoding="utf-8")
            (content / "journal/2026-06-23.md").write_text(
                '---\nheadline: 一句话\nheadline_source: written\nchains:\n- id: a\n  note: 独有逐点注解\n---\n', encoding="utf-8")
            builder = Builder()
            builder.out_dir = root / "out"
            with patch("build.CONTENT_DIR", content):
                builder.build_journal()
            self.assertEqual(builder.journal_entries[0]["chain_notes"]["a"],
                             {"note": "独有逐点注解", "outcome": "dropped", "outcome_note": "被批量方案取代"})
            self.assertEqual(builder.chains["chains"][0]["lane"], 0)
            self.assertIn("独有逐点注解", builder.journal_pages[0].html)
            self.assertFalse(any("缺少注解" in w for w in builder.warnings))

    def test_later_chain_summary_is_not_a_daily_outcome(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = self.make_fixture(root)
            registry_path = content / "chains.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["chains"][0].update(fate="folded", fate_note="后续进入另一条研究线")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            builder = Builder()
            builder.out_dir = root / "out"
            with patch("build.CONTENT_DIR", content):
                builder.build_journal()
            self.assertEqual(builder.journal_entries[0]["chain_notes"]["a"]["outcome_note"], "")
            self.assertEqual(builder.chains["chains"][0]["fate_note"], "后续进入另一条研究线")


if __name__ == "__main__":
    unittest.main()
