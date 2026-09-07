import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build import Builder


class TagSnapshotTest(unittest.TestCase):
    def test_custom_snapshot_is_embedded_and_script_closing_text_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "tags.json"
            data = {"schemaVersion": 1, "tags": [{"id": "x", "name": "</script>", "color": "#123456", "keywords": []}], "assignments": {"2026-07-09": ["x"]}}
            snapshot.write_text(json.dumps(data), encoding="utf-8")
            builder = Builder(offline=True, tags_snapshot=snapshot)
            builder.out_dir = root
            manifest = builder.manifest([], [])
            self.assertEqual(manifest["report_tags"], data)
            (root / "index.html").write_text('<body><!-- INLINE_DATA --></body>', encoding="utf-8")
            builder.inline_offline_data(manifest)
            page = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-offline="true"', page)
            self.assertIn('<\\/script>', page)
            self.assertEqual(page.count('</script>'), 1)

    def test_bad_snapshot_fails_build_instead_of_silently_losing_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tags.json"
            path.write_text('{}', encoding="utf-8")
            with self.assertRaises(ValueError):
                Builder(tags_snapshot=path).manifest([], [])
