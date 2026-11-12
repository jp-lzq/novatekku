"""Notes appended to answers whose numbers could not be confirmed."""

from app.ai_gateway.verify import annotate, notes_for
from app.ai_gateway.verify.check import Finding, Report

OK = Report(status="ok", checked=2, supported=2)
BAD = Report(status="warning", checked=2, supported=0, findings=[
    Finding("unsupported_amount", "181,000円", 181000, "JPY"),
    Finding("wrong_store_price", "175,500円", 175500, "JPY", store="森森買取", expected=[168000]),
])


def test_clean_answer_is_unchanged():
    assert annotate("最高は175,500円です。", OK) == "最高は175,500円です。"
    assert notes_for(OK) == []


def test_notes_in_each_language():
    ja = annotate("回答", BAD, "ja")
    assert "181,000円" in ja and "森森買取 の現在の価格は ¥168,000" in ja
    zh = notes_for(BAD, "zh")
    assert zh[0].startswith("※ 以下金额无法用") and "¥168,000" in zh[1]
    en = notes_for(BAD, "en")
    assert en[0].startswith("Note: these amounts") and "currently quotes ¥168,000" in en[1]


def test_unknown_language_uses_english():
    assert notes_for(BAD, "fr")[0].startswith("Note:")


def test_notes_follow_a_blank_line():
    assert annotate("回答\n\n", BAD, "ja").startswith("回答\n\n※")
