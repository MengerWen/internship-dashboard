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

    def test_redaction_covers_nested_text_and_keeps_public_links(self):
        counts = Counter()
        result = collector.redact({"items": ["C:\\Users\\private", "a@host", "10.2.3.4", "https://github.com/org/repo"]}, ["@"], counts)
        self.assertEqual(result["items"][:3], ["<已隐去>"] * 3)
        self.assertEqual(result["items"][3], "https://github.com/org/repo")
        self.assertEqual(counts["redacted"], 3)


if __name__ == "__main__":
    unittest.main()
