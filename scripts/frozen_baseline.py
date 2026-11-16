"""核对固定 B0 档案及其依赖，阻止候选构建覆盖档案。"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'artifacts/factor-strategy-comparison/baseline-frozen.json'


def sha256(path):
    raw = path.read_bytes()
    if path.suffix in ('.md', '.html', '.json'):
        raw = raw.replace(b'\r\n', b'\n')
    return hashlib.sha256(raw).hexdigest()


def baseline_data(page):
    match = re.search(r'id="csi2000-market-data">\s*([^<]+)</script>', page, re.S)
    if match is None:
        raise ValueError('B0 金额数据缺失')
    data = json.loads(gzip.decompress(base64.b64decode(match[1])))
    if len(data['dates']) != 566 or len(data['series']) != 192:
        raise ValueError('B0 应覆盖 566 日与 192 配置')
    return data


def verify(*, root=ROOT, manifest=MANIFEST):
    document = json.loads(manifest.read_bytes())
    if document['schema'] != 'frozen-baseline-v1':
        raise ValueError('B0 冻结清单版本不符')
    for record in document['files']:
        path = (root / record['path']).resolve()
        if not path.is_relative_to(root.resolve()) or sha256(path) != record['sha256']:
            raise ValueError(f'B0 冻结文件变化：{record["path"]}')
    return document


def protect_outputs(paths, *, root=ROOT, manifest=MANIFEST):
    if not manifest.exists():
        return
    document = verify(root=root, manifest=manifest)
    protected = {(root / row['path']).resolve() for row in document['files']}
    if protected.intersection(Path(path).resolve() for path in paths):
        raise ValueError('构建输出不能覆盖固定 B0 档案或依赖')


def freeze(*, research, root=ROOT, manifest=MANIFEST):
    if manifest.exists():
        return verify(root=root, manifest=manifest)
    source = root / 'content/daily/2026-11-16.show.html'
    note_source = source.with_name('2026-11-16.md')
    targets = [source.with_name('2026-11-13.show.html'), note_source.with_name('2026-11-13.md')]
    if any(path.exists() for path in targets):
        raise ValueError('11.13 已有内容，拒绝覆盖')
    page = source.read_text(encoding='utf-8')
    original = baseline_data(page)
    page = re.sub(r'<!-- G2-COMPARISON-BEGIN -->.*?<!-- G2-COMPARISON-END -->\s*', '', page, flags=re.S)
    page = page.replace('<time datetime="2026-11-16">2026.11.16 · 模型基准</time>',
                        '<time datetime="2026-11-13">2026.11.13 · 固定模型基准</time>')
    page = page.replace('<h1>中证 2000 底仓做 T：沪深冻结模型基准</h1>',
                        '<h1>中证 2000 底仓做 T：固定 baseline</h1>\n'
                        '<p>档案日期 2026-11-13；计算及首次发布于 2026-11-16。'
                        '<a href="2026-11-16.show.html">因子评测与策略比较</a></p>')
    note = note_source.read_text(encoding='utf-8')
    note = re.sub(r'<!-- G2-NOTE-BEGIN -->.*?<!-- G2-NOTE-END -->\s*', '', note, flags=re.S)
    note = note.replace('date: 2026-11-16', 'date: 2026-11-13')
    note = note.replace('show_source: 2026-11-16.show.html', 'show_source: 2026-11-13.show.html')
    note = note.replace('中证 2000 底仓做 T：沪深冻结模型基准', '中证 2000 底仓做 T：固定 baseline')
    note = note.replace('沪市和深市使用已冻结的',
                        '本页为 2026-11-13 固定 baseline 档案，计算及首次发布于 2026-11-16。'
                        '[因子评测与策略比较](2026-11-16.md)持续更新候选版本。\n\n沪市和深市使用已冻结的', 1)
    if baseline_data(page) != original:
        raise ValueError('归档前后 B0 数值或科学元信息不同')
    for path, text in zip(targets, (page, note), strict=True):
        path.write_text(text, encoding='utf-8', newline='\n')
    dependencies = []
    for style in re.findall(r'<style[^>]*>(.*?)</style>', page, re.S):
        for name in re.findall(r'url\(["\']?([^"\')]+)', style):
            if name.startswith(('data:', 'http:','https:')):
                continue
            path = (source.parent / name).resolve()
            if path.is_file() and path.is_relative_to(root.resolve()):
                dependencies.append(path)
    registries = [research / 'reports/2026-11' / name for name in (
        '2026-11-08-model-szse344-baseline-registration.json',
        '2026-11-09-model-sse340-baseline-registration.json')]
    document = dict(schema='frozen-baseline-v1', archive_date='2026-11-13', computed_and_published='2026-11-16',
        migration_source=dict(page=source.relative_to(root).as_posix(), page_sha256=sha256(source),
                              note_sha256=sha256(note_source), dashboard_revision='9b0e558fa35073fc3612bfbe795c68ff80d1d16c'),
        result=dict(path='/home/wangly/hdd-store/outputs/sirui/wangly-csi2000-base-position-20261116-ratios-01a1e3a7/market-comparison.json',
                    sha256='cccc7033c09e85bd4e4f1a5c7d1712d3acbb8bd04a2cb836f537b6a3217ecb4c'),
        days=566, configurations=192,
        science_sources=[dict(path=p.relative_to(research).as_posix(), sha256=sha256(p),
                              identity=json.loads(p.read_bytes())['identity'],
                              objects=json.loads(p.read_bytes())['objects']) for p in registries],
        files=[dict(path=p.relative_to(root).as_posix(), sha256=sha256(p), bytes=p.stat().st_size)
               for p in sorted(set(targets + dependencies))])
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return verify(root=root, manifest=manifest)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path)
    args = parser.parse_args()
    result = freeze(research=args.research) if args.research else verify()
    print(json.dumps(dict(days=result['days'], configurations=result['configurations'], frozen_files=len(result['files']))))
