import json
from pathlib import Path
import tempfile
import unittest

from scripts.collect_journal_actions import collect, targets


class ActionTests(unittest.TestCase):
    def test_patch_targets_and_direct_writes_remain_distinct(self):
        self.assertEqual(targets('Write', {'file_path': 'D:/research/report.md'}),
                         [{'operation': 'write', 'path': 'D:/research/report.md'}])
        self.assertEqual(targets('exec', 'text(await tools.apply_patch("*** Begin Patch\\n*** Add File: reports/idea.md\\n+text\\n*** End Patch"))'),
                         [{'operation': 'add', 'path': 'reports/idea.md'}])

    def test_raw_write_receipt_keeps_id_and_hash_and_does_not_execute(self):
        rows = [
            {'type': 'assistant', 'sessionId': 'native', 'cwd': 'D:/research', 'timestamp': '2026-09-28T08:10:58Z',
             'message': {'content': [{'type': 'tool_use', 'id': 'write1', 'name': 'Write', 'input': {'file_path': 'D:/research/idea.md', 'content': 'original'}}]}},
            {'type': 'user', 'sessionId': 'native', 'timestamp': '2026-09-28T08:10:59Z',
             'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'write1', 'content': 'File created successfully'}]}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'session.jsonl'
            p.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
            index = {'sessions': [{'file': str(p), 'platform': 'claude', 'session_id': 'wrong-file-id', 'snapshot_bytes': p.stat().st_size}]}
            result = collect(index)
            action = result['actions'][0]
            self.assertEqual(action['session_id'], 'native')
            self.assertEqual(action['timestamp'], '2026-09-28T16:10:58.000+08:00')
            self.assertEqual(action['receipt']['line'], 2)
            self.assertEqual(len(action['line_sha256']), 64)
            self.assertEqual(result['failures'], [])
            self.assertFalse(Path('D:/research/idea.md').exists())


if __name__ == '__main__':
    unittest.main()
