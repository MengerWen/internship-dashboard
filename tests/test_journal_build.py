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
            '---\nheadline: 一句话\nheadline_source: written\nchains: [a, absent]\nreports_covering: [2026-01-01]\n---\n正文独有文字', encoding="utf-8")
        for day in ("2026-06-23", "2026-06-24"):
            (content / f"journal/_evidence/{day}.json").write_text(json.dumps({"date": day,
                "repos": [{"repo": "r", "commits": 123, "items": [{"subject": "</script>证据"}]}],
                "plans": [], "suggest": {"chains": ["a"]}}), encoding="utf-8")
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
            self.assertEqual(missing["chains"], [])  # suggest 不参与构建。
            self.assertEqual(missing["headline_source"], "commit")
            self.assertEqual(missing["total_commits"], 123)
            self.assertTrue(first["has_body"])
            self.assertIsNone(builder.chains["tracks"][0]["stage"])
            self.assertEqual(builder.chains["chains"][0]["start"], "2026-06-23")
            self.assertEqual(len(builder.warnings), 4)
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


if __name__ == "__main__":
    unittest.main()
