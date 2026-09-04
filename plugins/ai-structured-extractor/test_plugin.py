import unittest

import plugin


SCHEMA = {
    "type": "object",
    "properties": {
        "model": {"type": "string"},
        "price": {"type": ["integer", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["model", "price", "tags"],
    "additionalProperties": False,
}


class FakeClient:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def complete(self, messages, schema):
        self.calls.append((messages, schema))
        return self.answer


class ExtractorTest(unittest.TestCase):
    def test_extracts_and_validates(self):
        client = FakeClient('```json\n{"model":"iPhone 17","price":218000,"tags":["新品"]}\n```')
        result = plugin.extract(client, "iPhone 17 新品 218,000円", SCHEMA)
        self.assertEqual(result["price"], 218000)
        self.assertEqual(client.calls[0][1], SCHEMA)

    def test_rejects_missing_required_field(self):
        client = FakeClient('{"model":"iPhone 17","price":null}')
        with self.assertRaisesRegex(plugin.ApiError, "tags is required"):
            plugin.extract(client, "iPhone 17", SCHEMA)

    def test_rejects_unknown_field(self):
        value = {"model": "iPhone 17", "price": None, "tags": [], "extra": True}
        with self.assertRaisesRegex(plugin.ApiError, "unknown fields"):
            plugin.validate(value, SCHEMA)

    def test_message_array(self):
        response = {
            "choices": [{"message": {"content": [{"type": "text", "text": "{}"}]}}]
        }
        self.assertEqual(plugin.message_text(response), "{}")


if __name__ == "__main__":
    unittest.main()
