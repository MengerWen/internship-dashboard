"""只读定位历史文件读写动作及回执，不执行会话中的任何工具或指令。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.collect_journal_sessions import local_time
except ModuleNotFoundError:
    from collect_journal_sessions import local_time

ROOT = Path(__file__).resolve().parents[1]


def execution_status(platform, name, part, result):
    if part.get('is_error') or part.get('isError'):
        return 'failed'
    text = str(result)
    tool = name.rsplit('.', 1)[-1].lower()
    if platform == 'codex' and tool == 'apply_patch':
        exit_codes = re.findall(r'(?:Exit code:|"exit_code"\s*:)\s*(-?\d+)', text, re.I)
        if any(int(code) != 0 for code in exit_codes):
            return 'failed'
        return 'confirmed' if 'Success. Updated the following files:' in text else 'unconfirmed'
    if platform == 'claude' and tool in ('write', 'edit'):
        return 'confirmed' if re.search(r'(?:created|updated|written|applied) successfully|successfully (?:created|updated|written)', text, re.I) else 'unconfirmed'
    # exec返回完成只证明外壳结束；输入中的补丁可能只是引用或尚未成功执行。
    return 'unconfirmed'


def targets(name, arguments):
    if isinstance(arguments, dict):
        if arguments.get('file_path'):
            return [{'operation': name.lower(), 'path': arguments['file_path']}]
        text = json.dumps(arguments, ensure_ascii=False)
    else:
        text = str(arguments)
    return [{'operation': op.lower(), 'path': path.strip()}
            for op, path in re.findall(r'\*\*\* (Add|Update|Delete) File: (.*?)(?:\\n|\n)', text)]


def collect(index):
    by_file = {s['file']: s for s in index['sessions']}
    actions, failures, seen, counts = [], [], set(), Counter()
    actions_by_id = {}
    for filename, session in sorted(by_file.items()):
        meta = {}
        calls = {}
        size = session['snapshot_bytes']
        try:
            with Path(filename).open('rb') as handle:
                number = 0
                while handle.tell() < size:
                    offset = handle.tell()
                    raw = handle.readline(size - offset)
                    number += 1
                    try:
                        record = json.loads(raw)
                    except ValueError:
                        continue
                    if record.get('type') in ('session_meta', 'turn_context'):
                        meta.update(record.get('payload', {}))
                    platform = session['platform']
                    event = record.get('payload', {})
                    native = event.get('item', {})
                    if platform == 'codex' and event.get('type') == 'item_completed' and str(native.get('type', '')).replace('_', '').lower() == 'filechange':
                        digest = hashlib.sha256(raw).hexdigest()
                        identity = hashlib.sha256((digest + '\0native-file-change\0' + str(native.get('id'))).encode()).hexdigest()
                        if identity in seen:
                            continue
                        seen.add(identity)
                        changes = native.get('changes', {})
                        if isinstance(changes, dict):
                            touched = []
                            for p, v in changes.items():
                                touched.append({'operation': 'delete' if v.get('move_path') else v.get('type', 'update').lower(), 'path': p})
                                if v.get('move_path'):
                                    touched.append({'operation':'add', 'path':v['move_path']})
                        else:
                            touched = [{'operation': (v.get('kind') or {}).get('type', 'update').lower(), 'path':v['path']} for v in changes]
                        try:
                            stamp = (local_time(datetime.fromtimestamp(event['completed_at_ms']/1000, timezone.utc).isoformat())
                                     if event.get('completed_at_ms') is not None else local_time(record.get('timestamp')))
                        except (ValueError, TypeError, KeyError, OverflowError):
                            stamp = None
                        confirmed = native.get('status') == 'completed'
                        actions.append({'id': identity, 'platform': platform, 'session_id': event.get('thread_id') or meta.get('id') or session['session_id'],
                            'file': filename, 'line': number, 'byte_offset': offset, 'line_sha256': digest,
                            'timestamp': stamp, 'date': stamp[:10] if stamp else None,
                            'date_status': 'native-completion-timestamp' if stamp else 'missing-timestamp',
                            'cwd': meta.get('cwd') or session.get('cwd'), 'tool_name': 'native-file-change',
                            'call_id': native.get('id'), 'native_item_id': native.get('id'), 'target_basis': 'native-file-change', 'targets': touched,
                            'receipt': {'line': number, 'line_sha256': digest, 'is_error': not confirmed,
                                        'execution_status': 'confirmed' if confirmed else 'failed', 'timestamp': stamp,
                                        'preview': str(native.get('status'))}})
                        counts['native_file_changes'] += 1
                        continue
                    parts = record.get('message', {}).get('content', []) if platform == 'claude' else [record.get('payload', {})]
                    if not isinstance(parts, list):
                        continue
                    for part_index, part in enumerate(parts):
                        kind = part.get('type')
                        if kind in ('tool_use', 'function_call', 'custom_tool_call'):
                            counts['tool_calls'] += 1
                            name = part.get('name', '')
                            args = part.get('input') or part.get('arguments') or ''
                            touched = targets(name, args)
                            if not touched:
                                continue
                            digest = hashlib.sha256(raw).hexdigest()
                            # Codex 的 id 是项目项身份，回执用 call_id；Claude 用工具 id。
                            call_id = (part.get('call_id') or part.get('id')) if platform == 'codex' else (part.get('id') or part.get('call_id'))
                            # Claude 一行可以包含多个工具调用；行哈希不能充当动作身份。
                            identity = hashlib.sha256((digest + '\0' + str(call_id or part_index)).encode()).hexdigest()
                            calls[call_id] = identity
                            if identity in seen:
                                continue
                            seen.add(identity)
                            try:
                                stamp = local_time(record.get('timestamp'))
                            except ValueError:
                                stamp = None
                            action = {'id': identity, 'platform': platform,
                                'session_id': record.get('sessionId') or meta.get('id') or session['session_id'],
                                'file': filename, 'line': number, 'byte_offset': offset, 'line_sha256': digest,
                                'timestamp': stamp, 'date': stamp[:10] if stamp else None,
                                'date_status': 'message-timestamp' if stamp else 'missing-timestamp',
                                'cwd': record.get('cwd') or meta.get('cwd') or session.get('cwd'),
                                'tool_name': name, 'call_id': call_id, 'target_basis': 'argument-pattern', 'targets': touched, 'receipt': None}
                            actions.append(action)
                            actions_by_id[identity] = action
                        elif kind in ('tool_result', 'function_call_output', 'custom_tool_call_output'):
                            counts['tool_receipts'] += 1
                            call_id = part.get('tool_use_id') or part.get('call_id')
                            digest = calls.get(call_id)
                            if digest:
                                action = actions_by_id.get(digest)
                                if action and action['receipt'] is None:
                                    result = part.get('content') if platform == 'claude' else part.get('output')
                                    try: stamp = local_time(record.get('timestamp'))
                                    except (ValueError, TypeError): stamp = None
                                    status = execution_status(platform, action['tool_name'], part, result)
                                    action['receipt'] = {'line': number, 'line_sha256': hashlib.sha256(raw).hexdigest(),
                                        'is_error': status == 'failed', 'execution_status': status, 'timestamp': stamp,
                                        'preview': str(result)[:600]}
        except (OSError, ValueError, TypeError) as exc:
            failures.append({'file': filename, 'error': str(exc)})
    return {'schema_version': 3, 'actions': actions, 'counts': dict(counts), 'failures': failures,
            'note': '历史文件动作定位。调用及返回不等于整个研究运行成功；完成状态仍核对正文、文件和专门运行收据。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21/sessions.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21/actions.json')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'data').resolve()):
        parser.error('历史工具信息仅写本机 data/')
    result = collect(json.loads(args.index.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"原始文件读写动作 {len(result['actions'])}；失败 {len(result['failures'])}")
    return int(bool(result['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
