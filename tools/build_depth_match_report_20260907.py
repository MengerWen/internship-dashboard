"""Render the depth-match briefing from the accepted evaluation, without recomputing factors."""
import argparse
import csv
import hashlib
import html
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
    rendered = render(ASSETS)
    template = (ROOT / 'content/daily/2026-09-06.show.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', template, re.S).group(1)
    body = (ROOT / 'tools/depth_match_report_20260907.html').read_text(encoding='utf-8')
    page = body.replace('/* REFERENCE_STYLE */', css).replace('/* REPORT_DATA */', json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/'))
    OUT.write_text(page, encoding='utf-8', newline='\n')
    audit = {'status':'complete','source_status':'accepted','source_result_sha256':digest(evidence/'DM_RESULT.json'),'source_seal':data['seal'],'reference_sha256':digest(ROOT/'content/daily/2026-09-06.show.html'),'html_sha256':digest(OUT),'copied_files':copied,'factor_count':24,'factor_days':14424,'figures':120,'periods':len(set(x['period'] for x in data['period_summary'])),'rendered_figures':{str(p.relative_to(ASSETS)):digest(p) for p in rendered},'method':'Presentation of sealed evaluation; no factor or return recalculation.'}
    (ASSETS/'2026-09-07-report-build-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
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
    print(json.dumps({'html_bytes':OUT.stat().st_size,'copied_files':len(copied),'periods':audit['periods']}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    build(parser.parse_args().source)
