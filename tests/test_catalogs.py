"""The translation catalogs: in step with the code, complete, and well-formed."""

import importlib.util
import re
import string
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("extract", ROOT / "scripts" / "extract_messages.py")
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)

KEYS, PROBLEMS = extract.templates()


def _fields(template: str) -> set[str]:
    template = re.sub(r"^[a-z][a-z-]*\|", "", template)  # drop a context
    return {field for _, field, _, _ in string.Formatter().parse(template) if field is not None}


def test_every_message_has_a_literal_template():
    assert PROBLEMS == []


@pytest.mark.parametrize("lang", extract.LANGUAGES)
def test_the_catalog_is_in_step_with_the_code(lang):
    catalog = extract.load(lang)
    assert list(catalog["messages"]) == KEYS, "run: python scripts/extract_messages.py"


@pytest.mark.parametrize("lang", extract.LANGUAGES)
def test_every_template_is_translated(lang):
    messages = extract.load(lang)["messages"]
    missing = [key for key, value in messages.items() if not value]
    assert missing == []


@pytest.mark.parametrize("lang", extract.LANGUAGES)
def test_a_translation_uses_the_same_placeholders(lang):
    for key, value in extract.load(lang)["messages"].items():
        if value:
            assert _fields(value) == _fields(key), key


@pytest.mark.parametrize("lang", extract.LANGUAGES)
def test_a_translation_keeps_the_spaces_around_it(lang):
    # " (about {decimal})" is added to a sentence: its leading space matters
    for key, value in extract.load(lang)["messages"].items():
        if value:
            english = re.sub(r"^[a-z][a-z-]*\|", "", key)
            assert (
                value[: len(value) - len(value.lstrip())]
                == english[: len(english) - len(english.lstrip())]
            ), key
            assert value[len(value.rstrip()) :] == english[len(english.rstrip()) :], key


@pytest.mark.parametrize("lang", extract.LANGUAGES)
def test_latex_words_are_translated(lang):
    words = extract.load(lang)["latex"]
    assert all(value for value in words.values())
