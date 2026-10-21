"""从固定 Git 快照采集逐条提交；任务归属及计量另行审阅。"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import subprocess
import re
import argparse
import hashlib
from collections import defaultdict
from fractions import Fraction
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(repo), *args],
                          capture_output=True, encoding="utf-8", errors="strict", check=True).stdout


def inventory(config):
    commits = []
    for source in config["repos"]:
        repo = (ROOT / source["path"]).resolve()
        revision = source["revision"]
        raw = git(repo, "log", revision, "--since=" + config["since"],
                  "--format=%x1e%aI%x00%H%x00%s", "--name-status", "--no-renames", "-z")
        for record in raw.split("\x1e")[1:]:
            timestamp, sha, rest = record.split("\0", 2)
            subject, *fields = rest.split("\0")
            fields = [p.strip("\n") for p in fields if p.strip("\n")]
            changes = {fields[i + 1]: fields[i] for i in range(0, len(fields), 2)}
            if prefix := source.get("only_under"):
                changes = {p[len(prefix):]: status for p, status in changes.items() if p.startswith(prefix)}
            paths = list(changes)
            day = datetime.fromisoformat(timestamp).astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
            if not paths or day < config["since"]:
                continue
            commits.append({"repo": source["name"], "revision": revision, "sha": sha,
                            "date": day, "timestamp": timestamp, "subject": subject,
                            "paths": sorted(set(paths)), "changes": changes})
    return sorted(commits, key=lambda c: (c["date"], c["repo"], c["timestamp"], c["sha"]))


def classify(commit, rules):
    """命名明确的专用文件定目标；公共代码随本次目标，不随所有消费者。"""
    repo, day, subject = commit["repo"], commit["date"], commit["subject"]
    override = rules.get("overrides", {}).get(commit["sha"])
    if override:
        return override
    if day > rules["reviewed_through"]:
        return {"status": "pending", "chains": [], "reason": "超出本轮已审阅日期；先核对新提交目标再扩展规则，不自动沿用历史归属"}
    if re.search(r"移动PLAN|consolidate.*plans|同步.*报告、计划与术语|整理.*PLAN.*架构", subject, re.I):
        return {"status": "maintenance", "chains": [], "reason": "归档或移动既有计划/报告；不把复制、改路径重复计为多项研究"}
    if repo == "sirui-quant-research" and day == "2026-07-14":
        return {"status": "mirror", "chains": [], "reason": "研究仓初始导入，既有实现已在父仓提交；避免复制历史计重"}
    if re.search(rules["unrelated"], subject, re.I):
        return {"status": "excluded", "chains": [], "reason": "本次研究范围之外的工具事项"}
    paths = [p for p in commit["paths"] if not re.search(rules["unrelated"], p, re.I)]
    material = [p for p in paths if not re.search(rules["non_task_paths"], p, re.I)]
    if not material:
        return {"status": "maintenance", "chains": [], "reason": "只有仓库规则、依赖、缓存或子仓指针；不重复作为任务产出计重"}
    if all(re.search(r"\.pem$|^docs/agents/|^\.pytest_tmp/", p, re.I) for p in material):
        return {"status": "maintenance", "chains": [], "reason": "凭据文件、代理配置或测试临时产物维护；不计作研究任务"}
    matches = [(cid, pattern) for cid, pattern in rules["subject_rules"] if re.search(pattern, subject, re.I)]
    subject_chain = matches[0][0] if matches else None
    if repo == "internship-dashboard":
        allowed = {"research-journal", "report328", "model-report", "visual-b", "report-tags"}
        subject_chain = subject_chain if subject_chain in allowed else None
        if not subject_chain:
            for cid, pattern in rules["path_rules"]:
                if cid in allowed and any(re.search(pattern, p, re.I) for p in material):
                    subject_chain = cid
                    break
        chain = subject_chain or ("dashboard-build" if day <= "2026-07-13" else "report-publish")
        return {"status": "assigned", "chains": [chain], "reason": "看板提交按本次制作/交互目标归属；报告主题不转记为研究计算", "anchors": material[:12]}
    if subject_chain in {"report328", "model-report", "visual-b", "report-tags", "research-journal"}:
        subject_chain = None
    anchors = defaultdict(list)
    common = []
    for path in material:
        # 模块名含原研究名不代表本次改动仍以原目标为主。
        shared = re.search(r"(?:src/algobench/|tests/|scripts/)(?:test_)?(?:formal_|event_prestate|run_guarded|run_formal|run_open5m_raw_bank|run_open5m_kernel_calibration|run_open5m_selected_date_calibration|run_open5m_real_data_calibration)|lv2_snapshot_workspace/(?:src|tests)/|PLAN/(?:RUNBOOK|factor_preregister)", path, re.I)
        if shared:
            common.append(path)
            continue
        for cid, pattern in rules["path_rules"]:
            if cid in {"report328", "model-report", "visual-b", "report-tags", "research-journal"}:
                continue
            if re.search(pattern, path, re.I):
                if cid == "ml-count" and day > "2026-08-10":
                    cid = "ml-exec"
                if cid == "old-factor-bank" and day < "2026-09-07":
                    cid = "open5m"
                anchors[cid].append(path)
                break
    if subject_chain == "old-factor-bank" and day < "2026-09-07":
        subject_chain = "open5m"
    if subject_chain:
        # 专用文件代表明确的其他交付；同一主线的旧说明与公共代码则作支持证据。
        anchors.setdefault(subject_chain, [])
    chains = sorted(anchors)
    if subject_chain:
        related = []
        for cid in list(anchors):
            if cid == subject_chain:
                continue
            independent = any(commit.get("changes", {}).get(p) == "A" and
                              re.search(r"^(?:PLAN/|docs/plans/|reports/|decisions/)", p) and p.endswith(".md")
                              for p in anchors[cid])
            if not independent:
                related.append(cid)
                del anchors[cid]
        chains = sorted(anchors)
    if not chains:
        for context in rules.get("context_rules", []):
            if (context["repo"] == repo and context["start"] <= day <= context["end"]
                    and any(re.search(context["path"], p, re.I) for p in material)):
                return {"status": "assigned", "chains": [context["chain"]],
                        "reason": context["reason"], "context_rule": context["id"],
                        "anchors": material[:12]}
        return {"status": "pending", "chains": [], "reason": "只有公共代码或含义不明的标题，缺少可独立确认的任务目标", "anchors": material[:12]}
    return {"status": "shared" if len(chains) > 1 else "assigned", "chains": chains,
            "reason": "专用文件路径及提交主题标识本次目标；公共代码计入本次目标" if len(chains) == 1 else "同一提交有多个明确目标，按目标数等分一份提交量",
            "anchors": dict(anchors), "subject_chain": subject_chain,
            "related_chains": related if subject_chain else []}


def attribute(commits, rules):
    ledger = []
    for commit in commits:
        result = classify(commit, rules)
        if result["chains"] and commit["repo"] != "internship-dashboard":
            primary = result.get("subject_chain")
            remapped = {}
            for cid in result["chains"]:
                mapped = phase_chain(cid, commit, primary)
                remapped[cid] = mapped
            if any(cid != value for cid, value in remapped.items()):
                result["phase_mapping"] = remapped
                result["reason"] += "；同名公共模块按本次有界实施阶段归属，保留映射供复核"
                result["chains"] = sorted(set(remapped.values()))
                result["status"] = "shared" if len(result["chains"]) > 1 else "assigned"
        chains = result["chains"]
        shares = {cid: {"numerator": 1, "denominator": len(chains)} for cid in chains}
        ledger.append({**commit, **result, "shares": shares})
    return ledger


def phase_chain(cid, commit, primary=None):
    day, repo, subject = commit["date"], commit["repo"], commit["subject"]
    # 时间只限定已核实的代码阶段，不单独给未知提交选任务。
    stage = next((c for start, end, c in [
        ("2026-07-15", "2026-07-25", "formal-engine"),
        ("2026-07-27", "2026-08-02", "gates"),
        ("2026-08-03", "2026-08-05", "fixed-history"),
        ("2026-08-06", "2026-09-18", "open5m"),
    ] if start <= day <= end), cid)
    if cid in {"formal-engine", "replay", "gates", "fixed-history", "open5m"} and day < "2026-08-11":
        return "algobench" if repo == "Quant_Research-Trading" and "2026-07-06" <= day <= "2026-07-14" else stage
    if cid == "replay" and day < "2026-10-17":
        return "open5m" if day <= "2026-09-06" else "old-factor-bank" if day <= "2026-09-12" else primary if primary in {"sse-v2", "szse-model328", "grouped-calibration"} else cid
    if cid == "ml-330" and day < "2026-09-20":
        return "ml-exec"
    if cid == "ml-exec" and "2026-09-20" <= day <= "2026-09-21":
        return "ml-330"
    if cid == "sse-v2" and day < "2026-09-23":
        return "lv2-snapshot" if day <= "2026-07-08" else "formal-engine" if day <= "2026-07-25" else "cancel-phase"
    if cid == "lv2-snapshot" and day > "2026-07-08":
        return "formal-engine" if day <= "2026-07-25" else "sse-v2" if day < "2026-10-17" else "replay"
    if cid == "literature" and repo == "sirui-quant-research":
        return "formal-engine" if day <= "2026-07-25" else "open5m" if day <= "2026-09-18" else "replay"
    if cid == "onboarding" and day >= "2026-10-14":
        return "sse-v2"
    if cid == "gates" and day >= "2026-08-06":
        return "open5m"
    if cid in {"formal-engine", "ml-exec", "cross-stock-sync"} and day >= "2026-10-19":
        return "replay"
    if cid == "formal-engine" and "2026-08-11" <= day <= "2026-08-20":
        return "ml-exec"
    if cid == "open5m" and day >= "2026-10-07":
        if primary == "corrected-replay-344":
            return "corrected-replay-344"
        if primary in {"replay", "sse-v2", "szse-model328", "grouped-calibration"}:
            return primary
        if day <= "2026-10-12":
            return "grouped-calibration"
    return cid


def summarize_day(payload, valid_chains):
    """用有理数核对守恒；展示层只接收已验证的汇总，不自行猜归属。"""
    totals, direct, shared = defaultdict(Fraction), Counter(), Counter()
    statuses, repos, seen = Counter(), Counter(), set()
    for item in payload["items"]:
        if item["status"] not in {"assigned", "shared", "pending", "maintenance", "mirror", "excluded"}:
            raise ValueError("归属状态无效")
        identity = (item["repo"], item["sha"])
        if identity in seen or not re.fullmatch(r"[a-f0-9]{40}", item["sha"]):
            raise ValueError("重复或无效提交身份")
        seen.add(identity)
        if item["date"] != payload["date"]:
            raise ValueError("提交日期不属于本日")
        statuses[item["status"]] += 1
        repos[item["repo"]] += 1
        amount = Fraction()
        for cid, share in item["shares"].items():
            if cid not in valid_chains or type(share["numerator"]) is not int or type(share["denominator"]) is not int:
                raise ValueError("归属链或份额类型无效")
            if share["denominator"] <= 0:
                raise ValueError("提交份额分母必须为正数")
            value = Fraction(share["numerator"], share["denominator"])
            if not 0 < value <= 1:
                raise ValueError("提交份额超出范围")
            amount += value
            totals[cid] += value
            (shared if len(item["shares"]) > 1 else direct)[cid] += 1
        if amount != (1 if item["status"] in {"assigned", "shared"} else 0):
            raise ValueError("单条提交份额不守恒")
    return {"total_commits": len(seen), "repos": dict(repos), "statuses": dict(statuses),
            "chains": {cid: {"value": float(totals[cid]), "direct": direct[cid], "shared": shared[cid],
                               "numerator": totals[cid].numerator, "denominator": totals[cid].denominator}
                       for cid in sorted(totals)}}


def public_days(ledger, config, rules):
    from scripts.collect_journal_evidence import redact
    days = defaultdict(list)
    for item in ledger:
        # 完整文件清单保留在本地盘点；页面给出目标锚点与可核对完整差异的SHA。
        row = {k: v for k, v in item.items() if k not in {"paths", "changes", "timestamp", "revision"}}
        row["basis"] = "专项复核" if item["sha"] in rules["overrides"] else "阶段上下文" if item.get("context_rule") else "主题与专用文件"
        anchors = item.get("anchors")
        if isinstance(anchors, dict):
            anchors = list(dict.fromkeys(p for values in anchors.values() for p in values))
        row["paths"] = (anchors or item["paths"])[:12]
        row.pop("anchors", None)
        days[item["date"]].append(row)
    config_fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    rules_fingerprint = hashlib.sha256(json.dumps(rules, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {day: redact({"schemaVersion": 1, "date": day, "method": rules["method"],
                         "source_config_sha256": config_fingerprint, "rules_sha256": rules_fingerprint,
                         "revisions": {s["name"]: s["revision"] for s in config["repos"]}, "items": items},
                        config["redact"], Counter()) for day, items in days.items()}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "scripts/journal_repos.json").read_text(encoding="utf-8"))
    commits = inventory(config)
    target = ROOT / "artifacts/journal-task-weight"
    target.mkdir(parents=True, exist_ok=True)
    (target / "commit-inventory.json").write_text(json.dumps(commits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rules = json.loads((ROOT / "scripts/journal_attribution_rules.json").read_text(encoding="utf-8"))
    ledger = attribute(commits, rules)
    (target / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    days = public_days(ledger, config, rules)
    destination = ROOT / "content/journal/_attribution"
    valid_chains = {c["id"] for c in json.loads((ROOT / "content/chains.json").read_text(encoding="utf-8"))["chains"]}
    different = []
    for day, payload in sorted(days.items()):
        summary = summarize_day(payload, valid_chains)
        evidence = json.loads((ROOT / "content/journal/_evidence" / (day + ".json")).read_text(encoding="utf-8"))
        if summary["repos"] != {r["repo"]: r["commits"] for r in evidence["repos"]}:
            raise ValueError(f"{day} 完整清单与既有固定采集的逐仓计数不一致")
        body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        path = destination / (day + ".json")
        if not path.exists() or path.read_text(encoding="utf-8") != body:
            different.append(day)
            if not args.check:
                destination.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8", newline="\n")
    print(json.dumps({"total": len(commits), "repos": Counter(c["repo"] for c in commits),
                      "statuses": Counter(c["status"] for c in ledger),
                      "days": len(days), "different": len(different),
                      "chains": Counter(cid for c in ledger for cid in c["chains"])}, ensure_ascii=False))
    if args.check and different:
        raise SystemExit(1)
