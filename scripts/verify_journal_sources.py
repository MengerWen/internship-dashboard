"""在配置指向的本地 Git 仓库核验固定原始链接，不访问或运行研究业务。"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'docs/journal-review/audit-2026-10-21/remediation-actions.json').read_text(encoding='utf-8'))
    config = json.loads((ROOT / 'scripts/journal_repos.json').read_text(encoding='utf-8'))
    repos = {r['name']: r for r in config['repos']}
    checked = []
    for key, ref in manifest['source_catalog'].items():
        spec = repos[ref['repo']]
        path = (ROOT / spec['path']).resolve()
        def git(*params):
            return subprocess.run(['git', '-C', str(path), *params], check=True, capture_output=True, encoding='utf-8').stdout
        git('merge-base', '--is-ancestor', ref['revision'], spec['revision'])
        if ref['kind'] == 'file':
            if spec.get('only_under') and not ref['path'].startswith(spec['only_under']):
                raise ValueError(f'{key}: 超出父仓白名单')
            body = git('show', f"{ref['revision']}:{ref['path']}")
            lo, hi = ref['lines']
            if not (1 <= lo <= hi <= len(body.splitlines())):
                raise ValueError(f'{key}: 行号超出文件范围')
        else:
            git('cat-file', '-e', ref['revision'] + '^{commit}')
        checked.append(key)
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'passed': True,
              'source_count': len(checked), 'source_ids': sorted(checked),
              'revisions': {name: r['revision'] for name, r in repos.items()},
              'scope': 'Git对象、祖先关系、文件行号、父仓白名单；不表示服务器现场运行验收。'}
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"固定原始引用 {len(checked)} 项：Git对象、行号及版本包含关系全部通过。")


if __name__ == '__main__':
    main()
