"""Turn free-text iPhone buyback quotes into validated rows.

The model reads messy text ("17PM 256 新品×3 19.8万"); every value it returns is
then checked here: model and capacity must be real iPhone variants and the
price must literally appear in the source line, so invented numbers are dropped.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

CAPACITIES = ("64", "128", "256", "512", "1TB", "2TB")
CONDITIONS = ("new", "used", "unknown")
PRICE_RANGE = (1_000, 2_000_000)
QUANTITY_RANGE = (1, 999)
VARIANTS = {"": "", "pro": " Pro", "promax": " Pro Max", "plus": " Plus", "mini": " mini", "air": " Air", "e": "e"}

SYSTEM_PROMPT = (
    "You extract iPhone buyback quotes from short Japanese, Chinese or English text. "
    "Return JSON: {\"results\": [{\"index\": <line index>, \"items\": [{\"model\": str, \"capacity\": str, "
    "\"condition\": \"new\"|\"used\"|\"unknown\", \"quantity\": int, \"unit_price\": int}]}]}. "
    "unit_price is the price for one device in yen. Copy numbers from the text; never estimate. "
    "Lines without a quote get an empty items list."
)


class QuoteParserError(RuntimeError):
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
            raise QuoteParserError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
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
                    raise QuoteParserError("message content is not text")
                return content
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise QuoteParserError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as error:
                if attempt == self.retries:
                    raise QuoteParserError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise QuoteParserError("request failed")


def normalize_model(value):
    """'17PM', 'iPhone17 ProMax', 'iphone 16e' -> canonical name, or None."""
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("iphone", " ").replace("pro max", "promax")
    compact = re.sub(r"[\s_-]+", "", text)
    compact = re.sub(r"(?<=\d)pm$", "promax", compact)
    match = re.fullmatch(r"(1[1-9]|air)(promax|pro|plus|mini|air|e)?", compact)
    if not match:
        return None
    generation, variant = match.group(1), match.group(2) or ""
    if generation == "air":
        return "iPhone Air" if not variant else None
    return f"iPhone {generation}{VARIANTS[variant]}"


def normalize_capacity(value):
    text = unicodedata.normalize("NFKC", str(value or "")).upper().replace(" ", "")
    match = re.fullmatch(r"(\d+)(GB|G|TB|T)?", text)
    if not match:
        return None
    number, unit = int(match.group(1)), match.group(2) or ""
    if unit.startswith("T"):
        label = f"{number}TB"
    elif number in (1024, 2048):
        label = f"{number // 1024}TB"
    elif number in (1, 2) and not unit:
        label = f"{number}TB"
    else:
        label = str(number)
    return label if label in CAPACITIES else None


def prices_in_text(line):
    """All yen amounts written in a line, including 19.8万 / 19万8千 forms."""
    text = unicodedata.normalize("NFKC", line)
    found = set()
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*万(?:\s*(\d+)\s*千)?", text):
        amount = float(match.group(1)) * 10_000 + int(match.group(2) or 0) * 1_000
        found.add(int(round(amount)))
    for match in re.finditer(r"\d{1,3}(?:,\d{3})+|\d+", re.sub(r"\d+(?:\.\d+)?\s*万(?:\s*\d+\s*千)?", " ", text)):
        found.add(int(match.group(0).replace(",", "")))
    return found


def validate_item(item, line):
    """Return (clean_item, None) or (None, reason)."""
    if not isinstance(item, dict):
        return None, "item is not an object"
    model = normalize_model(item.get("model"))
    if not model:
        return None, f"unknown model: {item.get('model')!r}"
    capacity = normalize_capacity(item.get("capacity"))
    if not capacity:
        return None, f"unknown capacity: {item.get('capacity')!r}"
    price = item.get("unit_price")
    if isinstance(price, bool) or not isinstance(price, int) or not PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
        return None, f"price out of range: {price!r}"
    if price not in prices_in_text(line):
        return None, f"price {price} does not appear in the text"
    quantity = item.get("quantity", 1)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not QUANTITY_RANGE[0] <= quantity <= QUANTITY_RANGE[1]:
        return None, f"quantity out of range: {quantity!r}"
    condition = item.get("condition") if item.get("condition") in CONDITIONS else "unknown"
    return {
        "model": model,
        "capacity": capacity,
        "condition": condition,
        "quantity": quantity,
        "unit_price": price,
        "subtotal": price * quantity,
    }, None


class QuoteParser:
    def __init__(self, client, batch_size=20):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.client = client
        self.batch_size = batch_size

    def _request(self, lines):
        content = self.client.complete([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"lines": list(enumerate(lines))}, ensure_ascii=False)},
        ])
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise QuoteParserError("model did not return JSON") from error
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise QuoteParserError("model response has no results list")
        by_index = {}
        for result in results:
            if isinstance(result, dict) and isinstance(result.get("index"), int):
                by_index[result["index"]] = result.get("items") or []
        return by_index

    def parse(self, lines):
        output = []
        for start in range(0, len(lines), self.batch_size):
            batch = lines[start:start + self.batch_size]
            raw = self._request(batch)
            for offset, line in enumerate(batch):
                items, errors = [], []
                raw_items = raw.get(offset, [])
                if not isinstance(raw_items, list):
                    raw_items, errors = [], ["items is not a list"]
                for item in raw_items:
                    clean, reason = validate_item(item, line)
                    if clean:
                        items.append(clean)
                    else:
                        errors.append(reason)
                output.append({"line": start + offset + 1, "text": line, "items": items, "errors": errors})
        return output


def write_csv(results, stream):
    fields = ["line", "model", "capacity", "condition", "quantity", "unit_price", "subtotal"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for result in results:
        for item in result["items"]:
            writer.writerow({"line": result["line"], **item})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Parse free-text iPhone buyback quotes")
    parser.add_argument("input", help="text file, one quote per line ('-' for stdin)")
    parser.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    stream = sys.stdin if args.input == "-" else open(args.input, encoding="utf-8")
    with stream:
        lines = [line.strip() for line in stream if line.strip()]
    results = QuoteParser(ChatClient.from_env(), batch_size=args.batch_size).parse(lines)
    if args.format == "csv":
        write_csv(results, sys.stdout)
    else:
        for result in results:
            print(json.dumps(result, ensure_ascii=False))
    rejected = sum(len(result["errors"]) for result in results)
    if rejected:
        print(f"{rejected} extracted value(s) rejected; see errors in jsonl output", file=sys.stderr)


if __name__ == "__main__":
    main()
