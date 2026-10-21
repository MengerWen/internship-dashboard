import copy
import unittest

from scripts.reconcile_journal_sources import canonical, digest, public_ledger, reconcile


class ReconciliationTests(unittest.TestCase):
    def fixture(self):
        material = {'files': [{'id': 'f', 'source': 'r', 'path': 'reports/a.md', 'kind': 'document',
            'git_state': 'untracked', 'sha256': 'h', 'filename_dates': ['2020-01-01']}],
            'commits': [], 'snapshots': [], 'directory_exclusions': [], 'failures': []}
        message = {'date': '2026-10-14', 'timestamp': '2026-10-14T12:00:00+08:00',
                   'line_sha256': 'm', 'line': 12, 'role': 'user'}
        session = {'sessions': [{'platform': 'codex', 'session_id': 's', 'messages': [message]}],
                   'files': [], 'failures': []}
        decisions = {'documents': {'f': {'chains': ['idea'], 'disposition': 'primary', 'review_level': 'review'}},
                     'sessions': {'codex:s': {'chains': ['idea'], 'disposition': 'research-related'}},
                     'material_universe_sha256': digest([('f', 'h', None, 'document')]),
                     'message_universe_sha256': digest(['codex:s:m'])}
        config = {'sources': [{'id': 'r', 'path': '.'}]}
        return material, session, {'actions': [], 'failures': []}, decisions, config

    def test_missing_session_decision_fails_instead_of_silently_dropping(self):
        args = self.fixture()
        args[3]['sessions'].clear()
        with self.assertRaisesRegex(ValueError, '会话决议 未守恒'):
            reconcile(*args)

    def test_filename_and_read_are_not_write_date_proof(self):
        args = self.fixture()
        result = reconcile(*args)
        self.assertEqual(result['files'][0]['write_evidence'], [])
        self.assertEqual(result['messages'][0]['date'], '2026-10-14')
        self.assertNotIn('path', public_ledger(result)['files'][0])
        self.assertEqual(public_ledger(result)['files'][0]['destination'], ['chain:idea'])

    def test_changed_or_failed_input_cannot_pass_coverage(self):
        for mode in ('changed', 'failed'):
            args = self.fixture()
            if mode == 'changed':
                args[0]['files'][0]['changed_during_read'] = True
            else:
                args[2]['failures'] = ['unreadable']
            with self.assertRaises(ValueError):
                reconcile(*args)

    def test_new_report_and_new_message_cannot_inherit_old_review(self):
        for kind in ('file', 'message'):
            args = self.fixture()
            if kind == 'file':
                new = dict(args[0]['files'][0], id='new', path='reports/missing.md')
                args[0]['files'].append(new)
            else:
                args[1]['sessions'][0]['messages'].append(dict(args[1]['sessions'][0]['messages'][0], line_sha256='new'))
            with self.assertRaisesRegex(ValueError, '范围'):
                reconcile(*args)

    def test_duplicate_physical_messages_have_one_native_identity(self):
        args = self.fixture()
        args[1]['sessions'].append(copy.deepcopy(args[1]['sessions'][0]))
        result = reconcile(*args)
        self.assertEqual(len(result['sessions']), 1)
        self.assertEqual(len(result['messages']), 1)

    def test_windows_alias_and_slash_prefix_match_without_losing_drive(self):
        self.assertEqual(canonical('/D:/MG/！Internship/26 Summer/❗思瑞投资/a.md'),
                         canonical('D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/a.md'))
        self.assertEqual(canonical(r'D:\\MG\\！Internship\\26 Summer\\❗思瑞投资\\a.md'),
                         canonical('D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/a.md'))


if __name__ == '__main__':
    unittest.main()
