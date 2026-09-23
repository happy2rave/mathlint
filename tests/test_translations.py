"""Nothing a student reads is left in English when they asked for another language.

Every problem the page can be given — the problem banks, the examples, the
open-textbook library, and a few of each kind besides — is answered, and every
field made of words must be a translatable message whose template the catalogs
translate. Words inside LaTeX (``\\text{or}``) must be in each catalog's
``latex`` section.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

from mathlint import i18n
from mathlint.errors import MathlintError, error_text
from mathlint.i18n import Message
from mathlint.web_api import _HANDLERS

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


calc_bank = _load("calc_bank", ROOT / "tests" / "calc" / "bank.py")
solve_bank = _load("solve_bank", ROOT / "tests" / "solve" / "bank.py")

#: fields that hold math, names or ids rather than words
MATH_FIELDS = {
    "answers",
    "answer",
    "decimal",
    "expr",
    "id",
    "interval_text",
    "kind",
    "letters",
    "math",
    "method",
    "mode",
    "operation",
    "raw",
    "read_as",
    "result",
    "variable",
    "variables",
    "verdict",
    "x",
    "y",
    "from_label",
    "to_label",
    "conditions",
    "expression",
    "value",
    "values",
    "point",
    "text_input",
    "input",
    "operation_label",
    "counterexample",
}
#: words that are math, not English
MATH_WORDS = {
    "sin",
    "cos",
    "tan",
    "cot",
    "sec",
    "csc",
    "log",
    "exp",
    "sqrt",
    "cbrt",
    "abs",
    "lim",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "arcsin",
    "arccos",
    "arctan",
    "oo",
    "inf",
    "rref",
    "det",
    "pi",
    "ln",
    "dx",
    "dy",
    "dt",
    "theta",
}
WORD = re.compile(r"[A-Za-z]{3,}")
LATEX_TEXT = re.compile(r"\\text\{([^{}]*)\}")

EXTRA_SOLVE = [
    "2x + 1 > 3",
    "-2x + 4 <= 10",
    "1 < 2x + 1 < 5",
    "x^2 - x - 6 >= 0",
    "(x - 1)/(x + 2) < 0",
    "|x - 1| < 3",
    "|2x + 1| >= 5",
    "x^2 + 1 > 0",
    "x^2 + 1 < 0",
    "x + y = 3\nx - y = 1",
    "x + y + z = 6\nx - y = -1\n2x + z = 5",
    "x + y = 2\n2x + 2y = 4",
    "x + y = 2\nx + y = 3",
    "x^2 + y^2 = 25\nx + y = 7",
    "y = x^2\ny = x + 2",
    "A = pi r^2",
    "v = u + a t",
    "x^2 - 9",
    "2x^2 + 5x + 3",
    "x^3 - 8",
    "x^2 + 6x + 9",
    "(x + 3)(x - 3)",
    "(2x - 1)^3",
    "(x^2 - 4)/(x^2 - x - 2)",
    "log(8)/log(2)",
    "sin(x)^2 + cos(x)^2",
    "sqrt(50)",
    "2^10",
    "5!",
    "25%",
    "0.25 + 1/4",
    "e^(ln 3)",
    "3/(x - 1) + 2/(x + 1)",
    "d/dx x^2 sin x",
    "d/dx e^(3x) cos x",
    "d/dx ln(x^2 + 1)",
    "d/dx x/(x + 1)",
    "d^2/dx^2 x^3 sin x",
    "dy/dx: x^2 + y^2 = 25",
    "tangent to y = x^2 at x = 1",
    "int x e^x dx",
    "int x^2 dx",
    "int_0^1 x^2 dx",
    "int 1/(x^2 - 1) dx",
    "int (x + 1)/(x^2 + 3x + 2) dx",
    "int sqrt(4 - x^2) dx",
    "int 1/sqrt(x^2 + 9) dx",
    "int sin(x) cos(x) dx",
    "int x ln x dx",
    "lim x->2 (x^2 - 4)/(x - 2)",
    "lim x->0 sin(x)/x",
    "lim x->oo (2x^2 + 1)/(x^2 - 3)",
    "lim x->0+ 1/x",
    "lim x->0 1/x",
    "lim x->0 (sqrt(x + 4) - 2)/x",
    "lim x->3 x^2",
    "y' = 2y",
    "dy/dx + 2y = e^x",
    "y'' + 3y' + 2y = 0",
    "y'' + 4y = 0; y(0) = 1, y'(0) = 0",
    "y'' - 2y' + y = 0",
    "y'' + y = x",
    "taylor ln(x) at 1 order 4",
    "maclaurin e^x",
    "maclaurin sin x order 5",
    "e^(2x) = 8",
    "2^x = 16",
    "log(x) + log(x - 3) = 1",
    "sqrt(x + 3) = x - 3",
    "|2x - 1| = 5",
    "x^4 - 5x^2 + 4 = 0",
]
EXTRA_STEPS = [
    ("rref", "[[1,2],[3,4]]"),
    ("rref", "[[1,2,3],[2,4,6]]"),
    ("det", "[[1,2],[3,4]]"),
    ("det", "[[1,2,3],[0,1,4],[5,6,0]]"),
    ("inverse", "[[1,2],[3,4]]"),
    ("inverse", "[[1,2],[2,4]]"),
    ("eigen", "[[2,0],[0,3]]"),
    ("eigen", "[[4,1],[2,3]]"),
    ("diff", "x^2 sin x"),
    ("integrate", "x e^x"),
]
BAD_INPUT = ["x^2 +", "x + = 3", "lim x (x)", "(x + 1", "x = = 2", ""]


def _solve_inputs() -> list[str]:
    inputs = [entry[0] for entry in solve_bank.BANK]
    for name in dir(calc_bank):
        value = getattr(calc_bank, name)
        if name.isupper() and isinstance(value, list):
            inputs += [entry[0] for entry in value if isinstance(entry, tuple)]
    examples = json.loads((WEB / "solve-examples.json").read_text(encoding="utf-8"))
    inputs += ["\n".join(example["lines"]) for example in examples]
    textbook = json.loads((WEB / "textbook-problems.json").read_text(encoding="utf-8"))
    inputs += [problem["text"] for problem in textbook]
    return list(dict.fromkeys(inputs + EXTRA_SOLVE))


def _replies():
    """Every reply the corpus produces, before it is localized."""
    for text in _solve_inputs():
        reply = _try("solve", {"text": text})
        yield text, reply
        if isinstance(reply, dict) and reply.get("needs_letter"):
            for letter in reply["letters"]:
                yield text, _try("solve", {"text": text, "variable": letter})
        methods = reply.get("methods", []) if isinstance(reply, dict) else []
        for method in methods[1:]:
            yield text, _try("solve", {"text": text, "method": method["id"]})
    checks = json.loads((WEB / "examples.json").read_text(encoding="utf-8"))
    for example in checks:
        text = "\n".join(example["lines"])
        yield text, _try("check", {"text": text})
    for text in ["2x + 3 = 7\n2x = 4\nx = 3", "x^2 = 4\nx = 2", "(x+1)^2\n= x^2 + 1"]:
        yield text, _try("check", {"text": text})
    for operation, target in EXTRA_STEPS:
        yield target, _try("steps", {"operation": operation, "target": target})
    for text in BAD_INPUT:
        yield text, _try("solve", {"text": text})
    yield (
        "tutor",
        _try("tutor", {"previous": "2x + 3 = 7", "attempt": "2x = 5", "expected": "2x = 4"}),
    )


def _try(kind, data):
    try:
        return _HANDLERS[kind](data)
    except MathlintError as error:
        return {"error": error_text(error)}


def _english(value, field) -> list[str]:
    """The English left in a value that should be translatable."""
    if isinstance(value, Message):
        if value.parts:
            return [bad for part in value.parts for bad in _english(part, field)]
        found = [] if i18n._catalog("ro")["messages"].get(value.key) else [value.key]
        for arg in value.args.values():
            if isinstance(arg, str):
                found += _english(arg, field)
        return found
    if isinstance(value, str):
        words = [word for word in WORD.findall(value) if word.lower() not in MATH_WORDS]
        return [value] if words else []
    return []


def _walk(value, field, found, latex_words):
    if isinstance(value, dict):
        for key, item in value.items():
            _walk(item, key, found, latex_words)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, field, found, latex_words)
    elif isinstance(value, str):
        if field.endswith("latex") or field == "latex":
            latex_words.update(word.strip() for word in LATEX_TEXT.findall(value))
        elif field not in MATH_FIELDS:
            found.extend((field, text) for text in _english(value, field))


@pytest.fixture(scope="module")
def corpus():
    found, latex_words = [], set()
    for _, reply in _replies():
        _walk(reply, "", found, latex_words)
    return found, latex_words


@pytest.mark.xfail(reason="calc, steps and check are wrapped in the next commits")
def test_every_word_a_student_reads_is_translatable(corpus):
    found, _ = corpus
    english = sorted({f"{field}: {text}" for field, text in found})
    assert english == [], "\n".join(english[:80])


@pytest.mark.parametrize("lang", i18n.LANGUAGES[1:])
def test_every_word_inside_latex_is_translated(corpus, lang):
    _, latex_words = corpus
    words = i18n._catalog(lang)["latex"]
    assert sorted(word for word in latex_words if word and word not in words) == []
