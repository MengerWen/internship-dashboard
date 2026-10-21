"""将独立来源快照与审阅决议逐项对账；不从已有日卡反推采集范围。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import ntpath
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
WRITES = {'write', 'edit', 'add', 'update'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def canonical(path):
    from scripts.collect_journal_sessions import norm
    value = norm(path)
    alias = norm('D:/MG/！Internship/26 Summer/❗思瑞投资')
    if value == alias or value.startswith(alias + '/'):
        value = norm('D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资') + value[len(alias):]
    return value


def private(path):
    return bool(re.search(r'(^|/)(?:dating|[^/]*dating[^/]*)(/|\.|$)', path, re.I))


def supporting_route(row):
    """有名称的支持材料去向；不把路径命中当作完成或实际工作日证明。"""
    path = row['path'].lower()
    if private(path):
        return {'disposition': 'excluded', 'destination': ['excluded:non-research'],
                'reason': '其他项目或私人材料'}
    if row['kind'] == 'restricted-configuration':
        return {'disposition': 'restricted', 'destination': ['restricted:configuration'],
                'reason': '仅登记存在，不读取正文或发布路径'}
    rules = [
        (r'journal|chains|研究日志', 'research-journal'),
        (r'cross.stock|c33|c3\.3', 'cross-stock-sync'),
        (r'depth.match|c7\.1', 'depth-match'),
        (r'cancel.phase|cancel.lag|mechanical.cancel', 'cancel-phase'),
        (r'sse|沪市', 'sse-v2'),
        (r'corrected.replay|kernel.throughput|344', 'corrected-replay-344'),
        (r'model328|szse.factor', 'szse-model328'),
        (r'grouped|barra', 'grouped-calibration'),
        (r'ml_|intraday_ml|ml/', 'ml-exec'),
        (r'lowlat|clusterlob|factor_lab|论文|literature', 'literature'),
        (r'algobench', 'algobench'),
        (r'lv2_snapshot', 'lv2-snapshot'),
        (r'交易规则|米筐ricequant', 'onboarding'),
        (r'storage|cleanup|存储', 'storage-cleanup'),
        (r'doris', 'doris-migration'),
        (r'trading.window', 'trading-window-freeze'),
        (r'formal|scorer|pair', 'formal-engine'),
    ]
    for pattern, chain in rules:
        if re.search(pattern, path):
            return {'disposition': 'support', 'destination': ['chain:' + chain],
                    'reason': '任务相关代码、证据、数据、文献或历史副本；不独立计为成果'}
    family = row['path'].split('/')[0] if '/' in row['path'] else 'root'
    return {'disposition': 'support', 'destination': ['support:' + row['source'] + ':' + family],
            'reason': '项目公共支持材料；保留形态及目录归属，不推断单链贡献'}


def assert_exact(label, expected, actual):
    if len(actual) != len(set(actual)):
        raise ValueError(label + ' 存在重复身份')
    if set(expected) != set(actual):
        raise ValueError(f'{label} 未守恒：缺 {len(set(expected)-set(actual))}，多 {len(set(actual)-set(expected))}')


def reconcile(materials, sessions, actions, decisions, source_config, inventory=None):
    from scripts.collect_journal_inventory import validate_inventory
    validate_inventory(inventory, sessions)
    for name, obj in [('materials', materials), ('sessions', sessions), ('actions', actions)]:
        if obj.get('failures'):
            raise ValueError(name + ' 有读取失败，不能签收完整来源')
    files = materials['files']
    universe = sorted((x['id'], x.get('sha256'), x.get('bytes'), x['kind']) for x in files)
    if decisions.get('material_universe_sha256') != digest(universe):
        raise ValueError('材料范围或内容变化：先审阅新增、修改及删除材料，再更新决议指纹')
    message_universe = sorted({s['platform'] + ':' + s['session_id'] + ':' + m['line_sha256']
                              for s in sessions['sessions'] for m in s['messages']})
    if decisions.get('message_universe_sha256') != digest(message_universe):
        raise ValueError('消息范围变化：先审阅新消息，不能沿用旧会话归属自动签收')
    if any(x.get('changed_during_read') for x in files):
        raise ValueError('材料采集期间变化，必须重采或单独记录版本')
    file_ids = {x['id'] for x in files}
    if set(decisions['documents']) - file_ids:
        raise ValueError('文档决议引用不存在的材料')
    bases = {x['id']: str((ROOT / x['path']).resolve()) for x in source_config['sources']}
    paths = {canonical(bases[x['source']] + '/' + x['path']): x['id'] for x in files}
    write_dates = defaultdict(list)
    action_files = defaultdict(set)
    for action in actions['actions']:
        for target in action['targets']:
            path = target['path']
            if not re.match(r'^/?[A-Za-z]:', path):
                path = (action.get('cwd') or '') + '/' + path
            fid = paths.get(canonical(path))
            if fid:
                action_files[action['id']].add(fid)
            receipt = action.get('receipt')
            if (fid and target['operation'] in WRITES and receipt and receipt.get('timestamp')
                    and receipt.get('execution_status') == 'confirmed'):
                write_dates[fid].append({'date': receipt['timestamp'][:10], 'action': action['id'],
                    'operation': target['operation'], 'receipt_line_sha256': receipt['line_sha256']})
    file_rows = []
    primary_hashes = {}
    for fid, decision in decisions['documents'].items():
        row = next(x for x in files if x['id'] == fid)
        if decision['disposition'] == 'primary' and row.get('sha256'):
            primary_hashes.setdefault(row['sha256'], fid)
    for row in files:
        decision = decisions['documents'].get(row['id'])
        if decision:
            kind = decision['disposition']
            route = {'disposition': kind, 'destination': ['chain:' + c for c in decision['chains']]
                     or ['excluded:non-research'], 'reason': '逐项审阅决议', 'review_level': decision['review_level']}
        elif row.get('sha256') in primary_hashes:
            route = {'disposition': 'duplicate', 'destination': ['file:' + primary_hashes[row['sha256']]],
                     'reason': '与已登记材料字节完全相同'}
        else:
            route = supporting_route(row)
        file_rows.append({k: row[k] for k in ['id', 'source', 'path', 'kind', 'git_state']} |
                         {'sha256': row.get('sha256'), 'write_evidence': write_dates[row['id']],
                          'filename_dates': row.get('filename_dates', []), **route})
    by_file = {x['id']: x for x in file_rows}
    grouped = defaultdict(list)
    for session in sessions['sessions']:
        grouped[session['platform'] + ':' + session['session_id']].append(session)
    assert_exact('会话决议', grouped, list(decisions['sessions']))
    session_rows, message_rows = [], []
    seen_messages = set()
    for key, copies in sorted(grouped.items()):
        decision = decisions['sessions'][key]
        destinations = ['chain:' + c for c in decision['chains']]
        destinations = destinations or [decision['disposition'] + ':context']
        session_rows.append({'id': key, **decision, 'destination': destinations})
        for copy in copies:
            for msg in copy['messages']:
                identity = key + ':' + msg['line_sha256']
                if identity in seen_messages:
                    continue
                seen_messages.add(identity)
                message_rows.append({'id': identity, 'session': key, 'date': msg['date'],
                    'timestamp': msg['timestamp'], 'role': msg['role'], 'line': msg['line'],
                    'evidence_kind': msg.get('evidence_kind', 'message'),
                    'line_sha256': msg['line_sha256'], 'destination': destinations,
                    'disposition': decision['disposition']})
    session_map = {x['id']: x for x in session_rows}
    commit_rows = []
    file_by_path = {(x['source'], x['path']): x for x in file_rows}
    for commit in materials['commits']:
        destinations = set()
        for change in commit['changes']:
            f = file_by_path.get((commit['source'], change['path']))
            if f:
                destinations.update(f['destination'])
            else:
                destinations.add('history:' + commit['source'] + ':no-current-file')
        commit_rows.append({k: commit[k] for k in ['id', 'source', 'sha', 'date', 'author_timestamp', 'committer_timestamp']} |
                           {'destination': sorted(destinations), 'changes': len(commit['changes'])})
    action_rows = []
    for action in actions['actions']:
        destinations = {d for fid in action_files[action['id']] for d in by_file[fid]['destination']}
        if not destinations:
            session_key = action['platform'] + ':' + action['session_id']
            destinations.update(session_map.get(session_key, {}).get('destination', ['support:historical-tool-context']))
        action_rows.append({'id': action['id'], 'date': action['date'], 'date_status': action['date_status'],
                            'destination': sorted(destinations), 'files': sorted(action_files[action['id']])})
    assert_exact('材料', [x['id'] for x in files], [x['id'] for x in file_rows])
    assert_exact('提交', [x['id'] for x in materials['commits']], [x['id'] for x in commit_rows])
    assert_exact('工具动作', [x['id'] for x in actions['actions']], [x['id'] for x in action_rows])
    expected_messages = {s['platform'] + ':' + s['session_id'] + ':' + m['line_sha256']
                         for s in sessions['sessions'] for m in s['messages']}
    assert_exact('原始消息行', expected_messages, [x['id'] for x in message_rows])
    result = {'schema_version': 1, 'snapshots': materials['snapshots'],
              'source_coverage': {'status': inventory['coverage_status'], 'inventory_sha256': digest(inventory),
                                  'captured_at': inventory.get('captured_at')},
              'files': file_rows, 'sessions': session_rows, 'messages': message_rows,
              'commits': commit_rows, 'actions': action_rows,
              'directory_exclusions': materials['directory_exclusions'], 'session_files': sessions['files']}
    for rows in [file_rows, session_rows, message_rows, commit_rows, action_rows]:
        if any(not x['destination'] for x in rows):
            raise ValueError('空去向')
    return result


def public_ledger(ledger):
    """公开副本只保留身份、哈希及去向，完整定位保留在本机。"""
    out = {'schema_version': 1}
    if 'source_coverage' in ledger:
        out['source_coverage'] = ledger['source_coverage']
    for key in ['files', 'sessions', 'messages', 'commits', 'actions']:
        out[key] = [{k: v for k, v in row.items() if k not in
                     {'path', 'review_level', 'reason', 'index', 'filename_dates', 'write_evidence'}}
                    for row in ledger[key]]
    out['snapshots'] = [{k: v for k, v in row.items() if k != 'path'} for row in ledger.get('snapshots', [])]
    out['directory_exclusions'] = [{'source': row['source'], 'path_sha256': digest(row['path']),
                                    'reason': row['reason']} for row in ledger.get('directory_exclusions', [])]
    out['session_files'] = [{k: v for k, v in row.items() if k not in {'file', 'problems'}} |
                            {'file_sha256': digest(row['file']), 'problem_count': len(row.get('problems', []))}
                            for row in ledger.get('session_files', [])]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21')
    parser.add_argument('--decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21/dispositions.json')
    parser.add_argument('--public', type=Path)
    parser.add_argument('--inventory', type=Path, required=True, help='独立清单核对结果；存在正文缺口时拒绝完整签收')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'data').resolve()):
        parser.error('完整定位只写本机 data/')
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    try:
        result = reconcile(read(args.input / 'materials.json'), read(args.input / 'sessions.json'),
                           read(args.input / 'actions.json'), read(args.decisions), read(ROOT / 'scripts/journal_materials.json'), read(args.inventory))
    except ValueError as exc:
        print('来源对账未签收：' + str(exc))
        return 1
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.public:
        args.public.parent.mkdir(parents=True, exist_ok=True)
        args.public.write_bytes(gzip.compress(json.dumps(public_ledger(result), ensure_ascii=False,
                               separators=(',', ':')).encode(), mtime=0))
    print(json.dumps({key: len(result[key]) for key in ['files', 'sessions', 'messages', 'commits', 'actions']}, ensure_ascii=False))
    print('文件去向', dict(Counter(x['disposition'] for x in result['files'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
