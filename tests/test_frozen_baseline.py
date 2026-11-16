import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from frozen_baseline import MANIFEST, ROOT, baseline_data, protect_outputs, verify


def test_migrated_baseline_keeps_every_amount_and_condition():
    document = verify()
    before = baseline_data((ROOT / document['migration_source']['page']).read_text(encoding='utf-8'))
    after = baseline_data((ROOT / 'content/daily/2026-11-13.show.html').read_text(encoding='utf-8'))
    assert before == after
    assert len(after['dates']) == 566
    assert len(after['series']) == 192
    assert after['tradeFractions'] == [10, 20, 30]
    assert len(document['science_sources']) == 2
    for record in document['science_sources']:
        assert any(row['kind'] == 'oof_prediction' for row in record['objects'])


def test_frozen_outputs_reject_aliases_but_allow_new_comparison_page():
    protect_outputs([ROOT / 'content/daily/2026-11-16.show.html'])
    with pytest.raises(ValueError, match='覆盖固定 B0'):
        protect_outputs([ROOT / 'content/daily/../daily/2026-11-13.show.html'])


def test_corrupt_frozen_dependency_stops_all_builds(tmp_path):
    asset = tmp_path / 'baseline.html'
    asset.write_text('frozen', encoding='utf-8')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(dict(schema='frozen-baseline-v1', files=[dict(
        path=asset.name, sha256=hashlib.sha256(asset.read_bytes()).hexdigest())])), encoding='utf-8')
    verify(root=tmp_path, manifest=manifest)
    asset.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='冻结文件变化'):
        protect_outputs([tmp_path / 'candidate.html'], root=tmp_path, manifest=manifest)
