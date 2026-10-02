"""Find unusual store prices and explain them.

Detection is plain statistics and never depends on the model: inside each
model + capacity group, a price is flagged when its robust z-score (median and
median absolute deviation) is above the threshold.  The model only suggests a
likely cause for each flagged price, chosen from a fixed list.
"""

import argparse
import csv
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

THRESHOLD = 3.5
MIN_STORES = 4
FLAT_TOLERANCE = 0.05  # when most stores quote the same price
CAUSES = ("typo", "different_condition", "stale_price", "promotion", "carrier_model", "unknown")

SYSTEM_PROMPT = (
    "You review iPhone buyback prices that differ strongly from other stores. "
    "For each item choose the most likely cause from: " + ", ".join(CAUSES) + ". "
    "Return JSON: {\"explanations\": [{\"id\": <item id>, \"cause\": <cause>, \"note\": short text}]}. "
    "Do not invent prices."
)


class AnomalyError(RuntimeError):
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
            raise AnomalyError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
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
                    raise AnomalyError("message content is not text")
                return content
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise AnomalyError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as error:
                if attempt == self.retries:
                    raise AnomalyError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise AnomalyError("request failed")


def read_prices(stream):
    """CSV with columns model, capacity, store, price."""
    rows = []
    for number, row in enumerate(csv.DictReader(stream), start=2):
        try:
            price = int(str(row["price"]).replace(",", "").strip())
        except (KeyError, ValueError):
            raise AnomalyError(f"line {number}: price must be an integer")
        model, capacity, store = (str(row.get(key) or "").strip() for key in ("model", "capacity", "store"))
        if not model or not capacity or not store or price <= 0:
            raise AnomalyError(f"line {number}: model, capacity, store and a positive price are required")
        rows.append({"model": model, "capacity": capacity, "store": store, "price": price})
    return rows


def detect(rows, threshold=THRESHOLD, min_stores=MIN_STORES):
    groups = {}
    for row in rows:
        groups.setdefault((row["model"], row["capacity"]), []).append(row)
    anomalies = []
    for (model, capacity), items in sorted(groups.items()):
        if len(items) < min_stores:
            continue
        prices = [item["price"] for item in items]
        median = statistics.median(prices)
        mad = statistics.median(abs(price - median) for price in prices)
        for item in items:
            deviation = item["price"] - median
            if mad:
                score = 0.6745 * deviation / mad
                flagged = abs(score) > threshold
            else:
                score = None
                flagged = abs(deviation) > median * FLAT_TOLERANCE
            if flagged:
                anomalies.append({
                    "id": len(anomalies),
                    "model": model,
                    "capacity": capacity,
                    "store": item["store"],
                    "price": item["price"],
                    "median": round(median),
                    "difference": round(deviation),
                    "difference_percent": round(deviation / median * 100, 1),
                    "robust_z": round(score, 2) if score is not None else None,
                    "store_count": len(items),
                })
    return anomalies


class AnomalyExplainer:
    def __init__(self, client, batch_size=20):
        self.client = client
        self.batch_size = batch_size

    def explain(self, anomalies):
        explained = [{**item, "cause": None, "note": None} for item in anomalies]
        for start in range(0, len(explained), self.batch_size):
            batch = explained[start:start + self.batch_size]
            content = self.client.complete([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"items": batch}, ensure_ascii=False)},
            ])
            try:
                data = json.loads(content)
            except json.JSONDecodeError as error:
                raise AnomalyError("model did not return JSON") from error
            ids = {item["id"] for item in batch}
            for explanation in (data.get("explanations") or []) if isinstance(data, dict) else []:
                if not isinstance(explanation, dict) or explanation.get("id") not in ids:
                    continue
                target = explained[explanation["id"]]
                target["cause"] = explanation.get("cause") if explanation.get("cause") in CAUSES else "unknown"
                target["note"] = str(explanation.get("note") or "")[:300]
        return explained


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect and explain unusual buyback prices")
    parser.add_argument("csv", help="CSV with model, capacity, store, price ('-' for stdin)")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--min-stores", type=int, default=MIN_STORES)
    parser.add_argument("--rules-only", action="store_true", help="detect without asking the model")
    args = parser.parse_args(argv)
    stream = sys.stdin if args.csv == "-" else open(args.csv, encoding="utf-8", newline="")
    with stream:
        rows = read_prices(stream)
    anomalies = detect(rows, args.threshold, args.min_stores)
    if anomalies and not args.rules_only:
        anomalies = AnomalyExplainer(ChatClient.from_env()).explain(anomalies)
    json.dump({"rows": len(rows), "anomalies": anomalies}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
