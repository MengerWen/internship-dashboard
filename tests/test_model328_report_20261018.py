"""Check the 328-column performance atlas against its accepted numeric payloads."""
import base64
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'content/assets/model328-2026-10-18'


def source():
    return json.loads((ASSETS/'report-data.json').read_bytes())


def full_factor(f):
    m=f['metadata'];p=ASSETS/'factors'/(m['definition_key']+'__'+m['projection']+'.js')
    encoded=json.loads(re.fullmatch(r'window.rawbankFactorLoaded\("[^"]+",("[^"]+")\);',p.read_text(encoding='utf-8')).group(1))
    return json.loads(gzip.decompress(base64.b64decode(encoded)))


def test_calendar_feature_order_and_scientific_identity():
    d=source();fs=d['factors'];proof=d['evaluation_proof']
    assert len(d['dates'])==len(set(d['dates']))==601
    assert len(d['periods'])==44
    assert len(fs)==328 and [f['metadata']['index'] for f in fs]==list(range(328))
    assert Counter(f['metadata']['source'] for f in fs)==Counter(old=256,cancel_buy=24,cancel_sell=24,depth=24)
    assert Counter(f['metadata']['projection'] for f in fs)==Counter(buy=164,sell=164)
    assert len({(f['metadata']['definition_key'],f['metadata']['projection']) for f in fs})==328
    assert proof['passed'] and proof['stock_days']==1719612
    assert proof['independent_daily_ic_checks']==601 and proof['daily_group_checks']==1971280
    assert proof['factor_acceptance_sha256']=='fc0f323dca7c222f0ec6dbe44e472447b2e4139aee76c67318d42a71c64bbd83'
    assert proof['label_spec_hash']=='638fa8814eaf79199adc1680500ecf1ec9a3e743ad9b5fbf47344b7cb441172c'


def test_all_numeric_assets_match_daily_statistics_and_full_sample_counts():
    d=source()
    for slim in d['factors']:
        f=full_factor(slim)
        assert f['metadata']==slim['metadata']
        assert len(f['periods'])==44 and len(f['daily_ic'])==601
        assert len(f['shape'])==100 and len(f['periods'][0]['groups'])==50
        a=np.array([[np.nan if v is None else v for v in row] for row in f['daily_ic']])
        for j in range(2):
            finite=a[:,j][np.isfinite(a[:,j])];s=f['periods'][0]['ic'][j]
            assert s[4]==len(finite)
            if len(finite):assert abs(s[0]-float(finite.mean()))<1e-14
            else:assert s[0] is None
        assert f['details']['ols']['n']==f['distribution']['pairs']==sum(r[3] for r in f['daily_health'])
        assert sum(b['count'] for b in f['shape'])+f['distribution']['under']+f['distribution']['over']==f['distribution']['finite']
        full=f['details']['scatter'].get('full')
        if full:
            assert full['included']==sum(c[2] for c in full['cells'])==f['distribution']['pairs']
            assert full['outside']==0
        for p,summary in zip(f['periods'],slim['periods']):
            assert p['ic']==summary['ic'] and p['spread']==summary['spread']


def test_csv_contains_all_columns_and_periods_at_full_precision():
    d=source()
    with (ASSETS/'all-period-performance.csv').open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    assert len(rows)==328*44
    lookup={(r['model_column'],r['period']):r for r in rows}
    for f in d['factors']:
        for period,p in zip(d['periods'],f['periods']):
            r=lookup[(f['metadata']['factor_id'],period['id'])]
            assert r['Rank_IC']==('' if p['ic'][1][0] is None else str(p['ic'][1][0]))
            assert int(r['IC_valid_days'])==p['ic'][1][4]


def test_page_reuses_performance_explorer_and_bound_payload():
    page=(ROOT/'content/daily/2026-10-18.show.html').read_text(encoding='utf-8')
    encoded=re.search(r'<script id="report-gzip" type="application/octet-stream">(.*?)</script>',page,re.S).group(1)
    assert json.loads(gzip.decompress(base64.b64decode(encoded)))==source()
    for key in ['ic','monthly','groups','scatter','shape','periods','definition']:
        assert f'data-tab="{key}"' in page
    for name in ['rawbankFactorLoaded','densitySVG','drawFactorDetail','download-factor','download-groups','download-summary']:
        assert name in page
    assert 'FACTOR ATLAS · 328 SERIES' in page
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://',page)
    assert (ROOT/'content/daily/2026-10-18.md').read_text(encoding='utf-8').count('{{')==0


def test_factor_asset_hash_inventory_and_download_permissions():
    rows=json.loads((ASSETS/'evidence/factor-assets.json').read_bytes())
    assert len(rows)==328
    for r in rows:
        p=ASSETS/r['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
        assert p.stat().st_size==r['bytes']<25*1024**2
    md=(ROOT/'content/daily/2026-10-18.md').read_text(encoding='utf-8')
    assert 'show_allow_downloads: true' in md and 'date: 2026-10-18' in md
    assert '601日结果属于历史样本内描述' in (ROOT/'content/daily/2026-10-18.show.html').read_text(encoding='utf-8')
