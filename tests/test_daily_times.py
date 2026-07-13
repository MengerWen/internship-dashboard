import unittest
from datetime import datetime
from unittest.mock import patch

from build import Builder, CN_TZ, ROOT


class DailyTimesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = Builder()
        self.path = ROOT / "content" / "daily" / "2026-07-09.md"
        self.mtime = datetime(2026, 7, 13, 22, 51, 49, tzinfo=CN_TZ)

    def test_uses_each_documents_git_history_instead_of_shared_mtime(self) -> None:
        git_first = datetime(2026, 7, 9, 23, 38, 37, tzinfo=CN_TZ)
        git_last = datetime(2026, 7, 10, 10, 55, 5, tzinfo=CN_TZ)

        with (
            patch.object(self.builder, "git_times_for", return_value=(git_first, git_last)),
            patch.object(self.builder, "mtime_for", return_value=self.mtime),
        ):
            published, updated, source = self.builder.daily_times(self.path, {})

        self.assertEqual(published, "2026-07-09T23:38:37+08:00")
        self.assertEqual(updated, "2026-07-10T10:55:05+08:00")
        self.assertEqual(source, "git")
        self.assertEqual(self.builder.time_stats["git"], 1)

    def test_frontmatter_can_pin_published_time(self) -> None:
        git_first = datetime(2026, 7, 7, 12, 24, 32, tzinfo=CN_TZ)
        git_last = datetime(2026, 7, 7, 13, 9, 35, tzinfo=CN_TZ)

        with (
            patch.object(self.builder, "git_times_for", return_value=(git_first, git_last)),
            patch.object(self.builder, "mtime_for", return_value=self.mtime),
        ):
            published, updated, source = self.builder.daily_times(
                self.path, {"published": "2026-07-05 09:10:11"}
            )

        self.assertEqual(published, "2026-07-05T09:10:11+08:00")
        self.assertEqual(updated, "2026-07-07T13:09:35+08:00")
        self.assertEqual(source, "frontmatter")

    def test_falls_back_to_mtime_when_git_history_is_missing(self) -> None:
        with (
            patch.object(self.builder, "git_times_for", return_value=(None, None)),
            patch.object(self.builder, "mtime_for", return_value=self.mtime),
        ):
            published, updated, source = self.builder.daily_times(self.path, {})

        self.assertEqual(published, "2026-07-13T22:51:49+08:00")
        self.assertEqual(updated, "2026-07-13T22:51:49+08:00")
        self.assertEqual(source, "mtime")
        self.assertEqual(len(self.builder.warnings), 2)


if __name__ == "__main__":
    unittest.main()
