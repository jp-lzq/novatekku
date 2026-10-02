import io
import json
import unittest

import plugin


def rows(model, capacity, prices):
    return [{"model": model, "capacity": capacity, "store": f"S{i}", "price": p} for i, p in enumerate(prices)]


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def complete(self, messages):
        self.requests.append(json.loads(messages[-1]["content"]))
        return self.response if isinstance(self.response, str) else json.dumps(self.response)


class DetectTest(unittest.TestCase):
    def test_flags_outlier_but_not_normal_spread(self):
        data = rows("iPhone 17 Pro", "256", [182000, 181500, 183000, 180500, 182500, 18200])
        found = plugin.detect(data)
        self.assertEqual([(a["store"], a["price"]) for a in found], [("S5", 18200)])
        self.assertLess(found[0]["difference_percent"], -80)

    def test_small_groups_are_skipped(self):
        self.assertEqual(plugin.detect(rows("iPhone 16", "128", [90000, 91000, 20000])), [])

    def test_flat_prices_use_tolerance(self):
        found = plugin.detect(rows("iPhone 15", "128", [60000, 60000, 60000, 60000, 66000]))
        self.assertEqual([a["price"] for a in found], [66000])
        self.assertIsNone(found[0]["robust_z"])
        self.assertEqual(plugin.detect(rows("iPhone 15", "128", [60000, 60000, 60000, 61000])), [])

    def test_groups_are_independent(self):
        data = rows("iPhone 17", "256", [120000] * 4 + [121000]) + rows("iPhone 17", "512", [150000, 151000, 149000, 150500])
        self.assertEqual(plugin.detect(data), [])


class ReadTest(unittest.TestCase):
    def test_reads_csv_with_commas_in_prices(self):
        text = 'model,capacity,store,price\niPhone 17,256,A,"120,000"\n'
        self.assertEqual(plugin.read_prices(io.StringIO(text))[0]["price"], 120000)

    def test_rejects_bad_rows(self):
        for text in ("model,capacity,store,price\niPhone 17,256,A,abc\n", "model,capacity,store,price\n,256,A,1000\n"):
            with self.assertRaises(plugin.AnomalyError):
                plugin.read_prices(io.StringIO(text))


class ExplainTest(unittest.TestCase):
    def setUp(self):
        self.anomalies = plugin.detect(rows("iPhone 17 Pro", "256", [182000, 181500, 183000, 180500, 18200]))

    def test_valid_explanation_is_attached(self):
        client = FakeClient({"explanations": [{"id": 0, "cause": "typo", "note": "missing a zero"}]})
        result = plugin.AnomalyExplainer(client).explain(self.anomalies)
        self.assertEqual((result[0]["cause"], result[0]["note"]), ("typo", "missing a zero"))
        self.assertEqual(client.requests[0]["items"][0]["price"], 18200)

    def test_unknown_cause_and_foreign_ids_are_ignored(self):
        client = FakeClient({"explanations": [{"id": 0, "cause": "aliens"}, {"id": 99, "cause": "typo"}]})
        result = plugin.AnomalyExplainer(client).explain(self.anomalies)
        self.assertEqual(result[0]["cause"], "unknown")
        self.assertEqual(len(result), 1)

    def test_detection_is_kept_when_model_says_nothing(self):
        result = plugin.AnomalyExplainer(FakeClient({"explanations": []})).explain(self.anomalies)
        self.assertEqual(result[0]["price"], 18200)
        self.assertIsNone(result[0]["cause"])

    def test_non_json_raises(self):
        with self.assertRaises(plugin.AnomalyError):
            plugin.AnomalyExplainer(FakeClient("oops")).explain(self.anomalies)


if __name__ == "__main__":
    unittest.main()
