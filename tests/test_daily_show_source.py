from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from build import Builder


class DailyShowSourceTests(unittest.TestCase):
    def build_fixture(self, root, source):
        content = root/'content'
        daily = content/'daily'
        daily.mkdir(parents=True)
        (daily/'2026-11-01.md').write_text('---\ntitle: 因子评价\nstage: factor\nshow_source: '+source+'\n---\n正文',encoding='utf-8')
        (daily/'2026-11.01.show.html').write_text('<html><body>完整评价</body></html>',encoding='utf-8')
        builder = Builder()
        builder.out_dir = root/'out'
        return builder, content

    def test_iso_daily_route_uses_named_show_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            builder, content = self.build_fixture(root,'2026-11.01.show.html')
            with patch('build.ROOT',root), patch('build.CONTENT_DIR',content):
                entries = builder.build_daily()
            self.assertEqual(entries[0]['show_path'],'daily/2026-11.01.show.html')
            self.assertTrue((root/'out/daily/2026-11.01.show.html').exists())
            self.assertFalse(any('缺少对应主日报' in w for w in builder.warnings))

    def test_source_cannot_escape_daily_directory(self):
        for source in ('../outside.show.html','..\\outside.show.html'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                builder, content = self.build_fixture(root,source)
                with patch('build.ROOT',root), patch('build.CONTENT_DIR',content), self.assertRaisesRegex(ValueError,'show_source'):
                    builder.build_daily()
