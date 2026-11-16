from collections import Counter
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
    from datetime import date, timedelta
    dates = [(date(2024, 7, 1) + timedelta(days=i)).isoformat() for i in range(565)]
    dates.append('2026-10-30')
    stages = [stage for stage, days in build.STAGES.items() for _ in range(days)]
    scope = []
    daily = []
    stats = []
    for k, key in enumerate(sorted(build.CONFIGURATIONS)):
        scope.append(dict(key=key))
        for i, (day, stage) in enumerate(zip(dates, stages, strict=True)):
            b = 1 + i / 2000
            a = (k + 1) * i / 1_000_000
            daily.append(dict(config=key, date=day, stage=stage, base=b, addition=a,
                              wealth=b + a, selected_sh=30, selected_sz=53, filled=81))
        stats.extend(dict(config=key, stage=stage, days=count, mean_bp=.12345)
                     for stage, count in build.STAGES.items())
    return dict(schema=build.SCHEMA, dates=dates, nominal=1.,
                configurations=scope, daily=daily, statistics=stats)


def test_template_and_payload_are_preserved(document):
    old_page = build.OLD_PAGE.read_text(encoding='utf-8')
    old_note = build.OLD_NOTE.read_text(encoding='utf-8')
    for path, digest in build.SOURCE_HASHES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    report = 'https://example.com/results'
    packed = build.pack(document)
    page = build.render(old_page, packed, report)
    note = build.render_note(old_note, document, report)
    assert (build.render(old_page, packed, report), build.render_note(old_note, document, report)) == (page, note)
    assert 'date: 2026-11-16' in note
    assert 'show_source: 2026-11-16.show/.html' in note
    assert 'published:' not in note
    timed = build.render_note(old_note, document, report, published='2026-11-16T15:17:43+08:00')
    assert 'published: "2026-11-16T15:17:43+08:00"' in timed
    assert '+0.12 bp' in note
    assert '2026.11.16' in page
    assert page.index('id="csi-base-position"') < page.index('id="index-switcher"')
    blocks = r'<script type="application/(?:json|octet-stream)" id="([^"]+)">\s*(.*?)\s*</script>'
    original = dict(re.findall(blocks, old_page, re.S))
    newer = dict(re.findall(blocks, page, re.S))
    assert {k: newer[k] for k in original} == original
    assert json.loads(gzip.decompress(base64.b64decode(newer['csi-base-data']))) == packed
    assert len(page.encode()) <= build.ASSET_LIMIT
    assert set(packed['config']) == build.CONFIGURATIONS
    assert Counter(packed['stages']) == build.STAGES


def test_refuses_inconsistent_amount(document):
    changed = dict(document, daily=document['daily'].copy())
    changed['daily'][0] = dict(changed['daily'][0], wealth=12)
    with pytest.raises(ValueError, match='Inconsistent'):
        build.pack(changed)


def test_protected_target_is_rejected_before_opening_input():
    argument = subprocess.run([sys.executable, str(Path(build.__file__)),
        '--aggregate', 'not-used.json', '--sha256', 'not-used',
        '--report-url', 'https://example.com', '--page', str(build.OLD_PAGE)],
        capture_output=True, text=True)
    assert argument.returncode != 0
    assert 'protected 11.9 sources' in argument.stderr
