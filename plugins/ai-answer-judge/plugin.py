"""Score AI answers from the NOVA AI test catalog.

Rule checks run first and cannot be overridden by the model: the answer must
exist, use the question's language and avoid table layouts.  A model then
grades accuracy and flags invented facts, optionally against reference data.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

LANGUAGES = ("zh", "ja", "en")
PASS_ACCURACY = 3
MAX_ANSWER_CHARS = 4000

SYSTEM_PROMPT = (
    "You review answers written by a smartphone assistant. Grade the answer to the question. "
    "If REFERENCE data is given, treat it as the only source of truth for prices, stores and totals; "
    "any price, store or total that REFERENCE does not support is invented. "
    "Return JSON: {\"accuracy\": 0-5, \"helpfulness\": 0-5, \"invented\": true|false, \"reason\": short text}."
)


class JudgeError(RuntimeError):
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
            raise JudgeError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
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
                    raise JudgeError("message content is not text")
                return content
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise JudgeError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as error:
                if attempt == self.retries:
                    raise JudgeError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise JudgeError("request failed")


def detect_language(text):
    """Rough zh / ja / en guess.

    Store names are often katakana or kanji (モバイルミックス, 森森買取), so
    Japanese is recognised by hiragana, which store names rarely use.
    """
    hiragana = len(re.findall(r"[\u3040-\u309f]", text))
    cjk = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if latin > 2 * cjk:
        return "en"
    if hiragana >= 3:
        return "ja"
    if cjk >= 3:
        return "zh"
    return "en"


def load_cases(path):
    """Read the test catalog: {"cases": {"zh": [...], ...}} or a flat JSON list."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict) and isinstance(data.get("cases"), dict):
        cases = []
        for language, rows in data["cases"].items():
            for row in rows:
                cases.append({**row, "language": row.get("language") or language})
        return cases
    if isinstance(data, list):
        return data
    raise JudgeError("unsupported catalog format")


def rule_check(case):
    """Deterministic problems with one answer (empty list = passed)."""
    answer = str(case.get("answer") or "").strip()
    problems = []
    if not answer:
        return ["empty answer"]
    expected = case.get("language")
    if expected in LANGUAGES and detect_language(answer) != expected:
        problems.append(f"answer language is {detect_language(answer)}, expected {expected}")
    if len(answer) > MAX_ANSWER_CHARS:
        problems.append(f"answer longer than {MAX_ANSWER_CHARS} characters")
    if re.search(r"^\s*\|.*\|\s*$", answer, re.M) or re.search(r"^\s*[-:| ]{5,}\s*$", answer, re.M):
        problems.append("table layout in answer")
    for phrase in case.get("must_include") or []:
        if phrase not in answer:
            problems.append(f"missing required text: {phrase}")
    for phrase in case.get("must_not_include") or []:
        if phrase in answer:
            problems.append(f"contains forbidden text: {phrase}")
    return problems


def _score(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JudgeError(f"{name} is not a number")
    return max(0, min(5, int(round(value))))


class AnswerJudge:
    def __init__(self, client=None, reference=None):
        self.client = client
        self.reference = reference

    def grade(self, case):
        content = self.client.complete([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "QUESTION": case.get("question"),
                "ANSWER": case.get("answer"),
                "REFERENCE": self.reference,
            }, ensure_ascii=False)},
        ])
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise JudgeError("model did not return JSON") from error
        if not isinstance(data, dict) or not isinstance(data.get("invented"), bool):
            raise JudgeError("model response is missing fields")
        return {
            "accuracy": _score(data.get("accuracy"), "accuracy"),
            "helpfulness": _score(data.get("helpfulness"), "helpfulness"),
            "invented": data["invented"],
            "reason": str(data.get("reason") or "")[:500],
        }

    def judge(self, case):
        problems = rule_check(case)
        result = {
            "id": case.get("id"),
            "language": case.get("language"),
            "category": case.get("category"),
            "rule_problems": problems,
            "grade": None,
        }
        if self.client is not None and not problems:
            try:
                result["grade"] = self.grade(case)
            except JudgeError as error:
                result["grade_error"] = str(error)
        grade = result["grade"]
        result["passed"] = not problems and "grade_error" not in result and (
            grade is None or (grade["accuracy"] >= PASS_ACCURACY and not grade["invented"])
        )
        return result

    def run(self, cases):
        results = [self.judge(case) for case in cases]
        return {"summary": summarize(results), "results": results}


def summarize(results):
    total = len(results)
    passed = sum(result["passed"] for result in results)
    by_category = {}
    for result in results:
        bucket = by_category.setdefault(result.get("category") or "-", {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += int(result["passed"])
    graded = [result["grade"] for result in results if result["grade"]]
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "rule_failures": sum(bool(result["rule_problems"]) for result in results),
        "invented": sum(grade["invented"] for grade in graded),
        "average_accuracy": round(sum(grade["accuracy"] for grade in graded) / len(graded), 2) if graded else None,
        "by_category": by_category,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score AI answers from a test catalog")
    parser.add_argument("catalog", help="aiTestCases.json or a JSON list of {question, answer, language}")
    parser.add_argument("--reference", help="JSON file with the price data the answers should rely on")
    parser.add_argument("--rules-only", action="store_true", help="skip the model and run rule checks only")
    parser.add_argument("--language", choices=LANGUAGES, help="only judge one language")
    parser.add_argument("--min-pass-rate", type=float, default=0.0, help="exit 1 when the pass rate is lower")
    args = parser.parse_args(argv)

    cases = load_cases(args.catalog)
    if args.language:
        cases = [case for case in cases if case.get("language") == args.language]
    reference = None
    if args.reference:
        with open(args.reference, encoding="utf-8") as handle:
            reference = json.load(handle)
    client = None if args.rules_only else ChatClient.from_env()
    report = AnswerJudge(client, reference).run(cases)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if report["summary"]["pass_rate"] < args.min_pass_rate:
        sys.exit(1)


if __name__ == "__main__":
    main()
