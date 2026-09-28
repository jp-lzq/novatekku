import io
import json
import unittest

import plugin


class FakeClient:
    model = "test-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def complete(self, messages):
        self.requests.append(json.loads(messages[-1]["content"]))
        return json.dumps(self.responses.pop(0), ensure_ascii=False)


class NormalizeTest(unittest.TestCase):
    def test_models(self):
        cases = {
            "17PM": "iPhone 17 Pro Max",
            "iPhone17 ProMax": "iPhone 17 Pro Max",
            "iphone 16e": "iPhone 16e",
            "ｉＰｈｏｎｅ　１５ Pro": "iPhone 15 Pro",
            "iPhone Air": "iPhone Air",
            "Galaxy S25": None,
            "iPhone 7": None,
        }
        for raw, expected in cases.items():
            self.assertEqual(plugin.normalize_model(raw), expected, raw)

    def test_capacities(self):
        cases = {"256": "256", "256GB": "256", "1TB": "1TB", "1024GB": "1TB", "2": "2TB", "300GB": None, "": None}
        for raw, expected in cases.items():
            self.assertEqual(plugin.normalize_capacity(raw), expected, raw)

    def test_prices_in_text(self):
        self.assertIn(198000, plugin.prices_in_text("17PM 256 新品×3 19.8万"))
        self.assertIn(198000, plugin.prices_in_text("17PM 256 19万8千"))
        self.assertIn(198000, plugin.prices_in_text("iPhone 17 Pro Max ¥198,000"))
        self.assertNotIn(198000, plugin.prices_in_text("iPhone 17 Pro Max 19.5万"))


class ParserTest(unittest.TestCase):
    def test_valid_items_are_normalized(self):
        client = FakeClient([{"results": [{"index": 0, "items": [
            {"model": "17PM", "capacity": "256GB", "condition": "new", "quantity": 3, "unit_price": 198000},
        ]}]}])
        result = plugin.QuoteParser(client).parse(["17PM 256 新品×3 19.8万"])
        self.assertEqual(result[0]["items"], [{
            "model": "iPhone 17 Pro Max", "capacity": "256", "condition": "new",
            "quantity": 3, "unit_price": 198000, "subtotal": 594000,
        }])
        self.assertEqual(result[0]["errors"], [])

    def test_invented_price_is_rejected(self):
        client = FakeClient([{"results": [{"index": 0, "items": [
            {"model": "17 Pro", "capacity": "256", "condition": "new", "quantity": 1, "unit_price": 185000},
        ]}]}])
        result = plugin.QuoteParser(client).parse(["17 Pro 256 相場はだいたい18万台"])
        self.assertEqual(result[0]["items"], [])
        self.assertIn("does not appear", result[0]["errors"][0])

    def test_bad_values_are_reported_not_kept(self):
        client = FakeClient([{"results": [{"index": 0, "items": [
            {"model": "Pixel 9", "capacity": "256", "quantity": 1, "unit_price": 90000},
            {"model": "16", "capacity": "300", "quantity": 1, "unit_price": 90000},
            {"model": "16", "capacity": "128", "quantity": 0, "unit_price": 90000},
            {"model": "16", "capacity": "128", "quantity": True, "unit_price": 90000},
            {"model": "16", "capacity": "128", "condition": "mint", "unit_price": 90000},
        ]}]}])
        result = plugin.QuoteParser(client).parse(["16 128 90000"])
        self.assertEqual(len(result[0]["errors"]), 4)
        self.assertEqual(result[0]["items"][0]["condition"], "unknown")
        self.assertEqual(result[0]["items"][0]["quantity"], 1)

    def test_batches_keep_line_numbers(self):
        client = FakeClient([
            {"results": [{"index": 1, "items": [{"model": "16", "capacity": "128", "unit_price": 90000}]}]},
            {"results": [{"index": 0, "items": [{"model": "15", "capacity": "128", "unit_price": 60000}]}]},
        ])
        result = plugin.QuoteParser(client, batch_size=2).parse(["hello", "16 128 90000", "15 128 60,000円"])
        self.assertEqual([row["line"] for row in result], [1, 2, 3])
        self.assertEqual(result[0]["items"], [])
        self.assertEqual(result[2]["items"][0]["model"], "iPhone 15")
        self.assertEqual(len(client.requests), 2)

    def test_non_json_response_raises(self):
        class BrokenClient:
            def complete(self, messages):
                return "not json"
        with self.assertRaises(plugin.QuoteParserError):
            plugin.QuoteParser(BrokenClient()).parse(["16 128 90000"])

    def test_csv_output(self):
        stream = io.StringIO()
        plugin.write_csv([{"line": 1, "items": [{
            "model": "iPhone 16", "capacity": "128", "condition": "new",
            "quantity": 2, "unit_price": 90000, "subtotal": 180000,
        }]}], stream)
        self.assertEqual(stream.getvalue().splitlines()[1], "1,iPhone 16,128,new,2,90000,180000")


class ClientTest(unittest.TestCase):
    def test_request_payload(self):
        captured = {}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def opener(request, timeout):
            captured["body"] = json.loads(request.data)
            captured["auth"] = request.get_header("Authorization")
            return Response(json.dumps({"choices": [{"message": {"content": "{}"}}]}).encode())

        client = plugin.ChatClient("https://api.example.test/v1/chat/completions", "key", "model-x", opener=opener)
        self.assertEqual(client.complete([{"role": "user", "content": "x"}]), "{}")
        self.assertEqual(captured["body"]["temperature"], 0)
        self.assertEqual(captured["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(captured["auth"], "Bearer key")


if __name__ == "__main__":
    unittest.main()
