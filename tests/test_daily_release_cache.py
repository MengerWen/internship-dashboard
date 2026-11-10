import subprocess

from scripts.daily_release_cache import DailyReleaseCache


def test_release_cache_reuses_only_unchanged_history_and_markdown(tmp_path):
    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
            cwd=tmp_path,
        )

    git("init", "-b", "main")
    (tmp_path / "build.py").write_text("# fixture", encoding="utf-8")
    daily = tmp_path / "content/daily"
    daily.mkdir(parents=True)
    old = daily / "old.md"
    edited = daily / "edited.md"
    old.write_text("untouched", encoding="utf-8")
    edited.write_text("before", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")

    file = tmp_path / ".git/daily-cache.json"
    dates = ["2026-11-01T09:00:00+08:00", "2026-11-02T09:00:00+08:00"]
    first = DailyReleaseCache(tmp_path, file)
    first.times = {"content/daily/old.md": dates, "content/daily/edited.md": dates}
    first.render("content/daily/old.md", "untouched", str.upper)
    first.render("content/daily/edited.md", "before", str.upper)
    first.save()

    edited.write_text("after", encoding="utf-8")
    git("add", "content/daily/edited.md")
    git("commit", "-m", "edit one report")
    second = DailyReleaseCache(tmp_path, file)
    assert second.saved_times("content/daily/old.md", True) == dates
    assert second.saved_times("content/daily/edited.md", True) is None
    assert second.render("content/daily/old.md", "untouched", str.lower) == "UNTOUCHED"
    assert second.render("content/daily/edited.md", "after", str.upper) == "AFTER"
    assert second.render_hits == 1

    second.times = {"content/daily/old.md": dates}
    second.save()
    git("checkout", "--detach", "HEAD~1")
    assert DailyReleaseCache(tmp_path, file).saved_times("content/daily/old.md", True) is None
