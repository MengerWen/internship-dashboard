import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('sessions', Path(__file__).resolve().parents[1] / 'scripts/collect_journal_sessions.py')
sessions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sessions)


class SessionEvidenceTests(unittest.TestCase):
    def test_heartbeat_is_retained_without_becoming_a_human_decision(self):
        record = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                  'content': [{'type': 'input_text', 'text': '<heartbeat>monitor sirui-quant-research</heartbeat>'}]}}
        self.assertEqual(sessions.message(record, 'codex')['evidence_kind'], 'automation-message')

    def test_human_choice_reply_extracts_answer_without_adopting_question(self):
        text = '<send_user_message_question_reply>\n' + json.dumps([
            {'question': '问题文本不是用户的新决定', 'answer': '好了优化到这样已经可以了'}
        ], ensure_ascii=False) + '\n</send_user_message_question_reply>'
        record = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                  'content': [{'type': 'input_text', 'text': text}]}}
        item = sessions.message(record, 'codex')
        self.assertIsNotNone(item)
        self.assertEqual(item['text'], '好了优化到这样已经可以了')
        self.assertEqual(item['evidence_kind'], 'user-choice')

    def test_claude_mixed_file_keeps_native_id_for_each_message(self):
        rows = [
            {'type': 'user', 'sessionId': 'original', 'cwd': 'D:/research',
             'timestamp': '2026-08-01T01:00:00Z', 'uuid': 'one',
             'message': {'role': 'user', 'content': '前面的研究'}},
            {'type': 'user', 'sessionId': 'continued', 'cwd': 'D:/research',
             'timestamp': '2026-08-02T01:00:00Z', 'uuid': 'two',
             'message': {'role': 'user', 'content': '后续研究'}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'continued.jsonl'
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
            result = sessions.collect({'sources': [{'name': 'fixture', 'path': folder, 'platform': 'claude'}],
                'project_roots': ['D:/research'], 'explicit_project_markers': []}, '2026-08-01', '2026-08-03')
            by_id = {s['session_id']: s['messages'] for s in result['sessions']}
            self.assertEqual(set(by_id), {'original', 'continued'})
            self.assertEqual(by_id['continued'][0]['text'], '后续研究')
            self.assertEqual(by_id['continued'][0]['line'], 2)
            self.assertEqual(by_id['continued'][0]['session_id'], 'continued')

    def test_project_reference_after_first_message_is_discovered(self):
        rows = [
            {'type': 'session_meta', 'payload': {'id': 'outside', 'cwd': 'D:/tools'}},
            {'type': 'response_item', 'timestamp': '2026-08-01T01:00:00Z',
             'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': '先安装工具'}]}},
            {'type': 'response_item', 'timestamp': '2026-08-02T01:00:00Z',
             'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': '再转换 sirui-quant-research 的研究文件'}]}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'outside.jsonl'
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
            result = sessions.collect({'sources': [{'name': 'fixture', 'path': folder, 'platform': 'codex'}],
                'project_roots': ['D:/research'], 'explicit_project_markers': ['sirui-quant-research']}, '2026-08-01', '2026-08-03')
            self.assertEqual(len(result['sessions']), 1)
            self.assertEqual(result['sessions'][0]['scope_basis'], 'user-project-reference')
            self.assertEqual(result['sessions'][0]['messages'][-1]['date'], '2026-08-02')

    def test_quoted_chat_preview_does_not_claim_unrelated_project(self):
        text = '## Referenced ChatGPT conversation:\n{"priorConversation":"sirui-quant-research"}\n## My request:\n解释一下代理设置'
        self.assertEqual(sessions.scope_text(text), '解释一下代理设置')

    def test_file_dispositions_account_for_empty_and_outside_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'outside.jsonl'
            path.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 'outside', 'cwd': 'D:/elsewhere'}}) + '\n', encoding='utf-8')
            result = sessions.collect({'sources': [{'name': 'fixture', 'path': folder, 'platform': 'codex'}],
                'project_roots': ['D:/research'], 'explicit_project_markers': []}, '2026-08-01', '2026-08-03')
            self.assertEqual(result['files'][0]['disposition'], 'outside-project-scope')
            self.assertEqual(len(result['files']), result['counts']['files_discovered'])

    def test_scope_uses_directory_boundary_and_windows_case(self):
        self.assertTrue(sessions.within('d:\\Research\\child', ['D:/research']))
        self.assertFalse(sessions.within('D:/research-private', ['D:/research']))

    def test_no_system_thinking_tools_or_compaction_as_human_evidence(self):
        def codex(role, text, **extra):
            return {'type': 'response_item', 'payload': {'type': 'message', 'role': role, 'content': [{'type': 'output_text', 'text': text}], **extra}}
        self.assertIsNone(sessions.message(codex('developer', 'rule'), 'codex'))
        self.assertIsNone(sessions.message(codex('assistant', 'thinking', channel='analysis'), 'codex'))
        self.assertIsNone(sessions.message(codex('assistant', 'update', phase='commentary'), 'codex'))
        self.assertIsNone(sessions.message(codex('user', '# AGENTS.md instructions for project'), 'codex'))
        self.assertEqual(sessions.message(codex('user', '请核对回放'), 'codex')['text'], '请核对回放')
        self.assertIsNone(sessions.message({'type': 'user', 'isCompactSummary': True, 'message': {'role': 'user', 'content': 'summary'}}, 'claude'))
        self.assertIsNone(sessions.message({'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'content': 'receipt'}]}}, 'claude'))

    def test_actual_message_date_crosses_midnight_and_invalid_time_is_reported(self):
        rows = [
            {'type': 'user', 'timestamp': '2026-08-01T15:59:59Z', 'uuid': 'one', 'message': {'role': 'user', 'content': '第一天'}},
            {'type': 'user', 'timestamp': '2026-08-01T16:00:00Z', 'uuid': 'two', 'message': {'role': 'user', 'content': '第二天'}},
            {'type': 'assistant', 'timestamp': '2026-08-02T01:00:00', 'message': {'role': 'assistant', 'content': '没有时区'}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session.jsonl'
            path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows) + '{partial', encoding='utf-8')
            result = sessions.scan_file(path, 'claude', '2026-08-02', '2026-08-02')
            self.assertEqual([r['text'] for r in result['messages']], ['第二天'])
            self.assertEqual(len(result['problems']), 2)
            self.assertEqual(result['messages'][0]['line'], 2)
            ref = {**result['messages'][0], 'excerpt': '第二天', 'session_id': 'id', 'platform': 'claude'}
            index = {'sessions': [{'session_id': 'id', 'platform': 'claude', 'file': str(path), **result}]}
            sessions.verify_ref(ref, index)
            with path.open('a', encoding='utf-8') as handle:
                handle.write('\n追加')
            sessions.verify_ref(ref, index)
            with self.assertRaisesRegex(ValueError, '摘录'):
                sessions.verify_ref({**ref, 'excerpt': '编造内容'}, index)
            path.write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '已变化'):
                sessions.verify_ref(ref, index)

    def test_missing_source_not_silently_empty(self):
        result = sessions.collect({'sources': [{'name': 'missing', 'path': 'Z:/does-not-exist/session-fixture', 'platform': 'codex'}], 'project_roots': [], 'explicit_project_markers': []}, '2026-08-01', '2026-08-02')
        self.assertEqual(result['failures'][0]['error'], 'source_missing')

    def test_daily_render_preserves_other_dates_and_escapes_original_text(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'content/journal'
            target.mkdir(parents=True)
            old = target / '2026-08-01.md'
            old.write_text('人工正文\n<!-- journal-session-evidence:start -->旧证据<!-- journal-session-evidence:end -->\n', encoding='utf-8')
            original = old.read_bytes()
            fresh = target / '2026-08-02.md'
            fresh.write_text('当日正文\n', encoding='utf-8')
            entry = {'date': '2026-08-02', 'platform': 'codex', 'kind': 'user-request',
                     'timestamp': '2026-08-02T01:00:00+08:00', 'supports': '研究要求',
                     'excerpt': '<script>wrong</script>', 'session_id': 'id', 'line': 2,
                     'line_sha256': 'a' * 64}
            with patch.object(sessions, 'ROOT', root):
                manifest = {'entries': [entry]}
                self.assertEqual(sessions.render_manifest(manifest), ['2026-08-02'])
                self.assertEqual(sessions.render_manifest(manifest, check=True), [])
            self.assertEqual(old.read_bytes(), original)
            self.assertIn('&lt;script&gt;', fresh.read_text(encoding='utf-8'))
            self.assertTrue(fresh.read_text(encoding='utf-8').startswith('当日正文\n'))


if __name__ == '__main__':
    unittest.main()
