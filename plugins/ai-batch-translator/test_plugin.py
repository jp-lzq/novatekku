import json
import unittest

import plugin


class FakeClient:
    model = "test-model"

    def __init__(self):
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        request = json.loads(messages[-1]["content"])
        return json.dumps(
            {"translations": [f"JA:{text}" for text in request["texts"]]},
            ensure_ascii=False,
        )


class TranslatorTest(unittest.TestCase):
    def test_preserves_placeholders_and_urls(self):
        client = FakeClient()
        translator = plugin.BatchTranslator(client, batch_size=2)
        result = translator.translate(
            ["Hello {name}", "Open https://example.com/a?q=1", "Total: %s"],
            "ja",
            "en",
        )
        self.assertEqual(result[0], "JA:Hello {name}")
        self.assertEqual(result[1], "JA:Open https://example.com/a?q=1")
        self.assertEqual(result[2], "JA:Total: %s")
        self.assertEqual(client.calls, 2)

    def test_cache_avoids_second_request(self):
        client = FakeClient()
        cache = plugin.TranslationCache()
        translator = plugin.BatchTranslator(client, cache=cache)
        first = translator.translate(["Hello"], "ja", "en")
        second = translator.translate(["Hello"], "ja", "en")
        self.assertEqual(first, second)
        self.assertEqual(client.calls, 1)
        cache.close()

    def test_rejects_changed_placeholder(self):
        with self.assertRaisesRegex(plugin.TranslationError, "placeholder 0"):
            plugin.restore("missing", ["{name}"])

    def test_run_shape(self):
        result = plugin.run(
            {"texts": ["one"], "source": "en", "target": "ja"},
            client=FakeClient(),
        )
        self.assertEqual(result, {"translations": ["JA:one"]})


if __name__ == "__main__":
    unittest.main()
