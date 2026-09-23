"""The message catalog: English stays English, and a reply can speak another language."""

import json

import pytest

from mathlint import i18n
from mathlint.i18n import Message, join, localize, msg, render, use_language
from mathlint.web_api import handle

FAKE = {
    "xx": {
        "messages": {
            "Add {n} to both sides": "Adaugă {n} în ambii membri",
            "the {thing}": "{thing}-ul",
            "numerator": "numărător",
            "Divide by {d}": None,
        },
        "latex": {"or": "sau"},
    }
}


@pytest.fixture
def fake_catalog(monkeypatch):
    monkeypatch.setattr(i18n, "_catalog", lambda lang: FAKE.get(lang, {}))


def test_a_message_is_its_english_text():
    message = msg("Add {n} to both sides", n=3)
    assert message == "Add 3 to both sides"
    assert isinstance(message, str)
    assert message.template == "Add {n} to both sides"
    assert message.startswith("Add")


def test_a_format_spec_still_works():
    assert msg("about {value:.2f}", value=1.23456) == "about 1.23"


def test_a_message_is_rendered_from_the_catalog(fake_catalog):
    assert localize(msg("Add {n} to both sides", n=3), "xx") == "Adaugă 3 în ambii membri"


def test_a_message_argument_is_translated_too(fake_catalog):
    message = msg("the {thing}", thing=msg("numerator"))
    assert message == "the numerator"
    assert localize(message, "xx") == "numărător-ul"


def test_an_untranslated_message_stays_english(fake_catalog):
    assert localize(msg("Divide by {d}", d=2), "xx") == "Divide by 2"
    assert localize(msg("Never seen"), "xx") == "Never seen"
    assert localize("plain text", "xx") == "plain text"


def test_adding_text_keeps_the_translatable_parts(fake_catalog):
    joined = msg("Add {n} to both sides", n=3) + "!"
    assert joined == "Add 3 to both sides!"
    assert isinstance(joined, Message)
    assert localize(joined, "xx") == "Adaugă 3 în ambii membri!"
    before = "1. " + msg("numerator")
    assert isinstance(before, Message)
    assert localize(before, "xx") == "1. numărător"


def test_join_keeps_the_translatable_parts(fake_catalog):
    joined = join(", ", [msg("numerator"), "x"])
    assert joined == "numerator, x"
    assert localize(joined, "xx") == "numărător, x"


def test_localize_walks_a_reply(fake_catalog):
    reply = {"steps": [{"text": msg("numerator"), "math": "x"}], "n": 3, "none": None}
    assert localize(reply, "xx") == {"steps": [{"text": "numărător", "math": "x"}], "n": 3,
                                      "none": None}


def test_words_inside_latex_are_translated(fake_catalog):
    latex = r"x = 2 \quad\text{or}\quad x = 3"
    assert localize(latex, "xx") == r"x = 2 \quad\text{sau}\quad x = 3"
    assert localize(latex, "en") == latex


def test_the_current_language_is_used_by_render(fake_catalog):
    message = msg("numerator")
    assert render(message) == "numerator"
    with use_language("xx"):
        assert render(message) == "numărător"
    assert render(message) == "numerator"


def test_english_is_the_default_and_unknown_languages_fall_back(fake_catalog):
    assert localize(msg("numerator"), "en") == "numerator"
    assert localize(msg("numerator"), "zz") == "numerator"


def test_the_page_can_ask_for_a_language(monkeypatch):
    template = "Subtract {term} from both sides"
    catalog = {"messages": {template: "Scade {term} din ambii membri"}, "latex": {}}
    monkeypatch.setattr(i18n, "_catalog", lambda lang: catalog if lang == "ro" else {})
    reply = json.loads(handle("solve", json.dumps({"text": "x + 1 = 3", "lang": "ro"})))
    assert reply["ok"]
    texts = [step["text"] for step in reply["result"]["steps"]]
    assert "Scade 1 din ambii membri" in texts


def test_the_shipped_catalogs_load():
    for lang in i18n.LANGUAGES[1:]:
        catalog = i18n._catalog(lang)
        assert set(catalog) == {"messages", "latex"}


def test_the_command_line_speaks_the_language(capsys):
    from mathlint.cli import main

    assert main(["solve", "x + 1 = 3", "--lang", "ro"]) == 0
    assert "Scădem 1 din ambii membri" in capsys.readouterr().out
    assert main(["solve", "x + 1 = 3"]) == 0
    assert "Subtract 1 from both sides" in capsys.readouterr().out
