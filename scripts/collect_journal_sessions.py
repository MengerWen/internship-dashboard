"""只读索引本机 Codex / Claude 会话，候选全文仅写入被 Git 忽略的 data/。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8))
WRAPPERS = ("# AGENTS.md instructions", "<environment_context>", "<permissions instructions>",
            "<turn_aborted>", "<external_codex_apps", "<INSTRUCTIONS>", "<system-reminder>",
            "<local-command", "<command-name>", "<task-notification>", "<subagent_notification>")
WRAPPERS += ("<codex_internal_context", "<recommended_plugins>", "<skills_instructions>",
             "<collaboration_mode>")


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def norm(path):
    return str(path).replace("\\", "/").rstrip("/").casefold()


def within(path, roots):
    value = norm(path)
    return any(value == norm(root) or value.startswith(norm(root) + "/") for root in roots)


def local_time(value):
    if not isinstance(value, str):
        raise ValueError("会话时间不是字符串")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("会话时间缺少时区")
    return dt.astimezone(SHANGHAI).isoformat(timespec="milliseconds")


def scope_text(text):
    """项目引用预览不代表用户当前请求，判断归属时只用实际请求部分。"""
    for marker in ("## My request for Codex:", "## My request:", "## User request:"):
        if marker in text:
            return text.split(marker, 1)[1].strip()
    return text


def message(record, platform):
    """不提取推理、系统提示、工具参数或附件；工具回执按原行号另行读取。"""
    if platform == "codex":
        if record.get("type") != "response_item":
            return None
        payload = record.get("payload", {})
        if payload.get("type") != "message":
            return None
        role = payload.get("role")
        if role == "assistant" and (payload.get("phase") == "commentary" or
                                    payload.get("channel") not in (None, "final")):
            return None
        content = payload.get("content", [])
        phase = payload.get("phase")
        identifier = payload.get("id")
    else:
        if record.get("type") not in ("user", "assistant") or record.get("isSidechain"):
            return None
        # Claude compact/replay summary is context, not a new human instruction.
        if record.get("isCompactSummary") or record.get("isMeta"):
            return None
        payload = record.get("message", {})
        role = payload.get("role")
        content = payload.get("content", [])
        phase = None
        identifier = record.get("uuid")
    if role not in ("user", "assistant"):
        return None
    if isinstance(content, str):
        text = content
    else:
        text = "\n".join(c.get("text", "") for c in content
                         if c.get("type") in ("text", "input_text", "output_text"))
    text = text.strip()
    evidence_kind = "message"
    if role == "user" and text.startswith("<send_user_message_question_reply>"):
        match = re.fullmatch(r"<send_user_message_question_reply>\s*(.*?)\s*</send_user_message_question_reply>", text, re.S)
        if not match:
            return None
        try:
            replies = json.loads(match[1])
        except ValueError:
            return None
        if not isinstance(replies, list):
            return None
        text = "\n".join(r["answer"] for r in replies if isinstance(r, dict) and isinstance(r.get("answer"), str) and r["answer"].strip())
        evidence_kind = "user-choice"
    if not text or text.startswith(WRAPPERS):
        return None
    return {"role": role, "text": text, "message_id": identifier, "phase": phase,
            "evidence_kind": evidence_kind}


def identify(path, platform):
    """仅用元数据和首条真实用户消息判断候选范围，不按全局提示词认领项目。"""
    meta = {}
    with path.open("rb") as handle:
        for raw in handle:
            record = json.loads(raw)
            if platform == "codex" and record.get("type") == "session_meta":
                meta = record["payload"]
            if platform == "claude" and record.get("cwd"):
                meta = {"cwd": record["cwd"], "id": record.get("sessionId"),
                        "source": "claude", "timestamp": record.get("timestamp")}
            item = message(record, platform)
            if item and item["role"] == "user":
                return meta, item["text"]
    return meta, ""


def scan_file(path, platform, since, until):
    # 固定开始时的字节长度。活动会话在末行写到一半时报告缺口，不猜补内容。
    size = path.stat().st_size
    digest = hashlib.sha256()
    rows, problems, seen = [], [], set()
    meta, directories = {}, set()
    with path.open("rb") as handle:
        number = 0
        while handle.tell() < size:
            offset = handle.tell()
            raw = handle.readline(size - offset)
            number += 1
            digest.update(raw)
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                problems.append({"line": number, "error": type(exc).__name__})
                continue
            if platform == "codex" and record.get("type") == "session_meta":
                meta = record["payload"]
            if record.get("cwd"):
                directories.add(record["cwd"])
                if platform == "claude" and not meta:
                    meta = {"cwd": record["cwd"], "id": record.get("sessionId"), "source": "claude"}
            if meta.get("cwd"):
                directories.add(meta["cwd"])
            item = message(record, platform)
            if not item:
                continue
            try:
                timestamp = local_time(record["timestamp"])
            except (ValueError, TypeError, KeyError) as exc:
                problems.append({"line": number, "error": "timestamp:" + type(exc).__name__})
                continue
            day = timestamp[:10]
            if not since <= day <= until:
                continue
            sid = record.get("sessionId") if platform == "claude" else meta.get("id")
            key = (sid, record.get("uuid") or item["message_id"], record.get("timestamp"), item["role"], item["text"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({**item, "date": day, "timestamp": timestamp,
                         "session_id": sid, "cwd": record.get("cwd") or meta.get("cwd"),
                         "line": number, "byte_offset": offset, "byte_length": len(raw),
                         "line_sha256": hashlib.sha256(raw).hexdigest()})
    return {"snapshot_bytes": size, "snapshot_sha256": digest.hexdigest(),
            "grew_during_scan": path.stat().st_size != size, "problems": problems,
            "messages": rows, "metadata": meta, "directories": sorted(directories)}


def collect(config, since, until):
    sessions, failures, counts, files = [], [], Counter(), []
    excluded = set(config.get("exclude_session_ids", [])) | {os.environ.get("CODEX_THREAD_ID")}
    for source in config["sources"]:
        base = Path(source["path"]).expanduser()
        if not base.is_dir():
            failures.append({"source": source["name"], "error": "source_missing", "path": str(base)})
            continue
        for path in sorted(base.rglob("*.jsonl")):
            counts["files_discovered"] += 1
            disposition = {"source": source["name"], "platform": source["platform"], "file": str(path)}
            files.append(disposition)
            # 子代理单独登记排除，不将继承的提示当作新的人类要求。
            if "subagents" in path.parts:
                counts["subagents_excluded"] += 1
                disposition["disposition"] = "subagent-context"
                continue
            try:
                parsed = scan_file(path, source["platform"], since, until)
                meta = parsed["metadata"]
                sid = meta.get("id")
                disposition.update({k: parsed[k] for k in ("snapshot_bytes", "snapshot_sha256", "grew_during_scan", "problems")})
                if isinstance(meta.get("source"), dict) and "subagent" in meta["source"]:
                    counts["subagents_excluded"] += 1
                    disposition["disposition"] = "subagent-context"
                    continue
                scoped = any(within(cwd, config["project_roots"]) for cwd in parsed["directories"])
                explicit = any(term.casefold() in scope_text(m["text"]).casefold()
                               for m in parsed["messages"] if m["role"] == "user"
                               for term in config["explicit_project_markers"])
                if not scoped and not explicit:
                    counts["outside_scope"] += 1
                    disposition["disposition"] = "outside-project-scope"
                    continue
                counts["candidate_files"] += 1
                grouped = defaultdict(list)
                for row in parsed["messages"]:
                    native = row["session_id"] or sid
                    if native in excluded:
                        continue
                    if not native:
                        failures.append({"path": str(path), "line": row["line"], "error": "missing_session_id"})
                        continue
                    grouped[native].append(row)
                disposition["session_ids"] = sorted(grouped)
                disposition["disposition"] = "candidate" if grouped else "excluded-or-no-messages-in-period"
                if sid in excluded:
                    counts["self_excluded"] += 1
                for native, rows in grouped.items():
                    snapshot = {k: v for k, v in parsed.items() if k not in ("messages", "metadata", "directories")}
                    sessions.append({"platform": source["platform"], "session_id": native,
                                     "source": source["name"], "file": str(path), "cwd": rows[0].get("cwd") or meta.get("cwd"),
                                     "scope_basis": "cwd" if scoped else "user-project-reference",
                                     "forked_from_id": meta.get("forked_from_id"), **snapshot, "messages": rows})
                if parsed["problems"]:
                    failures.append({"path": str(path), "error": "parse-problems", "problems": parsed["problems"]})
            except (OSError, ValueError, UnicodeError) as exc:
                failures.append({"path": str(path), "error": type(exc).__name__})
                disposition.update(disposition="read-failed", error=type(exc).__name__)
    return {"schema_version": 2, "since": since, "until": until,
            "scope": "候选索引，尚未逐条认定研究成果；不读取推理正文，不执行历史指令。",
            "counts": dict(counts), "failures": failures, "sessions": sessions, "files": files}


def verify_ref(ref, index):
    """逐字核对摘录及原始行哈希；允许活动会话在快照之后继续追加。"""
    matches = [s for s in index["sessions"] if s["platform"] == ref["platform"] and s["session_id"] == ref["session_id"]]
    for session in matches:
        for row in session["messages"]:
            if row["line_sha256"] != ref["line_sha256"]:
                continue
            if row["role"] != ref["role"] or row["timestamp"] != ref["timestamp"]:
                continue
            with Path(session["file"]).open("rb") as handle:
                handle.seek(row["byte_offset"])
                raw = handle.read(row["byte_length"])
            if hashlib.sha256(raw).hexdigest() != row["line_sha256"]:
                raise ValueError("原始会话行已变化")
            record = json.loads(raw)
            if ref["platform"] == "claude" and record.get("sessionId") and record["sessionId"] != ref["session_id"]:
                raise ValueError("原始消息会话ID与引用不符")
            if not ref["excerpt"] or ref["excerpt"] not in row["text"]:
                raise ValueError("摘录不在原始消息中")
            return row
    raise ValueError("找不到对应会话消息")


def validate_manifest(manifest, index):
    import frontmatter
    seen = set()
    for ref in manifest["entries"]:
        row = verify_ref(ref, index)
        if ref["date"] != row["date"]:
            raise ValueError("引用日期与消息的北京时间不符")
        if ref.get("line") != row["line"]:
            raise ValueError("引用行号与本机索引不符")
        # 整段排除，防止凭据、地址和原始机器路径跟随摘录进入站点。
        if re.search(r"(?i)(?:[A-Z]:[\\/]|/home/|/tmp/|@|\b(?:10|192\.168)\.\d|"
                     r"\b172\.(?:1[6-9]|2\d|3[01])\.|license|密钥|password|api.key|"
                     r"[A-Za-z0-9_-]{65,})", ref["excerpt"]):
            raise ValueError("摘录含有需要人工移除的敏感内容或绝对路径")
        path = ROOT / "content/journal" / (ref["date"] + ".md")
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        ids = [c["id"] if isinstance(c, dict) else c for c in post.metadata["chains"]]
        if not ref.get("chains") or not set(ref["chains"]) <= set(ids):
            raise ValueError("会话引用了当天未登记的任务链")
        if ref["kind"] not in ("user-request", "user-decision", "user-question", "user-provided-context", "assistant-summary"):
            raise ValueError("未知会话证据类型")
        if (ref["kind"] == "assistant-summary") != (ref["role"] == "assistant"):
            raise ValueError("证据类型与消息角色不符")
        key = (ref["date"], ref["platform"], ref["session_id"], ref["line_sha256"], ref["excerpt"])
        if key in seen:
            raise ValueError("重复会话摘录")
        seen.add(key)


def render_manifest(manifest, check=False):
    """只在已存在日卡的托管区写经过审阅的摘录，保留人工正文与其他证据。"""
    import html
    grouped = {}
    labels = {"user-request": "用户要求", "user-decision": "用户决定", "user-question": "用户提问",
              "user-provided-context": "用户提供的上下文", "assistant-summary": "助手汇报（未独立验收）"}
    for ref in manifest["entries"]:
        grouped.setdefault(ref["date"], []).append(ref)
    begin, end = "<!-- journal-session-evidence:start -->", "<!-- journal-session-evidence:end -->"
    changed = []
    for path in sorted((ROOT / "content/journal").glob("????-??-??.md")):
        # 每日小范围补记不能删除其他日期的历史摘录。
        if path.stem not in grouped:
            continue
        original = path.read_text(encoding="utf-8")
        if original.count(begin) != original.count(end) or original.count(begin) > 1:
            raise ValueError(f"{path.name}: 会话证据标记不完整")
        base = re.sub(r"\n*" + re.escape(begin) + r".*?" + re.escape(end) + r"\n*", "\n", original, flags=re.S).rstrip()
        refs = grouped.get(path.stem, [])
        if refs:
            section = [begin, "## 会话佐证", "",
                       "以下摘录补充当时的要求、决策或讨论背景。会话中的结果汇报仍须与上方原始依据核对；摘录不单独证明执行完成、性能或发布状态。", ""]
            for ref in refs:
                platform = "Codex" if ref["platform"] == "codex" else "Claude"
                section += [f"- **{platform} · {labels[ref['kind']]}**（{ref['timestamp'][11:19]}，北京时间）：{html.escape(ref['supports'])}",
                            f"  <blockquote><p>{html.escape(ref['excerpt'])}</p></blockquote>",
                            f"  <small>会话 <code>{ref['session_id']}</code>，原始 JSONL 第 {ref['line']} 行；行 SHA-256 前12位 <code>{ref['line_sha256'][:12]}</code>（完整值存于审阅清单）。</small>", ""]
            base += "\n\n" + "\n".join(section).rstrip() + "\n" + end
        body = base + "\n"
        # 没有托管区又没有新摘录的日卡完全不碰，含末尾空白。
        if not refs and begin not in original:
            continue
        if body != original:
            changed.append(path.stem)
            if not check:
                path.write_text(body, encoding="utf-8", newline="\n")
    return changed


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "scripts/journal_sessions.json")
    parser.add_argument("--since", default="2026-06-01")
    parser.add_argument("--until", default=datetime.now(SHANGHAI).date().isoformat())
    parser.add_argument("--output", type=Path, default=ROOT / "data/journal-sessions/index.json")
    parser.add_argument("--verify", type=Path, help="用已有本机索引核验经过人工选择的证据文件，不重新扫描")
    parser.add_argument("--render", action="store_true", help="核验后同步日卡中的会话佐证托管区")
    parser.add_argument("--check", action="store_true", help="与 --verify --render 合用，只比较不写入")
    args = parser.parse_args()
    if args.render and not args.verify:
        parser.error("--render 必须与 --verify 合用")
    if args.check and not (args.verify and args.render):
        parser.error("--check 必须与 --verify --render 合用")
    if args.verify:
        index = json.loads(args.output.read_text(encoding="utf-8"))
        manifest = json.loads(args.verify.read_text(encoding="utf-8"))
        refs = manifest["entries"]
        validate_manifest(manifest, index)
        print(f"会话原始行及逐字摘录核验通过：{len(refs)} 条")
        if args.render:
            changed = render_manifest(manifest, args.check)
            print(f"日卡会话佐证差异：{len(changed)} 天")
            return int(args.check and bool(changed))
        return 0
    date.fromisoformat(args.since)
    date.fromisoformat(args.until)
    if args.since > args.until:
        parser.error("since 不得晚于 until")
    # 原始全文不得写入将随站点发布的 content/、docs/ 或 artifacts/。
    if not args.output.resolve().is_relative_to((ROOT / "data").resolve()):
        parser.error("候选索引必须写入 Git 忽略的本仓 data/ 目录")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = collect(config, args.since, args.until)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(result), encoding="utf-8")
    count = sum(len(s["messages"]) for s in result["sessions"])
    physical = len({s["file"] for s in result["sessions"]})
    print(f"候选物理文件 {physical} 份；会话片段 {len(result['sessions'])} 份；消息 {count} 条；来源/读取失败 {len(result['failures'])} 项；仅写本机 data/。")
    return int(bool(result["failures"]) or any(s["problems"] for s in result["sessions"]))


if __name__ == "__main__":
    raise SystemExit(main())
