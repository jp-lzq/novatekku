"""The understanding benchmark: case format, grading, and a floor the score must not drop below."""

import json

import pytest

from app.ai_gateway.eval import CASES_FILE, format_report, grade, load_cases, run
from app.ai_gateway.eval.__main__ import main

# raise these when the score improves; never lower them to make a change pass
MIN_ACCURACY = 0.94
MIN_FIELD_ACCURACY = {"capacities": 1.0, "colors": 1.0, "markets": 1.0, "quantities": 1.0, "models": 0.96, "intent": 0.95}


@pytest.fixture(scope="module")
def score():
    return run()


def test_case_file_is_valid_and_covers_three_languages():
    cases = load_cases()
    assert len(cases) >= 150
    assert {case["lang"] for case in cases} == {"ja", "zh", "en"}
    assert sum(1 for case in cases if case.get("history")) >= 15  # follow-ups are part of the set


def test_score_does_not_drop(score):
    assert score.accuracy >= MIN_ACCURACY, format_report(score)
    for name, minimum in MIN_FIELD_ACCURACY.items():
        correct, graded = score.by_field[name]
        assert correct / graded >= minimum, (name, format_report(score))


def test_only_known_gaps_fail(score):
    unexpected = [item.case_id for item in score.failures if not item.known_gap]
    assert unexpected == [], format_report(score)


def test_fixed_known_gaps_are_reported(score):
    # when a known gap starts passing, the report says so (then the mark should be removed from cases.jsonl)
    assert isinstance(score.known_gaps_fixed, list)


def test_grade_compares_only_the_written_fields():
    case = {"id": "t", "lang": "ja", "q": "17 pro 256 いくら", "expect": {"models": ["iPhone 17 Pro"]}}
    result = grade(case)
    assert result.passed and result.fields == {"models": True}
    wrong = grade({**case, "expect": {"capacities": ["512"]}})
    assert not wrong.passed and wrong.got["capacities"] == ["256"]


def test_history_is_used_for_follow_ups():
    case = {"id": "t", "lang": "ja", "q": "512 は？", "history": ["17 pro 256 いくら"],
            "expect": {"models": ["iPhone 17 Pro"], "capacities": ["512"]}}
    assert grade(case).passed


def test_bad_case_files_are_rejected(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text('{"id": "a", "q": "x", "expect": {"price": 1}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown expect fields"):
        load_cases(path)
    path.write_text('{"id": "a", "q": "x", "expect": {}}\n{"id": "a", "q": "y", "expect": {}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
    path.write_text('{"q": "x", "expect": {}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="required"):
        load_cases(path)


def test_report_and_command_line(score, capsys):
    text = format_report(score)
    assert text.startswith("understanding benchmark:") and "by field:" in text and "by language:" in text
    main(["--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == score.total and "intent" in data["by_field"]
    assert CASES_FILE.name == "cases.jsonl"
