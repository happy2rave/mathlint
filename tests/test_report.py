import json

import mathlint

WRONG_CHAIN = "(x+1)^2\n= x^2 + 2x + 1\n= x^2 + 2x + 2"


def test_text_report_shows_the_first_error():
    text = mathlint.check(WRONG_CHAIN).to_text()
    assert "read as:" in text
    assert "WRONG" in text
    assert "First error: line 2 -> 3" in text


def test_text_report_says_when_nothing_is_wrong():
    text = mathlint.check("(x+1)^2\n= x^2 + 2x + 1").to_text()
    assert "No mistakes found" in text


def test_markdown_report_is_a_table():
    markdown = mathlint.check(WRONG_CHAIN).to_markdown()
    assert markdown.splitlines()[0].startswith("|")
    assert "---" in markdown


def test_dict_report_is_json_serialisable():
    data = mathlint.check(WRONG_CHAIN).to_dict()
    assert data["ok"] is False
    assert data["first_error"] == 3
    assert data["steps"][2]["verdict"] == "WRONG"
    json.dumps(data)


def test_colour_can_be_switched_on():
    coloured = mathlint.check(WRONG_CHAIN).to_text(color=True)
    assert "\033[" in coloured
