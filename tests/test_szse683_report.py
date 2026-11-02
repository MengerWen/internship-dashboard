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
ASSETS=ROOT/'content/assets/szse683-2026-11-01'


def decode_script(path):
    match=re.fullmatch(r'window\.(?:rawbankFactorLoaded|szseAtlasLoaded)\("[^"]+",("[^"]+")(?:,"[^"]+")?\);',path.read_text(encoding='utf-8'))
    return json.loads(gzip.decompress(base64.b64decode(json.loads(match[1]))))


def test_all_contexts_factors_counts_and_statistics():
    for segment,n in [('full',683),('base',601),('increment',82)]:
        for horizon in ('10m','lunch','close'):
            key=segment+'-'+horizon
            data=decode_script(ASSETS/key/'summary.js')
            assert len(data['dates'])==n and data['label']=='ret_'+horizon
            assert len(data['factors'])==344 and len(data['periods'])=={'full':50,'base':44,'increment':8}[segment]
            assert Counter(f['metadata']['source'] for f in data['factors'])==Counter(old=272,cancel_buy=24,cancel_sell=24,depth=24)
            assert set(data['definitions'])=={f['metadata']['definition_key'] for f in data['factors']}
            assert set(data['layers'])=={f['metadata']['layer'] for f in data['factors']}
            for slim in data['factors']:
                m=slim['metadata']
                packet=decode_script(ASSETS/horizon/'factors'/(m['definition_key']+'__'+m['projection']+'.js'))
                part=packet['segments'][segment];a,b=part['slice']
                f=dict(metadata=packet['metadata'],distribution=part['distribution'],shape=part['shape'],
                    daily_ic=packet['daily_ic'][a:b],daily_health=packet['daily_health'][a:b],
                    periods=[packet['periods'][i] for i in part['period_indexes']],details=part['details'])
                assert f['metadata']==m and len(f['daily_ic'])==n
                assert len(f['shape'])==100 and len(f['periods'][0]['groups'])==50
                ic=np.array(f['daily_ic'],dtype=float)
                for j in (0,1):
                    finite=ic[:,j][np.isfinite(ic[:,j])];stats=f['periods'][0]['ic'][j]
                    assert stats[4]==len(finite)
                    if len(finite):np.testing.assert_allclose(stats[0],finite.mean(),atol=1e-14)
                    else:assert stats[0] is None
                assert f['details']['ols']['n']==f['distribution']['pairs']==sum(r[3] for r in f['daily_health'])
                assert sum(b['count'] for b in f['shape'])+f['distribution']['under']+f['distribution']['over']==f['distribution']['finite']
                if f['details']['scatter']:
                    scatter=f['details']['scatter']['full']
                    assert scatter['outside']==0 and sum(c[2] for c in scatter['cells'])==scatter['included']==f['distribution']['pairs']
                assert [{k:p[k] for k in ('ic','spread')} for p in f['periods']]==slim['periods']


def test_csv_mapping_overlap_and_asset_identity():
    with gzip.open(ASSETS/'all-context-performance.csv.gz','rt',encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==344*(50+44+8)*3
    assert len({(r['context'],r['model_column'],r['period']) for r in rows})==len(rows)
    with (ASSETS/'column-mapping.csv').open(encoding='utf-8-sig',newline='') as f:
        mapping=list(csv.DictReader(f))
    assert len(mapping)==288 and len({r['old_column'] for r in mapping})==288
    overlap=json.loads((ASSETS/'factor-overlap.json').read_bytes())
    assert len(overlap['columns'])==344
    for v in overlap['segments'].values():
        a=np.array(v['mean'],dtype=float)
        np.testing.assert_allclose(a,a.T,equal_nan=True)
        assert np.nanmax(np.abs(a))<=1+1e-12
    for entry in json.loads((ASSETS/'factor-assets.json').read_bytes()):
        p=ASSETS/entry['path']
        assert p.stat().st_size==entry['bytes']<25*1024**2
        assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']


def test_page_contract_and_scope():
    page=(ROOT/'content/daily/2026-11.01.show.html').read_text(encoding='utf-8')
    assert not re.search(r'__[A-Z_]+__',page)
    for t in ['ic','monthly','groups','scatter','shape','periods','definition']:assert f'data-tab="{t}"' in page
    for text in ['核心研究结论','重点因子','提速成果','业务耗时','峰值内存']:assert text not in page
    assert 'sample-context' in page and 'horizon-context' in page
    assert 'show_source: 2026-11.01.show.html' in (ROOT/'content/daily/2026-11-01.md').read_text(encoding='utf-8')
