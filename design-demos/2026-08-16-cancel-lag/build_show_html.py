#!/usr/bin/env python3
"""Embed the frozen visual JSON into the self-contained daily show page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    template = args.template.read_text(encoding="utf-8")
    if template.count("__VISUAL_DATA__") != 1:
        raise ValueError("template must contain exactly one visual-data placeholder")
    payload = json.loads(args.data.read_text(encoding="utf-8"))
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if "</script" in compact.lower():
        raise ValueError("visual data cannot contain a closing script tag")
    output = template.replace("__VISUAL_DATA__", compact)
    args.output.write_text(output, encoding="utf-8")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
