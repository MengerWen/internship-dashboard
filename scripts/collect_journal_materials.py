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
    raw = git(source['resolved_path'], 'log', revision, '--since=' + since,
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
        cached, untracked = set(), set()
        if source.get('repo'):
            revision = git(base, 'rev-parse', source.get('revision', 'HEAD')).strip()
            snapshots.append({'source': source['id'], 'repo': source['repo'], 'path': str(base),
                              'revision': revision, 'captured_at': datetime.now(SHANGHAI).isoformat()})
            prefix = source.get('git_prefix', '')
            args = ('--', prefix) if prefix else ()
            cached = {p[len(prefix):] for p in git(base, 'ls-files', '-z', '--cached', *args).split('\0') if p}
            untracked = {p[len(prefix):] for p in git(base, 'ls-files', '-z', '--others', '--exclude-standard', *args).split('\0') if p}
            commits.extend(history(source, revision, since, until))
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
    return {'schema_version': 1, 'since': since, 'until': until, 'captured_at': datetime.now(SHANGHAI).isoformat(),
            'snapshots': snapshots, 'aliases': alias_checks, 'files': files, 'commits': commits,
            'directory_exclusions': exclusions, 'failures': failures,
            'note': '材料目录独立于日卡；全文仅本机。工作区逐文件采样，不是原子快照。文件名、Git日期与实际工作日分别处理。'}


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
