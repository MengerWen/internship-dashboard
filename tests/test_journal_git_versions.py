import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.collect_journal_materials import collect

ROOT=Path(__file__).resolve().parents[1]


class HistoricalVersionTests(unittest.TestCase):
    def test_earlier_idea_is_preserved_even_when_current_file_still_exists(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data') as tmp:
            base=Path(tmp);repo=base/'repo';repo.mkdir()
            env=dict(os.environ,GIT_AUTHOR_DATE='2026-08-01T12:00:00+08:00',GIT_COMMITTER_DATE='2026-08-01T12:00:00+08:00')
            def git(*args):
                return subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],env=env,check=True,capture_output=True)
            git('init','-b','main');doc=repo/'idea.md'
            doc.write_text('# 早期构思\n尚未实施\n',encoding='utf-8');git('add','idea.md');git('commit','-qm','first idea')
            doc.write_text('# 后续收敛规范\n',encoding='utf-8');git('add','idea.md');git('commit','-qm','revise idea')
            config={'sources':[{'id':'r','repo':'fixture','path':str(repo)}],'exclude_directory_names':['.git']}
            material=collect(config,'2026-06-01','2026-10-21')
            cfg=base/'config.json';cfg.write_text(json.dumps(config))
            sources=base/'materials.json';sources.write_text(json.dumps(material))
            output=base/'versions/index.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/collect_journal_git_versions.py'),'--materials',str(sources),'--config',str(cfg),'--output',str(output)],check=True,capture_output=True)
            result=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(result['versions']),2)
            texts=[Path(b['snapshot_file']).read_text(encoding='utf-8') for b in result['blobs']]
            self.assertTrue(any('早期构思' in t for t in texts))
            self.assertTrue(any('后续收敛规范' in t for t in texts))
            self.assertEqual(result['failures'],[])

