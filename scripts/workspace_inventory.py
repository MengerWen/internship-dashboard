"""只读盘点未跟踪文件及本项目临时输出，不执行删除或修改 Git 状态。"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def scan_tree(root: Path) -> dict:
    result = {"files": 0, "bytes": 0, "links": [], "errors": []}
    if not root.exists() and not root.is_symlink():
        return result
    if is_link(root):
        result["links"].append(str(root))
        return result

    def on_error(error: OSError) -> None:
        result["errors"].append(str(error))

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=on_error):
        for name in list(dirs):
            child = Path(directory) / name
            try:
                if is_link(child):
                    result["links"].append(str(child.relative_to(root)))
                    dirs.remove(name)
            except OSError as error:
                on_error(error)
                dirs.remove(name)
        for name in files:
            child = Path(directory) / name
            try:
                if is_link(child):
                    result["links"].append(str(child.relative_to(root)))
                    continue
                result["files"] += 1
                result["bytes"] += child.stat().st_size
            except OSError as error:
                on_error(error)
    return result


def inventory(root: Path) -> dict:
    process = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root, check=True, capture_output=True,
    )
    paths = [item.decode("utf-8") for item in process.stdout.split(b"\0") if item]
    groups = defaultdict(lambda: {"entries": 0, "bytes": 0})
    errors = []
    for relative in paths:
        group = "/".join(relative.rstrip("/").split("/")[:2])
        groups[group]["entries"] += 1
        try:
            path = root / relative
            if path.is_file() and not is_link(path):
                groups[group]["bytes"] += path.stat().st_size
        except OSError as error:
            errors.append(str(error))
    local = scan_tree(root / ".local" / "runs")
    return {
        "untracked_entries": len(paths),
        "untracked": paths,
        "groups": [{"path": name, **value} for name, value in sorted(groups.items())],
        "local_runs": local,
        "errors": errors,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--check", action="store_true", help="有未跟踪条目、扫描问题或超出容量时返回非零")
    parser.add_argument("--max-local-mib", type=int, default=1024, help="临时输出容量上限，默认 1024 MiB")
    args = parser.parse_args()
    if args.max_local_mib < 0:
        parser.error("容量上限必须非负")
    result = inventory(ROOT)
    local = result["local_runs"]
    result["local_limit_bytes"] = args.max_local_mib * 1024 * 1024
    result["ok"] = not (
        result["untracked_entries"] or result["errors"] or local["errors"] or local["links"]
        or local["bytes"] > result["local_limit_bytes"]
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'未跟踪条目：{result["untracked_entries"]}')
        print(f'临时输出：{local["files"]} 个文件，{local["bytes"] / 1024 ** 2:.2f} MiB')
        for group in result["groups"]:
            print(f'  {group["path"]}: {group["entries"]} 项，{group["bytes"] / 1024 ** 2:.2f} MiB')
        if result["errors"] or local["errors"] or local["links"]:
            print("存在读取错误或链接，请使用 --json 查看；本命令不会跟随链接。")
    return int(args.check and not result["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
