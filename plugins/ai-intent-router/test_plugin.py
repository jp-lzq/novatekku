import json
import unittest

import plugin


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def complete(self, messages):
        self.requests.append(json.loads(messages[-1]["content"]))
        response = self.responses.pop(0)
        return response if isinstance(response, str) else json.dumps(response)


class RuleTest(unittest.TestCase):
    def test_keyword_rules_in_three_languages(self):
        cases = {
            "iPhone 17 Pro 256GB 现在多少钱？": "price",
            "17 Pro Max 256 x3 合計はいくら？": "bulk_total",
            "现在有哪些型号可以查？": "catalog",
            "Is now a good time to sell my iPhone?": "selling",
            "中古で買うならどれがいい？": "buying",
            "安卓换到 iPhone 怎么迁移微信？": "migration",
            "iPhoneが充電中に熱いです": "troubleshooting",
            "How do I set up eSIM on iPhone?": "phone_other",
            "今天东京天气怎么样？": "off_topic",
        }
        for question, intent in cases.items():
            self.assertEqual(plugin.rule_intent(question), intent, question)

    def test_rules_only_router(self):
        result = plugin.IntentRouter().route(["iPhone 16 买取价格", "hello"])
        self.assertEqual([(r["intent"], r["source"]) for r in result], [("price", "rules"), ("off_topic", "rules")])


class ModelTest(unittest.TestCase):
    def test_confident_model_label_is_used(self):
        client = FakeClient([{"results": [{"index": 0, "intent": "selling", "confidence": 0.92}]}])
        result = plugin.IntentRouter(client).route(["手放すタイミングを知りたい"])
        self.assertEqual(result[0], {"question": "手放すタイミングを知りたい", "intent": "selling", "confidence": 0.92, "source": "model"})

    def test_invalid_or_unsure_labels_fall_back_to_rules(self):
        client = FakeClient([{"results": [
            {"index": 0, "intent": "weather", "confidence": 0.99},
            {"index": 1, "intent": "price", "confidence": 0.3},
            {"index": 2, "intent": "price", "confidence": True},
        ]}])
        result = plugin.IntentRouter(client).route(["今天天气", "iPhone 17 多少钱", "battery drains fast"])
        self.assertEqual([(r["intent"], r["source"]) for r in result],
                         [("off_topic", "rules"), ("price", "rules"), ("troubleshooting", "rules")])

    def test_batches_keep_order(self):
        client = FakeClient([
            {"results": [{"index": 0, "intent": "price", "confidence": 0.9}, {"index": 1, "intent": "catalog", "confidence": 0.9}]},
            {"results": [{"index": 0, "intent": "migration", "confidence": 0.9}]},
        ])
        result = plugin.IntentRouter(client, batch_size=2).route(["a", "b", "c"])
        self.assertEqual([r["intent"] for r in result], ["price", "catalog", "migration"])
        self.assertEqual(len(client.requests), 2)

    def test_non_json_raises(self):
        with self.assertRaises(plugin.RouterError):
            plugin.IntentRouter(FakeClient(["nope"])).route(["a"])


class EvaluateTest(unittest.TestCase):
    def test_accuracy_and_confusion(self):
        routed = [{"intent": "price"}, {"intent": "selling"}, {"intent": "price"}]
        report = plugin.evaluate(routed, ["price", "price", "price"])
        self.assertEqual(report["correct"], 2)
        self.assertEqual(report["accuracy"], 0.6667)
        self.assertEqual(report["confusion"], {"price->selling": 1})


if __name__ == "__main__":
    unittest.main()
