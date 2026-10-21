"""从原始目录、未提交文件及完整 Git 历史建立本机来源目录。"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8))
TEXT = {'.md', '.txt', '.rst', '.org', '.json', '.ipynb', '.yaml', '.yml', '.toml', '.log'}
CODE = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.css', '.sh', '.ps1', '.html', '.tex', '.sty', '.bib', '.c', '.h', '.pyi'}


def identity(source, path):
    return hashlib.sha256((source + '\0' + path).encode('utf-8')).hexdigest()[:24]


def git(path, *args):
    return subprocess.run(['git', '-c', 'core.quotepath=false', '-C', str(path), *args],
                          capture_output=True, encoding='utf-8', errors='strict', check=True).stdout


def history(source, revision, since, until):
    revisions = [revision] if isinstance(revision, str) else revision
    raw = git(source['resolved_path'], 'log', *revisions, '--since=' + since,
              '--format=%x1e%H%x00%aI%x00%cI%x00%s', '--name-status', '--no-renames', '-z')
    rows = []
    for block in raw.split('\x1e')[1:]:
        sha, author, committer, subject, *fields = block.split('\0')
        fields = [f.strip('\n') for f in fields if f.strip('\n')]
        changes = []
        for i in range(0, len(fields), 2):
            status, path = fields[i:i + 2]
            prefix = source.get('git_prefix', '')
            if prefix and not path.startswith(prefix):
                continue
            path = path[len(prefix):]
            if path.split('/')[0] in source.get('exclude_roots', []):
                continue
            changes.append({'status': status, 'path': path})
        day = datetime.fromisoformat(author).astimezone(SHANGHAI).date().isoformat()
        if changes and since <= day <= until:
            rows.append({'id': identity(source['id'], 'git:' + sha), 'source': source['id'],
                         'repo': source['repo'], 'sha': sha, 'date': day, 'author_timestamp': author,
                         'committer_timestamp': committer, 'subject': subject, 'changes': changes})
    return rows


def historical_files(source, commits, present, exclusions, failures, config):
    """现目录已无的路径仍保留Git对象。日期是版本时间，不冒充实际工作日。"""
    latest = {}
    for commit in commits:
        for change in commit['changes']:
            path = change['path']
            if path in present or path in latest:
                continue
            if any(p in config['exclude_directory_names'] or p.startswith('.codex-vet-') for p in Path(path).parts):
                exclusions.append({'source': source['id'], 'path': path, 'reason': 'historical-dependency-cache-git-or-build'})
                continue
            revision = commit['sha'] + ('^' if change['status'] == 'D' else '')
            latest[path] = (revision + ':' + source.get('git_prefix', '') + path, commit, change['status'])
    if not latest:
        return []
    specs = [x[0] for x in latest.values()]
    check = subprocess.run(['git', '-C', source['resolved_path'], 'cat-file', '--batch-check'],
                           input='\n'.join(specs) + '\n', capture_output=True, encoding='utf-8', check=True)
    checked = check.stdout.splitlines()
    if len(checked) != len(specs):
        raise ValueError('历史对象批次未守恒')
    rows, requests = [], []
    for (path, (spec, commit, status)), line in zip(latest.items(), checked):
        fields = line.split()
        if len(fields) != 3 or fields[1] != 'blob':
            revision, tree_path = spec.split(':', 1)
            tree = git(source['resolved_path'], 'ls-tree', '--full-tree', revision, '--', tree_path).strip()
            if tree.startswith('160000 commit '):
                target = tree.split()[2]
                rows.append({'id': identity(source['id'], 'gitlink:' + path + '@' + target),
                             'source': source['id'], 'path': path, 'kind': 'repository-link',
                             'git_state': 'historical-repository-link', 'gitlink_target': target,
                             'git_version_spec': spec, 'git_record_commit': commit['sha'],
                             'bytes': None, 'filename_dates': [], 'changed_during_read': False})
                continue
            failures.append({'source': source['id'], 'path': path, 'error': 'historical-object-unavailable', 'spec': spec})
            continue
        oid, _, size = fields; size = int(size); kind = file_kind(path)
        row = {'id': identity(source['id'], 'git:' + path + '@' + oid), 'source': source['id'], 'path': path,
               'kind': kind, 'bytes': size, 'git_state': 'historical-deleted' if status == 'D' else 'historical-other-ref',
               'git_blob': oid, 'git_version_spec': spec, 'git_record_commit': commit['sha'],
               'git_author_timestamp': commit['author_timestamp'], 'git_committer_timestamp': commit['committer_timestamp'],
               'filename_dates': sorted(set(re.findall(r'2026-\d\d-\d\d', Path(path).name))),
               'changed_during_read': False}
        rows.append(row)
        suffix = Path(path).suffix.lower()
        if kind != 'restricted-configuration' and ((suffix in TEXT and size <= 8_000_000) or (suffix in CODE and size <= 2_000_000)):
            requests.append((row, oid, suffix in TEXT))
    # 使用常驻批处理，避免每份历史文档启动一个Git进程。
    with subprocess.Popen(['git', '-C', source['resolved_path'], 'cat-file', '--batch'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        for row, oid, include_text in requests:
            process.stdin.write((oid + '\n').encode()); process.stdin.flush()
            header = process.stdout.readline().decode().split()
            if len(header) != 3 or header[0] != oid or header[1] != 'blob':
                raise ValueError('历史对象正文响应与请求不符')
            raw = process.stdout.read(int(header[2])); terminator = process.stdout.read(1)
            if len(raw) != row['bytes'] or terminator != b'\n':
                raise ValueError('历史对象正文长度不符')
            row['sha256'] = hashlib.sha256(raw).hexdigest()
            if include_text:
                try: text = raw.decode('utf-8-sig')
                except UnicodeError:
                    try: text = raw.decode('gb18030')
                    except UnicodeError:
                        failures.append({'source': source['id'], 'path': row['path'], 'error': 'historical-text-decode-failed'})
                        continue
                row.update(text=text, line_count=len(text.splitlines()),
                           title=next((l.lstrip('#').strip() for l in text.splitlines()[:60] if l.startswith('# ')), Path(row['path']).stem))
        process.stdin.close()
        if process.wait() != 0:
            raise ValueError('历史正文批处理失败')
    return rows


def file_kind(path):
    """这里只区分材料形态，研究含义和完成状态由后续处置表单独决定。"""
    p = Path(path)
    if re.search(r'(^|/)(?:\.env[^/]*|[^/]*\.(?:pem|key|pfx))$', path, re.I):
        return 'restricted-configuration'
    if re.search(r'(^|/)(?:source(?:-[^/]*)?|backup[^/]*|\.artifacts|\.local-output|\.pytest_tmp|\.agents|\.codex)(/|$)', path):
        return 'retained-copy-or-tool-artifact'
    if p.suffix.lower() == '.md':
        return 'document'
    if p.suffix.lower() == '.ipynb':
        return 'notebook'
    if p.suffix.lower() in CODE:
        return 'implementation-or-presentation-source'
    if p.suffix.lower() in {'.json', '.jsonl', '.log', '.txt', '.yaml', '.yml', '.toml'}:
        return 'evidence-or-configuration'
    if p.suffix.lower() in {'.pdf', '.bib', '.bbl'}:
        return 'reference-or-export'
    return 'supporting-data-or-asset'


def collect(config, since, until):
    files, commits, exclusions, failures, snapshots = [], [], [], [], []
    alias_checks = []
    for alias in config.get('aliases', []):
        a, b = Path(alias['path']), Path(alias['same_as'])
        alias_checks.append({**alias, 'same_file': a.exists() and b.exists() and os.path.samefile(a, b)})
    for original in config['sources']:
        source = dict(original)
        base = (ROOT / source['path']).resolve()
        source['resolved_path'] = str(base)
        if not base.is_dir():
            failures.append({'source': source['id'], 'error': 'source-directory-missing'})
            continue
        cached, untracked, source_commits = set(), set(), []
        if source.get('repo'):
            revision = git(base, 'rev-parse', source.get('revision', 'HEAD')).strip()
            refs = [line.split('\0') for line in git(base, 'for-each-ref', '--format=%(refname)%00%(objectname)%00%(objecttype)%00%(*objectname)%00%(*objecttype)').splitlines()]
            revisions = {revision} | {r[1] if r[2] == 'commit' else r[3] for r in refs if r[2] == 'commit' or r[4] == 'commit'}
            selected = set(git(base, 'rev-list', revision).splitlines())
            snapshots.append({'source': source['id'], 'repo': source['repo'], 'path': str(base),
                              'revision': revision, 'refs': refs, 'history_scope': 'all-local-refs-plus-selected-revision',
                              'captured_at': datetime.now(SHANGHAI).isoformat()})
            prefix = source.get('git_prefix', '')
            args = ('--', prefix) if prefix else ()
            cached = {p[len(prefix):] for p in git(base, 'ls-files', '-z', '--cached', *args).split('\0') if p}
            untracked = {p[len(prefix):] for p in git(base, 'ls-files', '-z', '--others', '--exclude-standard', *args).split('\0') if p}
            source_commits = history(source, sorted(revisions), since, until)
            for commit in source_commits:
                commit['selected_revision_ancestor'] = commit['sha'] in selected
            commits.extend(source_commits)
        walkbase = Path('\\\\?\\' + str(base)) if os.name == 'nt' else base
        def onerror(exc):
            failures.append({'source': source['id'], 'path': exc.filename, 'error': str(exc)})
        for current, dirs, names in os.walk(walkbase, followlinks=False, onerror=onerror):
            current = Path(current)
            for name in list(dirs):
                p = current / name
                reason = None
                if name in config['exclude_directory_names'] or name.startswith('.codex-vet-'):
                    reason = 'dependency-cache-git-or-build'
                elif current == walkbase and name in source.get('exclude_roots', []):
                    reason = 'separate-source-or-local-audit-output'
                elif p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
                    reason = 'directory-link-requires-explicit-source'
                if reason:
                    dirs.remove(name)
                    exclusions.append({'source': source['id'], 'path': p.relative_to(walkbase).as_posix(), 'reason': reason})
            for name in sorted(names):
                p = current / name
                rel = p.relative_to(walkbase).as_posix()
                try:
                    stat = p.stat()
                    kind = file_kind(rel)
                    row = {'id': identity(source['id'], rel), 'source': source['id'], 'path': rel,
                           'kind': kind, 'bytes': stat.st_size,
                           'git_state': 'tracked' if rel in cached else 'untracked' if rel in untracked else 'ignored-or-outside-git'}
                    if p.suffix.lower() in TEXT and stat.st_size <= 8_000_000 and kind != 'restricted-configuration':
                        raw = p.read_bytes()
                        row['sha256'] = hashlib.sha256(raw).hexdigest()
                        try:
                            text = raw.decode('utf-8-sig')
                        except UnicodeDecodeError:
                            text = raw.decode('gb18030')
                        row['text'] = text
                        row['line_count'] = len(text.splitlines())
                        row['title'] = next((l.lstrip('#').strip() for l in text.splitlines()[:60] if l.startswith('# ')), p.stem)
                    elif p.suffix.lower() in CODE and stat.st_size <= 2_000_000:
                        row['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
                    row['filename_dates'] = sorted(set(re.findall(r'2026-\d\d-\d\d', name)))
                    row['changed_during_read'] = p.stat().st_size != stat.st_size or p.stat().st_mtime_ns != stat.st_mtime_ns
                    files.append(row)
                except (OSError, UnicodeError) as exc:
                    failures.append({'source': source['id'], 'path': rel, 'error': str(exc)})
        if source.get('repo'):
            present = {f['path'] for f in files if f['source'] == source['id']}
            files.extend(historical_files(source, source_commits, present, exclusions, failures, config))
    return {'schema_version': 1, 'since': since, 'until': until, 'captured_at': datetime.now(SHANGHAI).isoformat(),
            'snapshots': snapshots, 'aliases': alias_checks, 'files': files, 'commits': commits,
            'directory_exclusions': exclusions, 'failures': failures,
            'note': '材料目录独立于日卡；全文仅本机。Git覆盖冻结的全部本地引用，origin引用是本地缓存，不证明已推送；已消失路径按最新可见版本保留对象，不将计划或检查点当已运行。工作区逐文件采样不是原子快照；Git日期不充当实际工作日。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'scripts/journal_materials.json')
    parser.add_argument('--since', default='2026-06-01')
    parser.add_argument('--until', default=datetime.now(SHANGHAI).date().isoformat())
    parser.add_argument('--output', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21/materials.json')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'data').resolve()):
        parser.error('原始全文只能写入本机 data/ 目录')
    result = collect(json.loads(args.config.read_text(encoding='utf-8')), args.since, args.until)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"来源文件 {len(result['files'])}；完整提交 {len(result['commits'])}；目录排除 {len(result['directory_exclusions'])}；读取失败 {len(result['failures'])}")
    return int(bool(result['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
