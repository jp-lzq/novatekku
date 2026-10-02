"""Sort user questions into a fixed set of intents.

The model labels questions in batches.  A label outside the allowed set or a
confidence below the threshold falls back to keyword rules, so every question
always gets a valid label and the result says which path decided it.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter

INTENTS = ("price", "bulk_total", "catalog", "selling", "buying", "migration", "troubleshooting", "phone_other", "off_topic")
MIN_CONFIDENCE = 0.6

# Checked in order; the first matching intent wins.
KEYWORDS = (
    ("bulk_total", r"[x×*]\s*\d+\s*台?|\d+\s*台|合计|合計|一共|总共|total|in total"),
    ("price", r"价格|价钱|报价|回收价|多少钱|均价|価格|買取|いくら|相場|price|quote|worth|buyback"),
    ("catalog", r"哪些型号|有什么型号|种类|ラインナップ|機種一覧|which models|lineup|what models"),
    ("selling", r"卖|出售|出手|売却|売る|手放|sell|selling|trade[ -]?in"),
    ("buying", r"买哪|选购|推荐.*(机|款)|二手|購入|買うなら|中古|which .* buy|should i buy|used phone"),
    ("migration", r"迁移|转移|换机|移行|機種変更|データ移行|transfer|migrat|move .* to"),
    ("troubleshooting", r"发热|发烫|掉电|耗电|充不进|卡顿|故障|发烧|発熱|熱い|バッテリー|充電|不具合|heat|hot|battery|drain|charg|slow|not working|crash"),
    ("phone_other", r"iphone|android|手机|手機|スマホ|esim|相机|カメラ|camera|wi-?fi|防水|water"),
)

SYSTEM_PROMPT = (
    "Classify each question for a smartphone buyback assistant. Allowed intents: " + ", ".join(INTENTS) + ". "
    "price = buyback price of a model; bulk_total = total for several devices; catalog = which models are available; "
    "selling / buying = advice on selling or choosing a phone; migration = moving data; troubleshooting = device problems; "
    "phone_other = other phone questions; off_topic = not about phones. "
    "Return JSON: {\"results\": [{\"index\": int, \"intent\": str, \"confidence\": 0-1}]}."
)


class RouterError(RuntimeError):
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
            raise RouterError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
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
                    raise RouterError("message content is not text")
                return content
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise RouterError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as error:
                if attempt == self.retries:
                    raise RouterError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise RouterError("request failed")


def rule_intent(question):
    text = unicodedata.normalize("NFKC", str(question or "")).lower()
    for intent, pattern in KEYWORDS:
        if re.search(pattern, text, re.I):
            return intent
    return "off_topic"


class IntentRouter:
    def __init__(self, client=None, batch_size=25, min_confidence=MIN_CONFIDENCE):
        self.client = client
        self.batch_size = batch_size
        self.min_confidence = min_confidence

    def _model_labels(self, questions):
        content = self.client.complete([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"questions": list(enumerate(questions))}, ensure_ascii=False)},
        ])
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise RouterError("model did not return JSON") from error
        labels = {}
        for item in (data.get("results") or []) if isinstance(data, dict) else []:
            if isinstance(item, dict) and isinstance(item.get("index"), int):
                labels[item["index"]] = item
        return labels

    def route(self, questions):
        output = []
        for start in range(0, len(questions), self.batch_size):
            batch = questions[start:start + self.batch_size]
            labels = self._model_labels(batch) if self.client is not None else {}
            for offset, question in enumerate(batch):
                item = labels.get(offset) or {}
                intent, confidence = item.get("intent"), item.get("confidence")
                valid = (
                    intent in INTENTS
                    and isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
                    and self.min_confidence <= confidence <= 1
                )
                if valid:
                    output.append({"question": question, "intent": intent, "confidence": round(confidence, 3), "source": "model"})
                else:
                    output.append({"question": question, "intent": rule_intent(question), "confidence": None, "source": "rules"})
        return output


def evaluate(routed, expected):
    """Accuracy and confusion counts against expected labels."""
    if len(routed) != len(expected):
        raise RouterError("routed and expected lengths differ")
    pairs = Counter((want, got["intent"]) for want, got in zip(expected, routed))
    correct = sum(count for (want, got), count in pairs.items() if want == got)
    return {
        "total": len(expected),
        "correct": correct,
        "accuracy": round(correct / len(expected), 4) if expected else 0.0,
        "confusion": {f"{want}->{got}": count for (want, got), count in sorted(pairs.items()) if want != got},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Classify questions into fixed intents")
    parser.add_argument("input", help="JSON Lines with {\"question\": ..., \"intent\": optional} ('-' for stdin)")
    parser.add_argument("--rules-only", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE)
    args = parser.parse_args(argv)
    stream = sys.stdin if args.input == "-" else open(args.input, encoding="utf-8")
    with stream:
        records = [json.loads(line) for line in stream if line.strip()]
    questions = [str(record.get("question") or "") for record in records]
    client = None if args.rules_only else ChatClient.from_env()
    routed = IntentRouter(client, min_confidence=args.min_confidence).route(questions)
    for item in routed:
        print(json.dumps(item, ensure_ascii=False))
    expected = [record.get("intent") for record in records]
    if all(label in INTENTS for label in expected) and expected:
        print(json.dumps({"evaluation": evaluate(routed, expected)}, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
