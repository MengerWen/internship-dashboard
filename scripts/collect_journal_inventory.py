"""只读核对独立会话登记；正文数据库投影与原始JSONL分别保存，缺口不签收。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collect_journal_sessions import SHANGHAI, WRAPPERS, scope_text, within, message

ROOT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def session_fingerprint(index):
    messages = sorted({(s['platform'], s['session_id'], m['line_sha256'], m.get('timestamp'), m.get('role'))
                       for s in index['sessions'] for m in s['messages']})
    files = sorted((f.get('platform'), f.get('file'), f.get('snapshot_sha256'), f.get('snapshot_bytes'), f.get('disposition'))
                   for f in index.get('files', []))
    return sha({'since': index.get('since'), 'until': index.get('until'), 'messages': messages, 'files': files})


def read_db(path):
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute('BEGIN')
    return conn


def projected_message(row):
    obj = json.loads(row['item_json'])
    kind = obj['type']
    if kind == 'userMessage':
        text = '\n'.join(c.get('text', '') for c in obj.get('content', []) if c['type'] == 'text')
        role = 'user'
    elif kind == 'agentMessage' and obj.get('phase') in (None, 'final', 'final_answer'):
        text, role = obj.get('text', ''), 'assistant'
    else:
        return None
    text = text.strip()
    if not text or text.startswith(WRAPPERS):
        return None
    stamp = datetime.fromtimestamp(row['created_at_ms'] / 1000, timezone.utc).astimezone(SHANGHAI)
    return {'evidence_format': 'codex-history-item', 'native_item_id': row['item_id'],
            'turn_id': row['turn_id'], 'item_json_sha256': hashlib.sha256(row['item_json'].encode()).hexdigest(),
            'timestamp': stamp.isoformat(timespec='milliseconds'), 'date': stamp.date().isoformat(),
            'date_evidence': 'thread_items.created_at_ms', 'role': role, 'text': text}


def official_archives(directory):
    pages = sorted(directory.glob('codex-archived-page-*.json'))
    if not pages:
        raise ValueError('缺少正式归档列表，不能只凭数据库或文件目录确认完整')
    threads, hashes = [], []
    for i, path in enumerate(pages):
        raw = path.read_bytes(); page = json.loads(raw)
        if not isinstance(page.get('threads'), list):
            raise ValueError('正式归档列表页无效')
        if bool(page.get('nextCursor')) != (i < len(pages) - 1):
            raise ValueError('正式归档列表翻页未结束或混入多个快照')
        threads.extend(page['threads']); hashes.append(hashlib.sha256(raw).hexdigest())
    ids = [t['id'] for t in threads]
    if len(ids) != len(set(ids)):
        raise ValueError('正式归档列表出现重复身份，需重新读取稳定快照')
    return threads, hashes


def collect(config, index, official_directory, output):
    settings = config['inventories']
    official, page_hashes = official_archives(official_directory)
    prior = {s['platform'] + ':' + s['session_id'] for s in index['sessions']}
    excluded = set(config.get('exclude_session_ids', [])) | {os.environ.get('CODEX_THREAD_ID')}
    db = read_db(Path(settings['codex_state']).expanduser())
    history = read_db(Path(settings['codex_history']).expanduser())
    captured = datetime.now(timezone.utc).isoformat()
    rows, messages, issues, tombstones = [], [], [], []
    markers = [s.casefold() for s in config['explicit_project_markers']]
    registered = [dict(r) for r in db.execute('SELECT id,rollout_path,created_at,updated_at,source,cwd,title,archived FROM threads ORDER BY id')]
    registered_ids = {r['id'] for r in registered}
    history_ids = {r[0] for r in history.execute('SELECT DISTINCT thread_id FROM thread_items')}
    for sid in sorted(history_ids - registered_ids):
        command = history.execute("SELECT item_json FROM thread_items WHERE thread_id=? AND item_type='commandExecution' ORDER BY rollout_ordinal LIMIT 1", (sid,)).fetchone()
        cwd = json.loads(command[0]).get('cwd', '') if command else ''
        registered.append({'id': sid, 'rollout_path': '', 'created_at': None, 'updated_at': None,
                           'source': 'history-only', 'cwd': cwd, 'title': None, 'archived': None})
    for record in registered:
        t = dict(record); key = 'codex:' + t['id']
        body = [m for r in history.execute("SELECT * FROM thread_items WHERE thread_id=? AND item_type IN ('userMessage','agentMessage') ORDER BY rollout_ordinal", (t['id'],))
                if (m := projected_message(r)) and index['since'] <= m['date'] <= index['until']]
        scoped = t['id'] in config.get('include_session_ids', []) or key in prior or within(t['cwd'], config['project_roots']) or any(
            any(term in scope_text(m['text']).casefold() for term in markers) for m in body if m['role'] == 'user')
        source = t['source']
        try: source = json.loads(source)
        except (ValueError, TypeError): pass
        sub = isinstance(source, dict) and 'subagent' in source
        parent = source.get('subagent', {}).get('thread_spawn', {}).get('parent_thread_id') if sub else None
        is_excluded = t['id'] in excluded
        disposition = ('excluded-audit-conversation' if is_excluded else 'subagent-context' if sub else
                       'project-candidate' if scoped else 'outside-project-scope')
        path_exists = Path(t['rollout_path']).is_file()
        turns = [dict(r) for r in history.execute('SELECT * FROM thread_turns WHERE thread_id=? ORDER BY rollout_ordinal', (t['id'],))]
        row = {**t, 'id': key, 'platform': 'codex', 'native_id': t['id'], 'parent_thread_id': parent,
               'scope': disposition, 'raw_path_exists': path_exists, 'in_session_snapshot': key in prior,
               'registration_state': 'registered' if t['id'] in registered_ids else 'history-only',
               'turn_count': len(turns), 'message_count': len(body), 'history_available': bool(body),
               'body_representation': 'JSONL+database-projection' if path_exists and body else
                                      'database-projection' if body else 'JSONL' if path_exists else 'metadata-only'}
        if scoped and not is_excluded:
            target = output / 'codex-history' / t['id']; target.mkdir(parents=True, exist_ok=True)
            hashes = []
            with (target / 'items.jsonl').open('w', encoding='utf-8', newline='\n') as handle:
                # 不导出推理正文；工具参数、回执和文件差异仅在本机保存。
                for r in history.execute("SELECT * FROM thread_items WHERE thread_id=? AND item_type!='reasoning' ORDER BY rollout_ordinal", (t['id'],)):
                    item = dict(r); item['item_json_sha256'] = hashlib.sha256(item['item_json'].encode()).hexdigest()
                    hashes.append(item['item_json_sha256']); handle.write(json.dumps(item, ensure_ascii=False) + '\n')
            (target / 'turns.json').write_text(json.dumps(turns, ensure_ascii=False, indent=2), encoding='utf-8')
            row['history_item_hashes_sha256'] = sha(hashes)
            messages.append({'id': key, 'scope': disposition, 'messages': body})
            if not path_exists and not body:
                issues.append({'id': key, 'kind': 'registered-body-unavailable'})
            if not sub and key not in prior and body:
                issues.append({'id': key, 'kind': 'not-in-reviewed-session-snapshot'})
        rows.append(row)
    db.close(); history.close()
    known = registered_ids
    for t in official:
        if t['id'] not in known:
            issues.append({'id': 'codex:' + t['id'], 'kind': 'official-list-without-local-registration'})

    native_files, raw_body_ids = {}, {}
    for source in config['sources']:
        if source['platform'] != 'claude': continue
        for path in Path(source['path']).expanduser().rglob('*.jsonl'):
            try:
                for raw in path.open('rb'):
                    try: item = json.loads(raw)
                    except ValueError: continue  # 原始JSONL的逐行错误仍由主采集器阻断。
                    if item.get('sessionId'):
                        native_files.setdefault(item['sessionId'], set()).add(str(path))
                        if message(item, 'claude') is not None:
                            raw_body_ids.setdefault(str(path), set()).add(item['sessionId'])
            except OSError as exc:
                issues.append({'id': sha(str(path)), 'kind': 'claude-raw-unreadable', 'error': type(exc).__name__})
    archive_indexes, metadata = [], []
    roots_seen = 0
    for root_name in settings['claude_desktop_roots']:
        root = Path(root_name).expanduser()
        if not root.is_dir(): continue
        roots_seen += 1; archive_ids = set(); present = set()
        for path in root.rglob('archived-sessions.idx'):
            raw = path.read_bytes(); obj = json.loads(raw)
            archive_ids.update(obj['archived'])
            archive_indexes.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'archived': obj['archived']})
        for path in root.rglob('deleted_*'):
            if path.is_file():
                tombstones.append({'path': str(path), 'id': path.name.removeprefix('deleted_'),
                                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for path in root.rglob('*.json'):
            raw = path.read_bytes(); obj = json.loads(raw)
            if not obj.get('sessionId'): continue
            sid = obj['sessionId']; present.add(sid)
            ids = {str(obj.get('cliSessionId') or ''), sid.removeprefix('local_')}
            ids.update(x for x in obj.get('bridgeSessionIds', []) if isinstance(x, str))
            files = sorted({p for s in ids for p in native_files.get(s, [])})
            body_ids = sorted({sid for path in files for sid in raw_body_ids.get(path, set())})
            own_body = bool(set(body_ids) & ids)
            scoped = any(within(obj.get(k) or '', config['project_roots']) for k in ('cwd', 'originCwd'))
            fields = ('sessionId','cliSessionId','cwd','originCwd','createdAt','lastActivityAt','isArchived',
                      'title','completedTurns','forkedFromSessionId','bridgeSessionIds','lastAssistantUuid',
                      'lastTurnReport','postTurnSummary')
            metadata.append({k: obj.get(k) for k in fields} | {'file_sha256': hashlib.sha256(raw).hexdigest()})
            row = {k: obj.get(k) for k in fields if k not in ('lastTurnReport', 'postTurnSummary')}
            row.update(id='claude-desktop:' + sid, platform='claude', native_id=obj.get('cliSessionId'),
                       indexed_archived=sid in archive_ids, raw_files=files, metadata_path=str(path),
                       raw_message_session_ids=body_ids, own_body_available=own_body,
                       metadata_sha256=hashlib.sha256(raw).hexdigest(), scope='project-candidate' if scoped else 'outside-project-scope',
                       body_representation=('JSONL' if own_body else 'JSONL-inherited-context' if files else 'metadata-only'),
                       in_session_snapshot=any('claude:' + s in prior for s in body_ids))
            rows.append(row)
            if scoped and not files:
                issues.append({'id': row['id'], 'kind': 'registered-body-unavailable'})
            elif scoped and obj.get('completedTurns') and not own_body:
                issues.append({'id': row['id'], 'kind': 'completed-turns-without-own-body'})
            elif scoped and not row['in_session_snapshot']:
                issues.append({'id': row['id'], 'kind': 'not-in-reviewed-session-snapshot'})
        for sid in archive_ids - present:
            issues.append({'id': 'claude-desktop:' + sid, 'kind': 'archive-index-without-metadata'})
    if not roots_seen:
        issues.append({'kind': 'claude-desktop-inventory-unavailable'})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'codex-messages.json').write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'claude-metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'schema_version': 1, 'captured_at': captured, 'session_snapshot_sha256': session_fingerprint(index),
            'coverage_status': 'open' if issues else 'covered', 'issues': issues, 'sessions': rows,
            'official_archived_ids': sorted('codex:' + t['id'] for t in official), 'official_page_sha256': page_hashes,
            'claude_archive_indexes': archive_indexes, 'claude_deleted_markers': tombstones,
            'failures': [], 'scope_note': '本机现存登记及正式归档列表交叉核对；数据库投影不冒充原始JSONL。'}


def validate_inventory(inventory, sessions):
    if inventory is None:
        raise ValueError('缺少独立会话清单核对；文件目录自我守恒不能证明来源齐全')
    if inventory.get('schema_version') != 1 or inventory.get('session_snapshot_sha256') != session_fingerprint(sessions):
        raise ValueError('独立清单与会话快照不匹配，必须重新核对')
    if inventory.get('coverage_status') != 'covered' or inventory.get('issues') or inventory.get('failures'):
        raise ValueError('独立会话清单仍有缺口，不能签收全部来源')
    present = {s['platform'] + ':' + s['session_id'] for s in sessions['sessions']}
    for row in inventory.get('sessions', []):
        if row['scope'] != 'project-candidate':
            continue
        if row['body_representation'] == 'metadata-only':
            raise ValueError('独立会话清单登记缺少正文，不能只改通过标记')
        identities = (['codex:' + str(row['native_id'])] if row['platform'] == 'codex' else
                      ['claude:' + str(sid) for sid in row.get('raw_message_session_ids', [row['native_id']])])
        if not any(identity in present for identity in identities):
            raise ValueError('独立清单中的会话未进入采集快照，不能只改通过标记')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'scripts/journal_sessions.json')
    parser.add_argument('--sessions', type=Path, required=True)
    parser.add_argument('--official', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'data').resolve()):
        parser.error('独立清单及正文只写本机data/')
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    result = collect(read(args.config), read(args.sessions), args.official, args.output)
    (args.output/'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['coverage_status'], 'registered': len(result['sessions']),
                      'issues': dict(Counter(i['kind'] for i in result['issues']))}, ensure_ascii=False))
    return int(result['coverage_status'] != 'covered')


if __name__ == '__main__':
    raise SystemExit(main())
