"""按同日、同任务的已登记依据区分产物、交流和待核。"""

from datetime import datetime, timedelta, timezone
import re


CN_TZ = timezone(timedelta(hours=8))
SOURCE_URL = "https://github.com/MengerWen/internship-dashboard/blob/main/docs/journal-review/rebuild-2026-10-21/days/{date}.md"


def _hash(value, length):
    return isinstance(value, str) and re.fullmatch(rf"[a-f0-9]{{{length}}}", value) is not None


def _on_day(value, date):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.tzinfo is not None and stamp.astimezone(CN_TZ).date().isoformat() == date
    except (ValueError, AttributeError):
        return False


def point_evidence(date, cid, attribution, source_day, documents, repo_urls):
    """仅处理构建输入；不读取外部仓库或原始会话，不按零提交推断交流。"""
    commits, files, sessions = {}, {}, {}
    for item in (attribution or {}).get("items", []):
        share = item.get("shares", {}).get(cid, {})
        if (item.get("date") != date or item.get("status") != "assigned"
                or share.get("numerator", 0) <= 0 or share.get("denominator", 0) <= 0
                or not _hash(item.get("sha"), 40)):
            continue
        repo, sha = item.get("repo", ""), item["sha"]
        paths = item.get("paths", [])
        code = any(re.search(r"\.(py|js|mjs|cjs|ts|tsx|jsx|cpp|cc|c|h|rs|sql|ipynb)$", p, re.I) for p in paths)
        template = repo_urls.get(repo, "")
        url = template.replace("{sha}", sha) if template.startswith("https://github.com/") else ""
        commits[(repo, sha)] = {"kind": "commit", "title": item.get("subject") or sha[:8],
                               "url": url, "sha": sha, "repo": repo,
                               "label": "代码提交" if code else "提交"}
    for did in source_day.get("documents", []):
        doc = documents.get(did, {})
        if (cid not in doc.get("chains", []) or doc.get("disposition") != "primary"
                or not _hash(doc.get("sha256"), 64)):
            continue
        proofs = [p for p in doc.get("write_evidence", []) if p.get("date") == date
                  and _hash(p.get("receipt_line_sha256"), 64)
                  and p.get("operation") in {"add", "update", "write", "edit"}
                  and (p.get("basis") in {"native-file-change", "direct-tool-result", "claude-tool-result", "raw-write-receipt"}
                       or doc.get("date_status") == "confirmed-native-or-direct-receipt")]
        if not proofs:
            continue
        files[did] = {"kind": "document", "id": did, "title": doc.get("title") or doc.get("path", "文档"),
                      "path": doc.get("path", ""), "sha256": doc["sha256"],
                      "url": SOURCE_URL.format(date=date) + "#已确认写入的材料", "label": "文档写入记录"}
    for session in source_day.get("sessions", []):
        lines = [p for p in session.get("user_lines", [])
                 if _hash(p.get("sha256"), 64) and _on_day(p.get("time"), date)]
        if cid not in session.get("chains", []) or not lines or not session.get("id"):
            continue
        sessions[session["id"]] = {"kind": "session", "id": session["id"], "title": session.get("title") or "交流记录",
                                   "url": SOURCE_URL.format(date=date) + "#会话",
                                   "time": lines[0]["time"], "label": "原始会话登记"}
    status = "artifact" if commits or files else "discussion" if sessions else "pending"
    kinds = []
    if any(c["label"] == "代码提交" for c in commits.values()):
        kinds.append("代码")
    if commits:
        kinds.append("提交")
    if files:
        kinds.append("文档")
    if sessions:
        kinds.append("会话")
    # 完整提交仍由原始归属明细提供；首屏只保留少量可查入口。
    return {"status": status, "kinds": kinds, "commit_count": len(commits),
            "document_count": len(files), "session_count": len(sessions),
            "artifacts": list(files.values())[:2] + list(commits.values())[:2],
            "discussions": list(sessions.values())[:2]}
