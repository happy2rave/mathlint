"""Everything mathlint says, in the language the reader asked for.

Solvers write English, but through :func:`msg`::

    msg("Subtract {term} from both sides", term=show(term))

The result is a :class:`Message`: a ``str`` that *is* the English sentence, so
the command line, the tests and the word matching in ``explain.py`` never know
the difference. It also remembers its template and arguments, so
:func:`localize` can render it again from ``locales/<lang>.json``, where each
English template maps to its translation. A template with no translation, and
any plain ``str``, stays English.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import re
from collections.abc import Iterable, Iterator
from contextvars import ContextVar
from functools import cache
from importlib import resources
from typing import Any

#: English first: it is the source every other language is translated from.
LANGUAGES = ("en", "ro", "ru", "es")

_LANGUAGE: ContextVar[str] = ContextVar("mathlint_language", default="en")
_LATEX_TEXT = re.compile(r"\\text\{([^{}]*)\}")


class Message(str):
    """An English sentence that knows how to say itself in other languages."""

    template: str
    args: dict[str, Any]
    parts: tuple[Any, ...]

    def __new__(cls, template: str, args: dict[str, Any], parts: tuple[Any, ...] = ()):
        english = "".join(map(str, parts)) if parts else template.format_map(args)
        message = super().__new__(cls, english)
        message.template = template
        message.args = args
        message.parts = parts
        return message

    def __getnewargs__(self) -> tuple:  # copy and pickle rebuild it from these
        return (self.template, self.args, self.parts)

    def __add__(self, other: object) -> Message:
        if not isinstance(other, str):
            return NotImplemented
        return _joined([self, other])

    def __radd__(self, other: object) -> Message:
        if not isinstance(other, str):
            return NotImplemented
        return _joined([other, self])

    def render(self, lang: str) -> str:
        if self.parts:
            return "".join(_render(part, lang) for part in self.parts)
        if lang == "en":
            return str.__str__(self)
        translation = _catalog(lang).get("messages", {}).get(self.template)
        if not translation:
            return str.__str__(self)
        args = {
            name: _render(value, lang) if isinstance(value, str) else value
            for name, value in self.args.items()
        }
        return translation.format_map(args)


def msg(template: str, **args: Any) -> Message:
    """A sentence to show a student; ``template`` is the key in every catalog."""
    return Message(template, args)


def join(separator: str, parts: Iterable[Any]) -> Message:
    """``separator.join(parts)``, keeping every part translatable."""
    items: list[Any] = []
    for index, part in enumerate(parts):
        if index:
            items.append(separator)
        items.append(part)
    return _joined(items)


def either(parts: Iterable[Any]) -> Message:
    """``a or b or c``."""
    return join(" " + msg("or") + " ", parts)


def both(parts: Iterable[Any]) -> Message:
    """``a and b and c``."""
    return join(" " + msg("and") + " ", parts)


def _joined(parts: list[Any]) -> Message:
    flat: list[Any] = []
    for part in parts:
        if isinstance(part, Message) and part.parts:
            flat.extend(part.parts)
        else:
            flat.append(part)
    return Message("", {}, tuple(flat))


def localize(value: Any, lang: str) -> Any:
    """``value`` with every message in it rendered in ``lang``.

    Walks dicts, lists and tuples; words inside ``\\text{...}`` in LaTeX are
    translated from the catalog's ``latex`` section.
    """
    if isinstance(value, Message):
        return value.render(lang)
    if isinstance(value, str):
        return _latex_words(value, lang)
    if isinstance(value, dict):
        return {key: localize(item, lang) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [localize(item, lang) for item in value]
    return value


def localized_copy(value: Any, lang: str) -> Any:
    """A copy of a result object (dataclasses all the way down) in ``lang``.

    The command line prints results with f-strings, which only see English; it
    prints a localized copy instead.
    """
    if isinstance(value, Message):
        return value.render(lang)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        copy = dataclasses.replace(value)
        for field in dataclasses.fields(value):
            setattr(copy, field.name, localized_copy(getattr(value, field.name), lang))
        return copy
    if isinstance(value, list):
        return [localized_copy(item, lang) for item in value]
    if isinstance(value, tuple):
        return tuple(localized_copy(item, lang) for item in value)
    return value


def render(value: Any) -> Any:
    """``value`` in the current language (see :func:`use_language`)."""
    return localize(value, _LANGUAGE.get())


@contextlib.contextmanager
def use_language(lang: str) -> Iterator[None]:
    token = _LANGUAGE.set(lang)
    try:
        yield
    finally:
        _LANGUAGE.reset(token)


def _render(value: Any, lang: str) -> str:
    if isinstance(value, Message):
        return value.render(lang)
    return str(value)


def _latex_words(text: str, lang: str) -> str:
    if lang == "en" or "\\text{" not in text:
        return text
    words = _catalog(lang).get("latex", {})

    def swap(match: re.Match) -> str:
        word = match[1].strip()
        translation = words.get(word)
        if not translation:
            return match[0]
        return "\\text{" + match[1].replace(word, translation) + "}"

    return _LATEX_TEXT.sub(swap, text)


@cache
def _catalog(lang: str) -> dict:
    if lang not in LANGUAGES[1:]:
        return {}
    source = resources.files("mathlint") / "locales" / f"{lang}.json"
    return json.loads(source.read_text(encoding="utf-8"))
