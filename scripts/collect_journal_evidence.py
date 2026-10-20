"""本地采集研究日志证据；站点构建只消费产物，不调用本脚本。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def git(repo, *args):
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(repo), *args],
        capture_output=True, encoding="utf-8", errors="strict", check=True,
    )
    return result.stdout


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def collect_commits(repo, revision, since, only_under=None):
    # NUL 分隔路径，避免中文转义、空格与特殊文件名破坏解析。
    raw = git(repo, "log", revision, "--date=short", "--since=" + since,
              "--format=%x1e%ad%x00%H%x00%s", "--name-only", "-z")
    days = defaultdict(lambda: {"commits": 0, "paths": Counter(), "items": []})
    for record in raw.split("\x1e")[1:]:
        day, sha, rest = record.split("\0", 2)
        subject, *paths = rest.split("\0")
        paths = [p.strip("\n") for p in paths if p.strip("\n")]
        if only_under:
            paths = [p[len(only_under):] for p in paths if p.startswith(only_under)]
        if not paths or day < since:
            continue
        entry = days[day]
        entry["commits"] += 1
        entry["paths"].update("/".join(p.split("/")[:2]) for p in paths)
        if len(entry["items"]) < 10:
            entry["items"].append({"sha": sha, "subject": subject})
    return days


def redact(value, fragments, counts):
    if isinstance(value, str):
        # 相对路径与公开 GitHub 链接可保留；绝对路径、邮箱、内网地址整条隐去。
        if any(token.casefold() in value.casefold() for token in fragments) or re.search(
            r"(?:\b[A-Za-z]:[\\/]|\\\\|\b(?:10|192\.168)\.\d|\b172\.(?:1[6-9]|2\d|3[01])\.)", value
        ):
            counts["redacted"] += 1
            return "<已隐去>"
        return value
    if isinstance(value, (list, tuple)):
        return [redact(v, fragments, counts) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, fragments, counts) for k, v in value.items()}
    return value


def collect(config, since):
    days = defaultdict(lambda: {"repos": [], "plans": [], "reports_published": []})
    registry = json.loads((ROOT / "content/chains.json").read_text(encoding="utf-8"))
    notes = {}
    for path in sorted((ROOT / "content/journal").glob("????-??-??.md")):
        notes[path.stem] = frontmatter.loads(path.read_text(encoding="utf-8")).metadata
    spans = {}
    for chain in registry["chains"]:
        active = [d for d, meta in notes.items() if chain["id"] in meta.get("chains", [])]
        if active:
            spans[chain["id"]] = (min(active), max(active))
    reports = {}
    # 日期归档不等于工作日期。所有显式引用的汇报关闭“名义日”默认覆盖。
    explicitly_covered = {str(r) for m in notes.values() for r in m.get("reports_covering", [])}
    for path in sorted((ROOT / "content/daily").glob("????-??-??.md")):
        meta = frontmatter.loads(path.read_text(encoding="utf-8")).metadata
        reports[path.stem] = {"date": path.stem, **{k: str(meta.get(k) or "") for k in ("title", "summary", "stage")}}
    for source in config["repos"]:
        repo = (ROOT / source["path"]).resolve()
        revision = source.get("revision", "HEAD")
        for day, entry in collect_commits(repo, revision, since, source.get("only_under")).items():
            paths = sorted(entry["paths"].items(), key=lambda x: (-x[1], x[0]))
            days[day]["repos"].append({"repo": source["name"], "commits": entry["commits"],
                                      "commit_url": source["commit_url"], "top_paths": paths[:8],
                                      "items": entry["items"]})
        for folder in source.get("plan_dirs", []):
            paths = git(repo, "ls-tree", "-r", "--name-only", revision, "--", folder).splitlines()
            for name in sorted(paths):
                match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", Path(name).name)
                if not match or match[1] < since or any(s in match[2] for s in config["exclude_plan_slugs"]):
                    continue
                body = git(repo, "show", f"{revision}:{name}")
                title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), Path(name).stem)
                days[match[1]]["plans"].append({"repo": source["name"], "file": name, "title": title})
        if source["name"] == "internship-dashboard":
            for rday in reports:
                added = git(repo, "log", revision, "--diff-filter=A", "--format=%ad", "--date=short",
                            "--", f"content/daily/{rday}.md").splitlines()
                if added and added[-1] >= since:
                    days[added[-1]]["reports_published"].append(rday)
    covers = defaultdict(list)
    for day, meta in notes.items():
        for rday in meta.get("reports_covering", []):
            if str(rday) in reports:
                covers[day].append(str(rday))
    for rday in reports:
        if rday not in explicitly_covered and rday not in config.get("exclude_report_coverage", []):
            covers[rday].append(rday)
    for day in covers:
        days[day]
    rules = config.get("suggest", {})
    stage_tracks = {t["stage"]: t["id"] for t in registry["tracks"] if t.get("stage")}
    payloads = {}
    for day, ev in sorted(days.items()):
        if day < since:
            continue
        how = {}
        for chain in registry["chains"]:
            cid = chain["id"]
            if cid not in spans or not spans[cid][0] <= day <= spans[cid][1]:
                continue
            tokens = rules.get(cid, {}).get("tokens", [cid])
            if any(token.casefold() in p["file"].casefold() for p in ev["plans"] for token in tokens):
                how[cid] = "plan-token"
        if not how:
            paths = [p for r in ev["repos"] for p, count in r["top_paths"]]
            for cid, rule in rules.items():
                if cid in spans and spans[cid][0] <= day <= spans[cid][1] and any(
                    token in path for token in rule.get("paths", []) for path in paths
                ):
                    how[cid] = "path"
        if not how:
            tracks = {stage_tracks.get(reports[r]["stage"]) for r in covers[day]}
            for c in registry["chains"]:
                cid = c["id"]
                if cid in spans and spans[cid][0] <= day <= spans[cid][1] and c["track"] in tracks:
                    how[cid] = "stage"
        payloads[day] = {"date": day, "weekday": "周" + "一二三四五六日"[date.fromisoformat(day).weekday()],
                         **ev, "reports_covering": sorted(covers[day]),
                         "suggest": {"chains": list(how), "how": how}}
    return payloads, notes


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比较产物，不写文件")
    parser.add_argument("--since", help="只处理此日及以后的证据")
    parser.add_argument("--config", type=Path, default=ROOT / "scripts/journal_repos.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    since = args.since or config["since"]
    date.fromisoformat(since)
    payloads, notes = collect(config, since)
    target = ROOT / "content/journal/_evidence"
    counts = Counter()
    expected = {f"{d}.json": encode(redact(ev, config["redact"], counts)) for d, ev in payloads.items()}
    actual = {p.name: p.read_bytes().decode("utf-8") for p in target.glob("*.json") if p.stem >= since}
    changed = sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))
    if not args.check:
        target.mkdir(parents=True, exist_ok=True)
        for name, body in expected.items():
            (target / name).write_text(body, encoding="utf-8", newline="\n")
        for name in actual.keys() - expected.keys():
            (target / name).unlink()
    missing = [d for d in payloads if d not in notes]
    print(f"证据 {len(payloads)} 天；差异 {len(changed)} 个；隐去 {counts['redacted']} 条；待写 {len(missing)} 天")
    for d in missing:
        ev = payloads[d]
        title = next((p["title"] for p in ev["plans"]), next((i["subject"] for r in ev["repos"] for i in r["items"]), "待写"))
        print(d, ",".join(ev["suggest"]["chains"]), title)
    if args.check and changed:
        print("证据落后：", ", ".join(changed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
