"""Check the published report against accepted counts and scientific identity."""
import base64
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'content/assets/model328-2026-10-18'
DATA = json.loads((ASSETS / 'report-data.json').read_text(encoding='utf8'))


def test_accepted_source_and_calendar_are_bound():
    assert DATA['source_sha256']['factor-bank/final_acceptance.json'] == 'fc0f323dca7c222f0ec6dbe44e472447b2e4139aee76c67318d42a71c64bbd83'
    assert len(DATA['days']) == 601
    assert len({d['date'] for d in DATA['days']}) == 601
    assert len(DATA['features']) == 328
    assert len(DATA['periods']) == 44
    assert sum(d['rows'] for d in DATA['days']) == 1719612
    assert sum(d['no_l2_facts'] for d in DATA['days']) == 4999
    assert [f['model_column'] for f in DATA['features']] == DATA['columns']


def test_every_downloaded_column_reconciles_to_daily_and_final_counts():
    with (ASSETS / 'factor-coverage.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 328
    for i, row in enumerate(rows):
        name = DATA['columns'][i]
        missing = sum(d['missing'][i] for d in DATA['days'])
        assert row['model_column'] == name
        assert int(row['model_index']) == i
        assert int(row['nan']) == missing == DATA['coverage']['missing_by_column'][name]
        assert int(row['finite']) + missing == 1719612
        assert abs(float(row['coverage_pct']) - int(row['finite']) / 1719612 * 100) < 1e-12
    assert sum(int(r['finite']) for r in rows) == 557600704
    assert sum(int(r['nan']) for r in rows) == 6432032


def test_sparse_columns_and_performance_limit_remain_visible():
    sparse = [f for f in DATA['features'] if f['original_column'].startswith('f96_')]
    assert len(sparse) == 2
    assert all(d['missing'][sparse[0]['index']] == d['missing'][sparse[1]['index']] for d in DATA['days'])
    for f in sparse:
        assert DATA['coverage']['missing_by_column'][f['model_column']] == 1681118
    fresh = [d for d in DATA['days'] if d['attempt'] in {'production-r03', 'production-r04'} and d['complete_business_timing']]
    assert len(fresh) == 328
    assert sum(d['business_wall_seconds'] > 300 for d in fresh) == 235
    assert DATA['computation']['passed'] is True
    assert DATA['computation']['performance_passed'] is False
    md = (ROOT / 'content/daily/2026-10-18.md').read_text(encoding='utf8')
    assert 'date: 2026-10-18' in md
    assert '2.238528%' in md and '性能门槛未通过' in md
    assert '{{' not in md


def test_embedded_payload_matches_the_download_and_has_no_old_return_results():
    page = (ROOT / 'content/daily/2026-10-18.show.html').read_text(encoding='utf8')
    encoded = re.search(r'<script id="report-gzip" type="application/octet-stream">(.*?)</script>', page, re.S).group(1)
    embedded = json.loads(gzip.decompress(base64.b64decode(encoded)))
    assert embedded == DATA
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://', page)
    assert 'fetch(' not in page
    assert all(not ({'stats', 'distribution', 'daily_ic', 'daily_rank'} & f.keys()) for f in DATA['features'])
    original = ROOT / 'artifacts/model328-report-2026-10-18/accepted-aggregates.json'
    assert hashlib.sha256(original.read_bytes()).hexdigest() == DATA['report_input_sha256']
