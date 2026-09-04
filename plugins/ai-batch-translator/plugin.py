import argparse
import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path


PLACEHOLDERS = re.compile(
    r"(https?://[^\s]+|\{\{[^{}]+\}\}|\$\{[^{}]+\}|\{[^{}]+\}|%(?:\([^)]+\))?[#0 +\-]?(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrs%])"
)


class TranslationError(RuntimeError):
    pass


class ChatClient:
    def __init__(self, endpoint, api_key, model, timeout=60, retries=2, opener=None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.opener = opener or urllib.request.urlopen

    @classmethod
    def from_env(cls):
        endpoint = os.environ.get("AI_API_URL", "").strip()
        api_key = os.environ.get("AI_API_KEY", "").strip()
        model = os.environ.get("AI_MODEL", "").strip()
        if not endpoint or not api_key or not model:
            raise TranslationError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
        return cls(endpoint, api_key, model)

    def complete(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise TranslationError("message content is not text")
                return content
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise TranslationError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as error:
                if attempt == self.retries:
                    raise TranslationError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise TranslationError("request failed")


class TranslationCache:
    def __init__(self, filename=":memory:"):
        self.connection = sqlite3.connect(filename)
        self.connection.execute(
            "create table if not exists translations "
            "(cache_key text primary key, translated_text text not null, created_at text default current_timestamp)"
        )

    def get(self, key):
        row = self.connection.execute(
            "select translated_text from translations where cache_key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def put(self, key, value):
        self.connection.execute(
            "insert or replace into translations(cache_key, translated_text) values (?, ?)",
            (key, value),
        )
        self.connection.commit()

    def close(self):
        self.connection.close()


def protect(text):
    values = []

    def replace(match):
        token = f"[[[P{len(values)}]]]"
        values.append(match.group(0))
        return token

    return PLACEHOLDERS.sub(replace, text), values


def restore(text, values):
    for index, value in enumerate(values):
        token = f"[[[P{index}]]]"
        if token not in text:
            raise TranslationError(f"placeholder {index} was changed")
        text = text.replace(token, value)
    return text


def parse_translations(content, expected):
    try:
        payload = json.loads(content)
        values = payload["translations"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise TranslationError("model returned invalid translation JSON") from error
    if not isinstance(values, list) or len(values) != expected:
        raise TranslationError("translation count does not match input")
    if not all(isinstance(value, str) for value in values):
        raise TranslationError("translations must be strings")
    return values


def cache_key(model, source, target, text):
    value = "\0".join((model, source, target, text)).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


class BatchTranslator:
    def __init__(self, client, cache=None, batch_size=20):
        self.client = client
        self.cache = cache or TranslationCache()
        self.batch_size = max(1, min(int(batch_size), 100))

    def translate(self, texts, target, source="auto"):
        if not target.strip():
            raise ValueError("target language is required")
        output = [None] * len(texts)
        missing = []
        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"item {index} is not text")
            if not text:
                output[index] = ""
                continue
            key = cache_key(self.client.model, source, target, text)
            cached = self.cache.get(key)
            if cached is None:
                missing.append((index, text, key))
            else:
                output[index] = cached

        for start in range(0, len(missing), self.batch_size):
            batch = missing[start:start + self.batch_size]
            protected = [protect(text) for _, text, _ in batch]
            request = {
                "source_language": source,
                "target_language": target,
                "texts": [text for text, _ in protected],
            }
            content = self.client.complete(
                [
                    {
                        "role": "system",
                        "content": "Translate each item naturally. Keep every [[[P0]]] style token unchanged and return JSON with a translations array.",
                    },
                    {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
                ]
            )
            translated = parse_translations(content, len(batch))
            for (index, _, key), value, (_, placeholders) in zip(batch, translated, protected):
                value = restore(value, placeholders)
                output[index] = value
                self.cache.put(key, value)
        return output


def run(payload, client=None, cache=None):
    client = client or ChatClient.from_env()
    translator = BatchTranslator(
        client,
        cache=cache,
        batch_size=payload.get("batch_size", 20),
    )
    return {
        "translations": translator.translate(
            payload.get("texts", []),
            payload.get("target", ""),
            payload.get("source", "auto"),
        )
    }


def read_texts(filename):
    content = Path(filename).read_text(encoding="utf-8")
    if Path(filename).suffix.lower() == ".json":
        values = json.loads(content)
        if not isinstance(values, list):
            raise ValueError("JSON input must be an array of strings")
        return values
    return content.splitlines()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--target", required=True)
    parser.add_argument("--source", default="auto")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--cache")
    parser.add_argument("--output")
    args = parser.parse_args()

    cache = TranslationCache(args.cache) if args.cache else TranslationCache()
    try:
        result = run(
            {
                "texts": read_texts(args.input),
                "target": args.target,
                "source": args.source,
                "batch_size": args.batch_size,
            },
            cache=cache,
        )
    finally:
        cache.close()
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
