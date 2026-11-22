"""Compatibility calls for report generators using the dashboard C++ navigation tool."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "content/daily"
ASSETS = ROOT / "scripts/nav_scrollspy"
MARKER = "data-nav-scrollspy"
SCRIPT = (ASSETS / "script.html").read_text(encoding="utf-8")
_rows = [line.split("\t") for line in (ASSETS / "policy.tsv").read_text(encoding="utf-8").splitlines()]
_values = {row[0]: row[1] for row in _rows if len(row) == 2}
PAPER, DARK, SUPERSEDED = _values["paper"] + "\n", _values["dark"] + "\n", _values["superseded"]
PAGES = {row[1]: {"none": None, "paper": PAPER, "dark": DARK}[row[2]] for row in _rows if row[0] == "page"}


def _tool() -> Path:
    tool = ROOT / ".local/native/bin" / ("nav_scrollspy.exe" if os.name == "nt" else "nav_scrollspy")
    if not tool.exists():
        subprocess.run(["node", str(ROOT / "scripts/workspace_inventory.cjs"), "--build"],
                       cwd=ROOT, stdout=sys.stderr, check=True)
    return tool


def _transform(args, data):
    process = subprocess.run([str(_tool()), *args], input=data, capture_output=True, cwd=ROOT)
    if process.returncode:
        reason = process.stderr.decode("utf-8", errors="replace").strip()
        if reason == "unterminated scrollspy block":
            raise ValueError(reason)
        raise SystemExit(reason)
    return process.stdout.decode("utf-8")


def strip(html: str) -> str:
    return _transform(["--strip"], html.encode("utf-8"))


def render(html: str, css: str | None, name: str) -> str:
    style = (css or "").encode("utf-8")
    return _transform(["--render", str(len(style)), name], style + html.encode("utf-8"))


def patch(path: Path, css: str | None) -> str:
    style = (css or "").encode("utf-8")
    return _transform(["--patch-file", str(len(style))], style + str(path.resolve()).encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return subprocess.run([str(_tool()), "--check" if args.check else "--apply"], cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
