import json
import os
import tempfile
import unittest

import plugin


class FakeClient:
    model = "test-model"

    def __init__(self, grade):
        self.grade = grade
        self.requests = []

    def complete(self, messages):
        self.requests.append(json.loads(messages[-1]["content"]))
        return self.grade if isinstance(self.grade, str) else json.dumps(self.grade)


GOOD = {"accuracy": 5, "helpfulness": 4, "invented": False, "reason": "matches reference"}


def case(**values):
    return {"id": 1, "category": "本地价格", "language": "zh", "question": "iPhone 17 多少钱？",
            "answer": "iPhone 17 256GB 当前最高回收价是 120,000 日元。", **values}


class RuleTest(unittest.TestCase):
    def test_language_detection(self):
        self.assertEqual(plugin.detect_language("当前最高回收价是 120,000 日元"), "zh")
        self.assertEqual(plugin.detect_language("現在の最高買取価格は森森買取です"), "ja")
        self.assertEqual(plugin.detect_language("The best price is 120,000 yen."), "en")
        self.assertEqual(plugin.detect_language("最高是モバイルミックス和森森買取，均为 184,000 日元"), "zh")
        self.assertEqual(plugin.detect_language("The top store is モバイルミックス at 184,000 yen today."), "en")

    def test_rules(self):
        self.assertEqual(plugin.rule_check(case()), [])
        self.assertEqual(plugin.rule_check(case(answer="  ")), ["empty answer"])
        self.assertIn("answer language is en, expected zh", plugin.rule_check(case(answer="The price is 120,000 yen.")))
        self.assertIn("table layout in answer", plugin.rule_check(case(answer="价格如下\n| 店铺 | 价格 |\n|---|---|")))
        self.assertIn("missing required text: 均价", plugin.rule_check(case(must_include=["均价"])))
        self.assertIn("contains forbidden text: 120,000", plugin.rule_check(case(must_not_include=["120,000"])))


class JudgeTest(unittest.TestCase):
    def test_pass_with_good_grade_and_reference_is_sent(self):
        client = FakeClient(GOOD)
        result = plugin.AnswerJudge(client, reference={"iPhone 17 256": 120000}).judge(case())
        self.assertTrue(result["passed"])
        self.assertEqual(client.requests[0]["REFERENCE"], {"iPhone 17 256": 120000})

    def test_invented_or_inaccurate_fails(self):
        self.assertFalse(plugin.AnswerJudge(FakeClient({**GOOD, "invented": True})).judge(case())["passed"])
        self.assertFalse(plugin.AnswerJudge(FakeClient({**GOOD, "accuracy": 2})).judge(case())["passed"])

    def test_rule_failure_skips_model_and_fails(self):
        client = FakeClient(GOOD)
        result = plugin.AnswerJudge(client).judge(case(answer=""))
        self.assertFalse(result["passed"])
        self.assertEqual(client.requests, [])

    def test_scores_are_clamped_and_bad_output_fails(self):
        grade = plugin.AnswerJudge(FakeClient({**GOOD, "accuracy": 9, "helpfulness": -1})).judge(case())["grade"]
        self.assertEqual((grade["accuracy"], grade["helpfulness"]), (5, 0))
        for bad in ("not json", {"accuracy": 5}, {**GOOD, "accuracy": "high"}):
            result = plugin.AnswerJudge(FakeClient(bad)).judge(case())
            self.assertFalse(result["passed"])
            self.assertIn("grade_error", result)

    def test_rules_only_mode(self):
        report = plugin.AnswerJudge().run([case(), case(id=2, answer="")])
        self.assertEqual(report["summary"]["total"], 2)
        self.assertEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["summary"]["pass_rate"], 0.5)
        self.assertIsNone(report["summary"]["average_accuracy"])

    def test_summary_by_category(self):
        report = plugin.AnswerJudge(FakeClient(GOOD)).run([case(), case(id=2, category="数据迁移")])
        self.assertEqual(report["summary"]["by_category"]["数据迁移"], {"total": 1, "passed": 1})
        self.assertEqual(report["summary"]["average_accuracy"], 5)


class CatalogTest(unittest.TestCase):
    def test_reads_nova_catalog_format(self):
        catalog = {"model": "m", "cases": {"ja": [{"id": 1, "question": "q", "answer": "a"}],
                                           "en": [{"id": 2, "question": "q", "answer": "a"}]}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(catalog, handle)
        try:
            cases = plugin.load_cases(handle.name)
        finally:
            os.unlink(handle.name)
        self.assertEqual([(row["id"], row["language"]) for row in cases], [(1, "ja"), (2, "en")])

    def test_repository_catalog_passes_rule_checks(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "data", "aiTestCases.json")
        if not os.path.exists(path):
            self.skipTest("catalog not present")
        report = plugin.AnswerJudge().run(plugin.load_cases(path))
        self.assertGreater(report["summary"]["total"], 0)
        failed = [(row["id"], row["language"], row["rule_problems"]) for row in report["results"] if not row["passed"]]
        self.assertEqual(failed, [])


if __name__ == "__main__":
    unittest.main()
