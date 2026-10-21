"""来源目录不能依赖已有日卡，未提交、历史笔记和失败均需显式保留。"""
from pathlib import Path
import tempfile
import unittest
import subprocess
import os
from scripts.collect_journal_materials import collect, file_kind


class MaterialTests(unittest.TestCase):
    def test_deleted_document_and_unmerged_branch_survive_current_directory_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def run(*args):
                env = dict(os.environ, GIT_AUTHOR_DATE='2026-08-01T12:00:00+08:00', GIT_COMMITTER_DATE='2026-08-01T12:00:00+08:00')
                return subprocess.run(['git','-C',tmp,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args], check=True, capture_output=True, env=env)
            run('init','-b','main')
            (root/'idea.md').write_text('# 尚未实施的构思\n',encoding='utf-8');run('add','idea.md');run('commit','-qm','create idea')
            (root/'idea.md').unlink();run('add','-u');run('commit','-qm','remove idea')
            run('checkout','-b','experiment');(root/'branch.md').write_text('# 分支试验\n',encoding='utf-8');run('add','branch.md');run('commit','-qm','unmerged experiment');run('checkout','main')
            target = run('rev-parse','HEAD').stdout.decode().strip()
            run('update-index','--add','--cacheinfo','160000,'+target+',external-repo');run('commit','-qm','link repository')
            result = collect({'sources':[{'id':'r','path':tmp,'repo':'fixture'}],'exclude_directory_names':['.git']},'2026-06-01','2026-10-21')
            self.assertEqual(len(result['commits']),4)
            historical = next(f for f in result['files'] if f['path']=='idea.md')
            self.assertEqual(historical['git_state'],'historical-deleted')
            self.assertIn('尚未实施',historical['text'])
            self.assertEqual(next(f for f in result['files'] if f['path']=='branch.md')['git_state'], 'historical-other-ref')
            self.assertTrue(any(not c['selected_revision_ancestor'] for c in result['commits']))
            self.assertTrue(any(f['kind']=='repository-link' for f in result['files']))
            self.assertEqual(result['failures'],[])

    def test_documents_without_journal_dates_and_ignored_assets_are_inventoried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'reports').mkdir()
            (root / 'reports/new-idea.md').write_text('# 研究构思\n尚未运行\n', encoding='utf-8')
            (root / 'result.parquet').write_bytes(b'example-data')
            (root / 'node_modules').mkdir()
            cfg = {'sources': [{'id': 'notes', 'path': tmp}], 'exclude_directory_names': ['node_modules']}
            r = collect(cfg, '2026-06-01', '2026-10-21')
            self.assertEqual({f['path'] for f in r['files']}, {'reports/new-idea.md', 'result.parquet'})
            self.assertEqual(r['files'][1]['title'], '研究构思')
            self.assertEqual(r['directory_exclusions'][0]['reason'], 'dependency-cache-git-or-build')
            self.assertEqual(r['failures'], [])

    def test_missing_source_is_failure_not_empty_success(self):
        r = collect({'sources': [{'id': 'missing', 'path': 'Z:/missing-materials-fixture'}], 'exclude_directory_names': []}, '2026-06-01', '2026-10-21')
        self.assertEqual(r['failures'][0]['error'], 'source-directory-missing')

    def test_source_copy_and_sensitive_configuration_are_not_new_research_documents(self):
        self.assertEqual(file_kind('reports/evidence/source-abcdef/PLAN/design.md'), 'retained-copy-or-tool-artifact')
        self.assertEqual(file_kind('.env.local'), 'restricted-configuration')
        self.assertEqual(file_kind('reports/2026-09/new-idea.md'), 'document')


if __name__ == '__main__':
    unittest.main()
