"""A short note for answers whose numbers could not be confirmed.

The answer itself is never rewritten here; a note is added at the end so the
reader knows which figures to double-check.  Shown in the answer language.
"""

from __future__ import annotations

from .check import Report

NOTES = {
    "ja": {
        "unsupported": "※ 次の金額は NOVA の最新データで確認できませんでした：{items}",
        "wrong_store": "※ {store} の現在の価格は {expected} です（回答中の {text} とは異なります）",
    },
    "zh": {
        "unsupported": "※ 以下金额无法用 NOVA 的最新数据确认：{items}",
        "wrong_store": "※ {store} 的当前价格是 {expected}（与回答中的 {text} 不一致）",
    },
    "en": {
        "unsupported": "Note: these amounts could not be confirmed with NOVA's latest data: {items}",
        "wrong_store": "Note: {store} currently quotes {expected} (not {text} as stated above)",
    },
}


def notes_for(report: Report, language: str = "ja") -> list[str]:
    text = NOTES.get(language, NOTES["en"])
    notes: list[str] = []
    unsupported = [item.text for item in report.findings if item.kind == "unsupported_amount"]
    if unsupported:
        notes.append(text["unsupported"].format(items="、".join(unsupported) if language != "en" else ", ".join(unsupported)))
    for item in report.findings:
        if item.kind == "wrong_store_price":
            expected = " / ".join(f"¥{value:,}" for value in item.expected)
            notes.append(text["wrong_store"].format(store=item.store, expected=expected, text=item.text))
    return notes


def annotate(answer: str, report: Report, language: str = "ja") -> str:
    """The answer with the notes appended; unchanged when everything checked out."""
    notes = notes_for(report, language)
    if not notes:
        return answer
    return answer.rstrip() + "\n\n" + "\n".join(notes)
