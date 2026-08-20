#!/usr/bin/env python3
"""Run the visual-data exporter over SSH stdin and save validated JSON locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--remote-python", required=True)
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--exporter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    command = (
        f"{args.remote_python} - --root {args.remote_root}"
    )
    completed = subprocess.run(
        ["ssh", args.host, command],
        input=args.exporter.read_text(encoding="utf-8"),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "remote exporter failed")
    payload = json.loads(completed.stdout)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
