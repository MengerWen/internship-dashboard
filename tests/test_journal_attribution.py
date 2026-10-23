"""提交计量的守恒、隔离和原始身份检查。"""
import copy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import unittest

from scripts.collect_journal_attribution import attribute, classify, summarize_day

ROOT = Path(__file__).resolve().parents[1]


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads((ROOT / "scripts/journal_attribution_rules.json").read_text(encoding="utf-8"))
        self.chains = {c["id"] for c in json.loads((ROOT / "content/chains.json").read_text(encoding="utf-8"))["chains"]}

    def test_every_published_commit_is_unique_and_conserved(self):
        seen = set()
        for path in (ROOT / "content/journal/_attribution").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            summary = summarize_day(payload, self.chains)
            evidence = json.loads((ROOT / "content/journal/_evidence" / path.name).read_text(encoding="utf-8"))
            self.assertEqual(summary["repos"], {r["repo"]: r["commits"] for r in evidence["repos"]})
            assigned = sum(Fraction(v["numerator"], v["denominator"]) for v in summary["chains"].values())
            self.assertEqual(assigned, sum(summary["statuses"].get(s, 0) for s in ["assigned", "shared"]))
            for item in payload["items"]:
                identity = (item["repo"], item["sha"])
                self.assertNotIn(identity, seen)
                seen.add(identity)
        self.assertGreater(len(seen), 2800)

    def test_ambiguous_shared_code_is_not_assigned_from_date_alone(self):
        result = classify({"repo": "sirui-quant-research", "date": "2026-10-16", "sha": "a" * 40,
                           "subject": "修正公共接口", "paths": ["lv2_snapshot_workspace/src/snapshot/scheduler.py"]}, self.rules)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["chains"], [])

    def test_mixed_tasks_split_one_commit_without_counting_shared_dependencies(self):
        commit = {"repo": "sirui-quant-research", "date": "2026-10-20", "sha": "a" * 40,
                  "subject": "记录344准备与环境恢复", "paths": ["PLAN/new-corrected-replay-344.md", "reports/new-wangly-environment.md"],
                  "changes": {"PLAN/new-corrected-replay-344.md": "A", "reports/new-wangly-environment.md": "A"}}
        result = attribute([commit], self.rules)[0]
        self.assertEqual(set(result["chains"]), {"corrected-replay-344", "wangly-env"})
        self.assertEqual(sum(Fraction(**share) for share in result["shares"].values()), 1)
        commit["changes"]["reports/new-wangly-environment.md"] = "M"
        self.assertEqual(attribute([commit], self.rules)[0]["chains"], ["corrected-replay-344"])

    def test_collector_does_not_confuse_stock_code_300344_with_344_recalibration(self):
        result = attribute([{"repo": "sirui-quant-research", "date": "2026-08-09", "sha": "a" * 40,
                             "subject": "fix: add missing 300344 quote exemption", "paths": ["scripts/run_open5m.py"]}], self.rules)[0]
        self.assertEqual(result["chains"], ["open5m"])

    def test_new_dates_require_review_even_when_the_title_matches_a_known_task(self):
        unreviewed_day = (date.fromisoformat(self.rules["reviewed_through"]) + timedelta(days=1)).isoformat()
        result = classify({"repo": "sirui-quant-research", "date": unreviewed_day, "sha": "c" * 40,
                           "subject": "继续344定参", "paths": ["scripts/run_corrected_replay_344.py"]}, self.rules)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["chains"], [])

    def test_duplicate_and_overallocated_evidence_are_rejected(self):
        item = {"date": "2026-10-20", "repo": "r", "sha": "a" * 40, "status": "assigned",
                "shares": {"replay": {"numerator": 1, "denominator": 1}}}
        payload = {"date": "2026-10-20", "items": [item, item]}
        with self.assertRaises(ValueError):
            summarize_day(payload, self.chains)
        payload["items"] = [copy.deepcopy(item)]
        payload["items"][0]["shares"]["sse-v2"] = {"numerator": 1, "denominator": 1}
        with self.assertRaises(ValueError):
            summarize_day(payload, self.chains)


if __name__ == "__main__":
    unittest.main()
