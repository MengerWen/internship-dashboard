"""只读定位历史文件读写动作及回执，不执行会话中的任何工具或指令。"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.collect_journal_sessions import local_time
except ModuleNotFoundError:
    from collect_journal_sessions import local_time

ROOT = Path(__file__).resolve().parents[1]


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
                    parts = record.get('message', {}).get('content', []) if platform == 'claude' else [record.get('payload', {})]
                    if not isinstance(parts, list):
                        continue
                    for part in parts:
                        kind = part.get('type')
                        if kind in ('tool_use', 'function_call', 'custom_tool_call'):
                            counts['tool_calls'] += 1
                            name = part.get('name', '')
                            args = part.get('input') or part.get('arguments') or ''
                            touched = targets(name, args)
                            if not touched:
                                continue
                            digest = hashlib.sha256(raw).hexdigest()
                            call_id = part.get('id') or part.get('call_id')
                            calls[call_id] = digest
                            if digest in seen:
                                continue
                            seen.add(digest)
                            try:
                                stamp = local_time(record.get('timestamp'))
                            except ValueError:
                                stamp = None
                            actions.append({'id': digest, 'platform': platform,
                                'session_id': record.get('sessionId') or meta.get('id') or session['session_id'],
                                'file': filename, 'line': number, 'byte_offset': offset, 'line_sha256': digest,
                                'timestamp': stamp, 'date': stamp[:10] if stamp else None,
                                'date_status': 'message-timestamp' if stamp else 'missing-timestamp',
                                'cwd': record.get('cwd') or meta.get('cwd') or session.get('cwd'),
                                'tool_name': name, 'call_id': call_id, 'targets': touched, 'receipt': None})
                        elif kind in ('tool_result', 'function_call_output', 'custom_tool_call_output'):
                            counts['tool_receipts'] += 1
                            call_id = part.get('tool_use_id') or part.get('call_id')
                            digest = calls.get(call_id)
                            if digest:
                                action = next((a for a in reversed(actions) if a['id'] == digest), None)
                                if action and action['receipt'] is None:
                                    result = part.get('content') if platform == 'claude' else part.get('output')
                                    action['receipt'] = {'line': number, 'line_sha256': hashlib.sha256(raw).hexdigest(),
                                        'is_error': bool(part.get('is_error') or part.get('isError')),
                                        'preview': str(result)[:600]}
        except (OSError, ValueError, TypeError) as exc:
            failures.append({'file': filename, 'error': str(exc)})
    return {'schema_version': 1, 'actions': actions, 'counts': dict(counts), 'failures': failures,
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
