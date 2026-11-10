"""Cache the parts of a daily report build whose inputs can be checked independently."""

import hashlib
import json
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


class DailyReleaseCache:
    def __init__(self, root: Path, path: Path):
        self.root = root
        self.path = path
        renderer_inputs = [root / "build.py", Path(__file__)]
        renderer = hashlib.sha256(b"\0".join(file.read_bytes() for file in renderer_inputs))
        renderer.update(sys.version.encode())
        for package in ("Markdown", "pymdown-extensions", "Pygments", "python-frontmatter"):
            renderer.update(f"{package}={version(package)}\0".encode())
        self.renderer = renderer.hexdigest()
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = {}
        if not isinstance(previous, dict):
            previous = {}
        self.previous_html = previous.get("html") if previous.get("renderer") == self.renderer else None
        self.previous_times = None
        self.head = None
        self.git_config = None
        self.changed = set()
        self.html = {}
        self.times = {}
        self.render_hits = 0
        self.time_hits = 0
        self.prepare_git(previous)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.DEVNULL, timeout=10)

    def prepare_git(self, previous):
        try:
            head, shallow = self.git("rev-parse", "HEAD", "--is-shallow-repository").decode().splitlines()
            if shallow != "false" or self.git("replace", "-l"):
                return
            grafts = Path(self.git("rev-parse", "--git-path", "info/grafts").decode().strip())
            if (self.root / grafts).exists():
                return
            self.head = head
            self.git_config = hashlib.sha256(self.git("--version") + self.git("config", "--null", "--list")).hexdigest()
            base = previous.get("head")
            if self.git_config != previous.get("git_config") or not isinstance(base, str) or not re.fullmatch(r"[a-f0-9]{40,64}", base):
                return
            if base != head:
                self.git("merge-base", "--is-ancestor", base, head)
                span = f"{base}..{head}"
                if self.git("rev-list", "--max-count=1", "--merges", span):
                    return
                changed = self.git("log", "--format=", "--name-only", "-z", "--no-renames", span, "--", "content/daily")
                self.changed = set(changed.decode("utf-8").split("\0"))
            self.previous_times = previous.get("times")
        except (OSError, ValueError, subprocess.SubprocessError):
            return

    def render(self, relative, body, renderer):
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        cached = self.previous_html.get(relative) if isinstance(self.previous_html, dict) else None
        if isinstance(cached, list) and len(cached) == 2 and cached[0] == digest and isinstance(cached[1], str):
            html = cached[1]
            self.render_hits += 1
        else:
            html = renderer(body)
        self.html[relative] = [digest, html]
        return html

    def saved_times(self, relative, include_first):
        if relative in self.changed or not isinstance(self.previous_times, dict):
            return None
        record = self.previous_times.get(relative)
        if not isinstance(record, list) or len(record) != 2 or not record[1] or (include_first and not record[0]):
            return None
        return record

    def save(self):
        data = {"head": self.head, "git_config": self.git_config, "renderer": self.renderer, "html": self.html, "times": self.times}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)
        print(f"日报渲染复用 {self.render_hits} 项，Git 时间复用 {self.time_hits} 项。")
