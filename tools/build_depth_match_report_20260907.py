"""Render the depth-match briefing from the accepted evaluation, without recomputing factors."""
import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/depth-match-2026-09-07'
OUT = ROOT / 'content/daily/2026-09-07.show.html'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build(source):
    review = source / '.local-output/depth-match-implementation/full-history-review'
    evidence = source / 'reports/2026-09/2026-09-08-depth-match-full-history-evidence'
    result = json.loads((evidence / 'DM_RESULT.json').read_text())
    assert result['status'] == 'accepted'
    ASSETS.mkdir(parents=True, exist_ok=True)
    copied = {}
    for folder in ['assets', 'evaluation', 'notebooks']:
        for p in (review / folder).iterdir():
            if p.is_file():
                dest = ASSETS / folder / p.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dest)
                assert digest(p) == digest(dest)
                copied[str(dest.relative_to(ASSETS)).replace('\\', '/')] = digest(dest)
    for p in evidence.rglob('*'):
        if p.is_file() and p.name != '.gitattributes':
            dest = ASSETS / 'evidence' / p.relative_to(evidence)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            assert digest(p) == digest(dest)
            copied[str(dest.relative_to(ASSETS)).replace('\\', '/')] = digest(dest)
    completion = source / 'reports/2026-09/2026-09-08-depth-match-full-history-completion.md'
    shutil.copyfile(completion, ASSETS / 'evidence' / completion.name)
    copied['evidence/' + completion.name] = digest(completion)
    def rows(name):
        with (ASSETS / 'evaluation' / (name + '.csv')).open(encoding='utf-8', newline='') as f:
            values = list(csv.DictReader(f))
        for row in values:
            for key, v in row.items():
                if key in ('period', 'date', 'start', 'end', 'formal_column', 'metric', 'column_a', 'column_b', 'label', 'record_id', 'short_alias', 'aggregation'): continue
                if v == '': row[key] = None
                elif v not in ('True', 'False'):
                    try: row[key] = float(v) if any(t in v.lower() for t in ('.','e')) else int(v)
                    except ValueError: pass
        return values
    def read(name):
        return json.loads((ASSETS / name).read_text(encoding='utf-8'))
    data = {name: rows(name) for name in ['period_summary', 'decile_summary', 'decile_spread_summary', 'group_diagnostics', 'group_dispersion', 'daily_ic', 'correlation', 'definition_pair_comparison']}
    data.update({name: read('evaluation/' + name + '.json') for name in ['ols','distribution','redundancy']})
    data['registry'] = read('evidence/registry.json')
    data['files'] = sorted(copied)
    data['seal'] = read('evidence/RUN_SEAL.json')
    assert len(data['registry']['columns']) == 24
    assert len(data['daily_ic']) == 14424
    assert len(list((ASSETS / 'assets').glob('*.png'))) == 120
    from depth_match_figures import render
    render(ASSETS)
    publish(data, copied, digest(evidence/'DM_RESULT.json'))


def publish(data, copied, source_result_sha256, raw=None):
    from depth_match_math import render_math, formulas
    reference = ROOT / 'content/daily/2026-09-06.show.html'
    css = re.search(r'<style>(.*?)</style>', reference.read_text(encoding='utf-8'), re.S).group(1)
    template_path = ROOT / 'tools/depth_match_report_20260907.html'
    script_path = ROOT / 'tools/depth_match_report_20260907.js'
    body = render_math(template_path.read_text(encoding='utf-8'))
    raw = raw or json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')
    page = body.replace('/* REFERENCE_STYLE */', css).replace('/* REPORT_DATA */', raw).replace('/* FORMULA_DATA */', json.dumps(formulas(), ensure_ascii=False).replace('</', '<\\/')).replace('/* DEPTH_SCRIPT */', script_path.read_text(encoding='utf-8'))
    OUT.write_text(page.replace('/* FIGURE_DATA */', '{}'), encoding='utf-8', newline='\n')
    shown = sorted((ASSETS / 'figures').glob('*.png')) + sorted(p for p in (ASSETS / 'assets').glob('*.png') if p.stem.endswith(('-scatter', '-distribution')))
    assert len(shown) == 120
    figures = {p.relative_to(ASSETS).as_posix(): base64.b64encode(p.read_bytes()).decode() for p in shown}
    offline = OUT.with_name('2026-09-07.html')
    offline.write_text(page.replace('/* FIGURE_DATA */', json.dumps(figures, separators=(',', ':'))), encoding='utf-8', newline='\n')
    audit = {'status':'complete','source_status':'accepted','source_result_sha256':source_result_sha256,'source_seal':data['seal'],'reference_sha256':digest(reference),'html_sha256':digest(OUT),'offline_html_sha256':digest(offline),'data_sha256':hashlib.sha256(raw.encode()).hexdigest(),'template_sha256':digest(template_path),'script_sha256':digest(script_path),'copied_files':copied,'factor_count':24,'factor_days':14424,'figures':120,'periods':len(set(x['period'] for x in data['period_summary'])),'rendered_figures':{p.relative_to(ASSETS).as_posix():digest(p) for p in sorted((ASSETS / 'figures').glob('*'))},'method':'Presentation of sealed evaluation; no factor or return recalculation.'}
    (ASSETS/'2026-09-07-report-build-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    package()
    print(json.dumps({'html_bytes':OUT.stat().st_size,'offline_bytes':offline.stat().st_size,'data_sha256':audit['data_sha256'],'periods':audit['periods']}))


def package():
    bundle = ASSETS / '2026-09-07-depth-match-review.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(OUT, OUT.relative_to(ROOT / 'content'))
        for p in sorted(ASSETS.rglob('*')):
            if p.is_file() and p.suffix != '.zip':
                archive.write(p, p.relative_to(ROOT / 'content'))
    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
    with zipfile.ZipFile(bundle) as archive:
        batches = [[]]
        size = 0
        for item in archive.infolist():
            if size + item.compress_size > 19 * 1024**2 and batches[-1]:
                batches.append([])
                size = 0
            batches[-1].append(item)
            size += item.compress_size
        assert len(batches) == 3, 'Update the three reading-package links for the new archive layout'
        for index, batch in enumerate(batches, 1):
            part = bundle.with_name(bundle.stem + f'-part{index:02}.zip')
            with zipfile.ZipFile(part, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
                for item in batch:
                    output.writestr(item.filename, archive.read(item))
            assert part.stat().st_size < 25 * 1024**2


def render_existing(daily_figures=False):
    current = OUT.read_text(encoding='utf-8')
    raw = re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', current, re.S).group(1)
    data = json.loads(raw)
    audit = json.loads((ASSETS/'2026-09-07-report-build-audit.json').read_text(encoding='utf-8'))
    for name, expected in audit['copied_files'].items():
        if digest(ASSETS / name) != expected:
            raise ValueError('Accepted input changed: ' + name)
    if daily_figures:
        from depth_match_figures import render
        render(ASSETS, daily_only=True)
    publish(data, audit['copied_files'], audit['source_result_sha256'], raw=raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--source', type=Path)
    modes.add_argument('--render-only', action='store_true')
    parser.add_argument('--daily-figures', action='store_true')
    args = parser.parse_args()
    if args.render_only:
        render_existing(args.daily_figures)
    else:
        build(args.source)
