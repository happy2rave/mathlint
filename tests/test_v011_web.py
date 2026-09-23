"""The v0.11 web app: every word in four languages, and nothing left out.

The page names its words by key (``data-i18n`` in the HTML, ``t("...")`` in the
scripts); English is the source in ``web/locales/en.json``. Every key used must
exist in English, and every other language must have exactly the same keys, the
same ``{placeholders}`` and the same markup.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
LOCALES = WEB / "locales"
LANGUAGES = ("ro", "ru", "es")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPTS = {path.name: path.read_text(encoding="utf-8") for path in WEB.glob("*.js")}
ENGLISH = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))


def _load(lang: str) -> dict:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


def _used_keys() -> set[str]:
    keys = set(re.findall(r'data-i18n(?:-html|-aria-label|-title|-placeholder)?="([^"]+)"', HTML))
    for text in SCRIPTS.values():
        keys |= set(re.findall(r'\bt\("([a-zA-Z][\w.]*\w)"', text))
        for line in re.findall(r"dataset\.i18n = [^;]*;", text):
            keys |= set(re.findall(r'"([a-z]+\.[\w.]+)"', line))
        keys |= set(re.findall(r'"((?:keypad|engine|history)\.[\w.]+)"', text))
    for verdict in ("OK", "WRONG", "WARNING", "UNSURE"):
        keys.add(f"verdict.{verdict}")
    for part in ("rule", "example", "mistake"):
        keys.add(f"steps.{part}")
    for name in ("solve-examples.json", "examples.json"):
        for example in json.loads((WEB / name).read_text(encoding="utf-8")):
            keys.add(f"example.{example['name']}")
            if "group" in example:
                keys.add(f"example.{example['group']}")
    return keys


def _fields(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


def _tags(text: str) -> list[str]:
    return re.findall(r"</?(\w+)", text)


def test_every_key_the_page_uses_is_in_english():
    missing = sorted(key for key in _used_keys() if key not in ENGLISH)
    assert missing == []


def test_english_has_no_unused_keys():
    unused = sorted(set(ENGLISH) - _used_keys())
    assert unused == []


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_language_has_the_same_keys(lang):
    assert sorted(_load(lang)) == sorted(ENGLISH)


@pytest.mark.parametrize("lang", LANGUAGES)
def test_a_translation_keeps_placeholders_and_markup(lang):
    for key, value in _load(lang).items():
        assert value.strip(), key
        assert _fields(value) == _fields(ENGLISH[key]), key
        assert sorted(_tags(value)) == sorted(_tags(ENGLISH[key])), key


def test_the_language_is_chosen_before_the_first_paint():
    assert 'localStorage.getItem("mathlint:lang")' in HTML
    assert 'name="language"' in HTML
    for lang in ("en", *LANGUAGES):
        assert f'value="{lang}"' in HTML


def test_every_request_carries_the_language():
    assert "lang: language()" in SCRIPTS["engine.js"]


def test_the_page_tests_are_not_published():
    build = (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
    assert 'ignore_patterns("tests")' in build


def test_history_is_kept_on_the_device_and_only_for_what_the_reader_asked():
    assert 'id="history-sheet"' in HTML
    assert 'id="open-history"' in HTML
    app = SCRIPTS["app.js"]
    assert app.count("historyStore.add(") == 3  # solve, check and work out
    # runs made on the reader's behalf stay out of it
    assert "check({ record: false })" in app
    assert "solve({ record: false })" in app
    assert "showSteps({ record: false })" in app
    assert '"history.js"' in (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
