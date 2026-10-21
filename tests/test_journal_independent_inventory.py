import unittest
from tests import test_journal_reconciliation as fixtures
from scripts.collect_journal_inventory import validate_inventory, official_archives, projected_message, collect
from scripts.collect_journal_sessions import within
from scripts.reconcile_journal_sources import reconcile
import json
from pathlib import Path
import tempfile
import sqlite3


class IndependentInventoryGateTests(unittest.TestCase):
    def test_native_windows_cwd_with_repeated_slashes_keeps_project_scope(self):
        self.assertTrue(within(r'D:\\MG\\Research\\project', ['D:/MG/Research']))
        self.assertTrue(within('/D:/MG/Research/project', ['D:/MG/Research']))
        self.assertTrue(within(r'\\?\D:\MG\Research\project', ['D:/MG/Research']))

    def test_file_only_snapshot_cannot_be_signed_off_as_complete(self):
        with self.assertRaisesRegex(ValueError, '独立'):
            reconcile(*fixtures.ReconciliationTests().fixture()[:5])

    def test_registered_missing_body_blocks_even_when_all_file_routes_exist(self):
        args = fixtures.ReconciliationTests().fixture()
        args[5].update(coverage_status='open', issues=[{'id': 'claude-desktop:missing', 'kind': 'registered-body-unavailable'}])
        with self.assertRaisesRegex(ValueError, '仍有缺口'):
            reconcile(*args)

    def test_inventory_is_bound_to_exact_message_universe(self):
        args = fixtures.ReconciliationTests().fixture()
        args[1]['sessions'][0]['messages'][0]['line_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, '不匹配'):
            validate_inventory(args[5], args[1])

    def test_clearing_issue_flags_cannot_hide_an_uncaptured_registration(self):
        args = fixtures.ReconciliationTests().fixture()
        args[5]['sessions'] = [{'scope':'project-candidate', 'platform':'codex', 'native_id':'missing',
                                'body_representation':'database-projection'}]
        with self.assertRaisesRegex(ValueError, '未进入采集快照'):
            validate_inventory(args[5], args[1])

    def test_archive_pagination_must_end_and_not_duplicate_threads(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/'codex-archived-page-000.json'
            path.write_text(json.dumps({'threads': [{'id': 'missing-local-file'}], 'nextCursor': 'more'}))
            with self.assertRaisesRegex(ValueError, '翻页未结束'):
                official_archives(Path(name))
            path.write_text(json.dumps({'threads': [{'id': 'a'}, {'id': 'a'}], 'nextCursor': None}))
            with self.assertRaisesRegex(ValueError, '重复身份'):
                official_archives(Path(name))

    def test_database_projection_has_native_key_and_time_without_fake_jsonl_line(self):
        item = {'type': 'userMessage', 'content': [{'type': 'text', 'text': '请暂停计算'}]}
        row = {'item_json': json.dumps(item), 'item_id': 'message-key', 'turn_id': 'turn-key', 'created_at_ms': 1791526757000}
        msg = projected_message(row)
        self.assertEqual(msg['date'], '2026-10-09')
        self.assertEqual(msg['evidence_format'], 'codex-history-item')
        self.assertNotIn('line', msg)
        self.assertNotIn('line_sha256', msg)

    def test_independent_sqlite_and_desktop_archive_find_absent_jsonl_and_orphan(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); state = root/'state.sqlite'; history = root/'history.sqlite'
            db = sqlite3.connect(state)
            db.execute('CREATE TABLE threads(id,rollout_path,created_at,updated_at,source,cwd,title,archived)')
            db.execute('INSERT INTO threads VALUES(?,?,?,?,?,?,?,?)', ('registered', str(root/'gone.jsonl'), 0, 0, 'vscode', 'D:/project', '研究', 1))
            db.commit(); db.close()
            db = sqlite3.connect(history)
            db.execute('CREATE TABLE thread_items(thread_id,turn_id,item_id,rollout_ordinal,created_at_ms,item_json,item_type)')
            db.execute('CREATE TABLE thread_turns(thread_id,turn_id,rollout_ordinal)')
            for sid in ('registered', 'orphan'):
                obj = json.dumps({'type': 'userMessage', 'content': [{'type': 'text', 'text': 'project-marker 请研究'}]})
                db.execute('INSERT INTO thread_items VALUES(?,?,?,?,?,?,?)', (sid,'turn','item',0,1791526757000,obj,'userMessage'))
                db.execute('INSERT INTO thread_turns VALUES(?,?,?)', (sid,'turn',0))
            db.commit(); db.close()
            official = root/'official'; official.mkdir()
            (official/'codex-archived-page-000.json').write_text(json.dumps({'threads':[{'id':'registered'}], 'nextCursor':None}))
            desktop = root/'desktop'; desktop.mkdir()
            (desktop/'archived-sessions.idx').write_text(json.dumps({'v':1,'archived':['local_ui']}))
            (desktop/'local_ui.json').write_text(json.dumps({'sessionId':'local_ui','cliSessionId':'native','cwd':'D:/project','isArchived':True}))
            raw = root/'raw'; raw.mkdir()
            cfg = {'sources':[{'platform':'claude','path':str(raw)}], 'project_roots':['D:/project'],
                   'explicit_project_markers':['project-marker'], 'inventories': {'codex_state':str(state),
                   'codex_history':str(history), 'claude_desktop_roots':[str(desktop)]}}
            index = {'sessions':[], 'since':'2026-10-01','until':'2026-10-21'}
            result = collect(cfg,index,official,root/'out')
            self.assertEqual({x['id'] for x in result['sessions']}, {'codex:registered','codex:orphan','claude-desktop:local_ui'})
            orphan = next(x for x in result['sessions'] if x['id']=='codex:orphan')
            self.assertEqual(orphan['registration_state'],'history-only')
            self.assertEqual(orphan['body_representation'],'database-projection')
            self.assertIn({'id':'claude-desktop:local_ui','kind':'registered-body-unavailable'},result['issues'])
            self.assertEqual(result['coverage_status'],'open')


if __name__ == '__main__':
    unittest.main()
