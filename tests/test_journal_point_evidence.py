import unittest

from scripts.journal_point_evidence import point_evidence


class PointEvidenceTests(unittest.TestCase):
    date = "2026-10-21"

    def resolve(self, items=(), sources=None, documents=None, cid="a"):
        return point_evidence(self.date, cid, {"items": list(items)}, sources or {}, documents or {},
                              {"r": "https://github.com/org/r/commit/{sha}"})

    def session(self, cid="a", stamp="2026-10-21T01:00:00+08:00"):
        return {"id": "codex:test", "title": "比较方案", "chains": [cid],
                "user_lines": [{"sha256": "a" * 64, "time": stamp}]}

    def test_no_commit_does_not_imply_discussion(self):
        self.assertEqual(self.resolve()["status"], "pending")

    def test_same_day_assigned_commit_and_session_are_both_preserved(self):
        item = {"date": self.date, "status": "assigned", "repo": "r", "sha": "b" * 40,
                "shares": {"a": {"numerator": 1, "denominator": 2}}, "paths": ["src/model.py"]}
        evidence = self.resolve([item], {"sessions": [self.session()]})
        self.assertEqual(evidence["status"], "artifact")
        self.assertEqual(evidence["kinds"], ["代码", "提交", "会话"])
        self.assertEqual(evidence["commit_count"], 1)
        self.assertEqual(evidence["session_count"], 1)
        self.assertTrue(evidence["artifacts"][0]["url"].endswith("b" * 40))

    def test_wrong_chain_day_pending_and_zero_share_do_not_create_artifacts(self):
        base = {"date": self.date, "status": "assigned", "repo": "r", "sha": "b" * 40,
                "shares": {"b": {"numerator": 1, "denominator": 1}}}
        for item in [base, {**base, "status": "pending"}, {**base, "date": "2026-10-20"},
                     {**base, "shares": {"a": {"numerator": 0, "denominator": 1}}}]:
            self.assertEqual(self.resolve([item])["status"], "pending")

    def test_document_without_commit_needs_write_receipt_not_filename_date(self):
        doc = {"id": "d", "title": "计划", "path": "PLAN/2026-10-21.md", "sha256": "c" * 64,
               "chains": ["a"], "disposition": "primary", "write_dates": [self.date]}
        sources = {"documents": ["d"]}
        self.assertEqual(self.resolve(sources=sources, documents={"d": doc})["status"], "pending")
        doc["write_evidence"] = [{"date": self.date, "operation": "add", "basis": "native-file-change", "receipt_line_sha256": "d" * 64}]
        result = self.resolve(sources=sources, documents={"d": doc})
        self.assertEqual(result["status"], "artifact")
        self.assertEqual(result["commit_count"], 0)
        self.assertEqual(result["document_count"], 1)
        doc["write_evidence"][0]["operation"] = "delete"
        self.assertEqual(self.resolve(sources=sources, documents={"d": doc})["status"], "pending")
        doc["write_evidence"][0]["operation"] = "update"
        doc["write_evidence"][0]["date"] = "2026-10-20"
        self.assertEqual(self.resolve(sources=sources, documents={"d": doc})["status"], "pending")

    def test_discussion_requires_located_message_on_actual_beijing_day(self):
        self.assertEqual(self.resolve(sources={"sessions": [self.session()]})["status"], "discussion")
        # UTC 前一天的 17 时属于北京时间当天；无时区时间不得猜测。
        for stamp, expected in [("2026-10-20T17:00:00Z", "discussion"),
                                ("2026-10-20T15:00:00Z", "pending"), ("2026-10-21T01:00:00", "pending")]:
            self.assertEqual(self.resolve(sources={"sessions": [self.session(stamp=stamp)]})["status"], expected)
        self.assertEqual(self.resolve(sources={"sessions": [self.session(cid="b")]})["status"], "pending")


if __name__ == "__main__":
    unittest.main()
