import importlib.util
from collections import Counter
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "collector", Path(__file__).resolve().parents[1] / "scripts/collect_journal_evidence.py"
)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class EvidenceTests(unittest.TestCase):
    def test_parent_whitelist_counts_only_matching_commits(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            def git(*args):
                return subprocess.run(["git", "-C", folder, *args], check=True, capture_output=True)
            git("init")
            git("config", "user.name", "Fixture")
            git("config", "user.email", "fixture@example.invalid")
            (repo / "outside.txt").write_text("outside")
            git("add", ".")
            git("commit", "-m", "outside")
            (repo / "实习").mkdir()
            (repo / "实习/中文 文件.md").write_text("inside")
            git("add", ".")
            git("commit", "-m", "inside")
            pinned = collector.git(repo, "rev-parse", "HEAD").strip()
            first = collector.collect_commits(repo, pinned, "2000-01-01", "实习/")
            entry = next(iter(first.values()))
            self.assertEqual(entry["commits"], 1)
            self.assertEqual(entry["items"][0]["subject"], "inside")
            self.assertIn("中文 文件.md", entry["paths"])
            (repo / "实习/another.md").write_text("later")
            git("add", ".")
            git("commit", "-m", "later")
            self.assertEqual(first, collector.collect_commits(repo, pinned, "2000-01-01", "实习/"))

    def test_outcomes_scan_full_day_and_accept_both_chain_formats(self):
        self.assertEqual(collector.chain_ids({"chains": ["a", {"id": "b", "note": "注解"}]}), ["a", "b"])
        with tempfile.TemporaryDirectory() as folder:
            def git(*args):
                return subprocess.run(["git", "-C", folder, *args], check=True, capture_output=True)
            git("init")
            git("config", "user.name", "Fixture")
            git("config", "user.email", "fixture@example.invalid")
            for i in range(12):
                (Path(folder) / "work.txt").write_text(str(i))
                git("add", ".")
                git("commit", "-m", f'Revert "尝试 {i}"')
            entry = next(iter(collector.collect_commits(folder, "HEAD", "2000-01-01").values()))
            self.assertEqual(len(entry["items"]), 10)
            self.assertEqual(entry["revert_count"], 12)
            self.assertEqual(len(entry["outcome_candidates"]), 12)
            self.assertTrue(all(c["kind"] == "intraday-revert" for c in entry["outcome_candidates"]))

    def test_redaction_covers_nested_text_and_keeps_public_links(self):
        counts = Counter()
        result = collector.redact({"items": ["C:\\Users\\private", "a@host", "10.2.3.4", "https://github.com/org/repo"], "top_paths": [("private.jumpserver.pem", 2)]}, ["@", "jumpserver"], counts)
        self.assertEqual(result["items"][:3], ["<已隐去>"] * 3)
        self.assertEqual(result["items"][3], "https://github.com/org/repo")
        self.assertEqual(result["top_paths"], [["<已隐去>", 2]])
        self.assertEqual(counts["redacted"], 4)


if __name__ == "__main__":
    unittest.main()
