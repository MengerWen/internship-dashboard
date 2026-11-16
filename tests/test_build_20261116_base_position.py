from copy import deepcopy
from datetime import date, timedelta
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_20261116_base_position as build


@pytest.fixture(scope='module')
def document():
    dates = [(date(2024, 7, 1) + timedelta(days=i)).isoformat() for i in range(565)]
    dates.append('2026-10-30')
    stages = [stage for stage, (_, _, count) in build.STAGES.items() for _ in range(count)]
    base = [[.4 + i / 10000, .6 + i / 20000] for i in range(566)]
    series = {key: [[i / 1_000_000, -i / 1_000_000, 30, 50, 29, 48] for i in range(566)]
              for key in build.CONFIGURATIONS}
    return dict(schema=build.SCHEMA, dates=dates, stages=stages, nominal=1.,
                initial=dict(index=[.4, .6], equal=[.4, .6]), base=dict(index=base, equal=base),
                series=series, original_sha256='f' * 64)


def test_original_comparison_layout_and_data_contract(document):
    original = build.template_text(build.OLD_PAGE)
    data = build.pack(document)
    page = build.render(original, data, 'https://example.com/results')
    assert build.render(original, data, 'https://example.com/results') == page
    assert page.count('id="return-chart"') == 1
    assert page.count('id="score-rows"') == 1
    assert page.count('id="signal-chart"') == 1
    assert '<canvas' not in page
    assert '原登记口径' not in page
    assert '全市场选股后取交集' not in page
    assert 'data-fill-basis=' not in page
    assert 'id="csi-base-position"' not in page
    assert 'id="return-data"' not in page
    assert 'id="fill-data"' not in page
    assert set(re.findall(r'data-lane="(\d)"', page)) == {'0', '1', '2', '3'}
    assert len(re.findall(r'<tr data-market=', page)) == 12
    assert page.count('data-curve-kind="returns"') == 5
    assert 'name="weight"' in page and 'name="sorting"' in page
    assert 'data-return-view="wealth"' in page and 'data-return-view="enhancement"' in page
    payload = re.search(r'id="csi2000-market-data">([^<]+)</script>', page).group(1)
    packed = json.loads(gzip.decompress(base64.b64decode(payload)))
    assert set(packed['series']) == build.CONFIGURATIONS
    assert packed['signal'] == build.csi_signals(original)
    assert packed['base'] == data['base']
    assert '__CHART_HELPERS__' not in page and 'isExcess()' not in page
    assert 'activeIndex' not in page and 'feeBasis' not in page
    assert len(page.encode()) <= build.ASSET_LIMIT
    assert 'url("../fonts/LibreBaskerville-Regular.woff2")' in page
    assert 'url("../../site/fonts/LibreBaskerville-Regular.woff2")' in page
    script = re.search(r'<script>\s*(.*?)\s*</script>', page, re.S).group(1)
    checked = subprocess.run(['node', '--check', '-'], input=script, encoding='utf-8', capture_output=True)
    assert checked.returncode == 0, checked.stderr
    for path, digest in build.SOURCE_HASHES.items():
        assert build.template_text(path)


def test_market_values_and_note(document):
    note = build.render_note(build.template_text(build.OLD_NOTE), 'https://example.com',
                             published='2026-11-16T15:17:43+08:00')
    assert 'show_source: 2026-11-16.show.html' in note
    assert 'published: "2026-11-16T15:17:43+08:00"' in note
    assert '原登记口径' not in note and '历史对照' not in note
    for field in ('initial', 'base', 'series'):
        bad = deepcopy(document)
        if field == 'initial':
            bad[field]['index'] = [0., 1.]
        elif field == 'base':
            bad[field]['index'][0] = [1.]
        else:
            bad[field]['index-combined-morning-L-5'][0][4] = 31
        with pytest.raises(ValueError):
            build.pack(bad)


def test_protected_target_is_rejected_before_opening_input():
    output = subprocess.run([sys.executable, str(Path(build.__file__)),
        '--aggregate', 'not-used.json', '--sha256', 'not-used',
        '--report-url', 'https://example.com', '--page', str(build.OLD_PAGE),
        '--published', '2026-11-16T15:17:43+08:00'], capture_output=True, text=True)
    assert output.returncode != 0
    assert 'protected 11.9 sources' in output.stderr
