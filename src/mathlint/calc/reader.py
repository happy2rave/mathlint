"""Read a calculation — numbers only — into a :mod:`tree`.

Anything with a letter that is not a function name, ``pi``, ``e`` or ``of`` is
algebra, not arithmetic; :class:`NotArithmetic` sends it to the expression
tools instead.
"""

from __future__ import annotations

import re

import sympy as sp

from ..errors import ParseError
from ..i18n import msg
from ..parse.latex import latex_to_plain
from ..parse.unicode_math import normalize_unicode
from .tree import Call, Frac, Neg, Num, Percent, Power, Product, Sum, fraction, integer, number

MAX_LENGTH = 500
MAX_DIGITS = 60

FUNCTIONS = {
    "sqrt": "sqrt",
    "cbrt": "root3",
    "abs": "abs",
    "ln": "ln",
    "log": "ln",
    "exp": "exp",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "cot": "cot",
    "sec": "sec",
    "csc": "csc",
    "arcsin": "asin",
    "arccos": "acos",
    "arctan": "atan",
    "asin": "asin",
    "acos": "acos",
    "atan": "atan",
    "sinh": "sinh",
    "cosh": "cosh",
    "tanh": "tanh",
}
CONSTANTS = {"pi": sp.pi, "e": sp.E}
_WORDS = sorted([*FUNCTIONS, *CONSTANTS, "of"], key=len, reverse=True)

_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|(root\d+|[A-Za-z]+)|(\S))")
_ROOT_POWER = re.compile(r"\(\(1\)/\((\d+)\)\)")


class NotArithmetic(Exception):
    """The text has letters in it: it is an expression, not a calculation."""


def prepare(text: str) -> str:
    """Plain text with ``:`` for division and ``%`` kept."""
    text = text.replace(r"\div", "÷").replace(r"\%", "%").replace(r"\colon", ":")
    text = re.sub(r"\\sqrt\[(\d+)\]", r"\\root\1", text)
    text = _protect_roots(text)
    if "\\" in text:
        text = latex_to_plain(text)
    text = text.replace("÷", ":").replace("°", "")
    text = normalize_unicode(text)
    return text.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")


def _protect_roots(text: str) -> str:
    # \sqrt[3]{8} reads better as a cube root than as 8^(1/3)
    return re.sub(r"\\root(\d+)", lambda match: f" root{match.group(1)} ", text)


def read_arithmetic(text: str):
    """The calculation tree for ``text``, or :class:`NotArithmetic`."""
    if "=" in text:
        raise NotArithmetic
    body = prepare(text).strip()
    if not body:
        raise ParseError(msg("there is nothing to calculate"))
    if len(body) > MAX_LENGTH:
        raise ParseError(msg("this is too long (limit {limit} characters)", limit=MAX_LENGTH))
    tokens = _tokens(body)
    reader = _Reader(tokens)
    tree = reader.sum()
    if reader.position < len(tokens):
        kind, value = tokens[reader.position]
        raise ParseError(msg("cannot read the {value!r} here", value=value))
    return tree


def _tokens(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for match in _TOKEN.finditer(text):
        number_text, name, other = match.groups()
        if number_text is not None:
            if len(number_text.replace(".", "")) > MAX_DIGITS:
                raise ParseError(msg("that number is too long to work with"))
            tokens.append(("num", number_text))
        elif name is not None:
            tokens.extend(("name", word) for word in _split_name(name))
        elif other is not None:
            if other == ",":
                raise ParseError(msg("write decimals with a point, like 2.5"))
            if other not in "+-*/:^()!%|":
                raise NotArithmetic
            tokens.append(("op", other))
    return tokens


def _split_name(name: str) -> list[str]:
    """``2pi`` and ``sqrt`` are words; any other letter makes this algebra."""
    if re.fullmatch(r"root\d+", name):
        return [name]
    words: list[str] = []
    index = 0
    while index < len(name):
        word = next((word for word in _WORDS if name.startswith(word, index)), None)
        if word is None:
            raise NotArithmetic
        words.append(word)
        index += len(word)
    return words


class _Reader:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.position = 0
        self.bars = 0  # how many | ... | are open

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise ParseError(msg("this calculation stops too early"))
        self.position += 1
        return token

    def expect(self, value: str) -> None:
        token = self.peek()
        if token != ("op", value):
            raise ParseError(f"expected {value!r}")
        self.position += 1

    def sum(self):
        terms = [self.product()]
        signs = [1]
        while self.peek() in (("op", "+"), ("op", "-")):
            _, sign = self.take()
            terms.append(self.product())
            signs.append(-1 if sign == "-" else 1)
        return terms[0] if len(terms) == 1 else Sum(terms, signs)

    def product(self):
        factors = [self.signed()]
        ops = ["*"]
        while True:
            token = self.peek()
            if token in (("op", "*"), ("name", "of")):
                self.take()
                factors.append(self.signed())
                ops.append("*")
            elif token == ("op", ":"):
                self.take()
                factors.append(self.signed())
                ops.append(":")
            elif token == ("op", "/"):
                self.take()
                factors[-1] = settle_fraction(Frac(factors[-1], self.signed()))
            elif self._starts_factor(token):
                factors.append(self.power())
                ops.append("")
            else:
                break
        return factors[0] if len(factors) == 1 else Product(factors, ops)

    def _starts_factor(self, token) -> bool:
        if token is None:
            return False
        kind, value = token
        if kind == "name":
            return value != "of"
        if token == ("op", "("):
            return True
        if token == ("op", "|"):
            return self.bars == 0
        previous = self.tokens[self.position - 1]
        return kind == "num" and previous in (("op", ")"), ("op", "!"), ("op", "%"))

    def signed(self):
        token = self.peek()
        if token in (("op", "-"), ("op", "+")):
            self.take()
            inner = self.signed()
            if token == ("op", "+"):
                return inner
            if isinstance(inner, Num):
                return negate(inner)
            return Neg(inner)
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == ("op", "^"):
            self.take()
            exponent = self.signed()
            return Power(base, exponent)
        return base

    def postfix(self):
        node = self.atom()
        while self.peek() in (("op", "!"), ("op", "%")):
            _, value = self.take()
            node = Call("factorial", node) if value == "!" else Percent(node)
        return node

    def atom(self):
        kind, value = self.take()
        if kind == "num":
            if "." in value:
                return number(sp.Rational(value), decimal=True)
            return integer(int(value))
        if kind == "name":
            if value in CONSTANTS:
                return Num(CONSTANTS[value], "exact")
            if value.startswith("root"):
                return Call(value, self._argument())
            if value in FUNCTIONS:
                return self._function(FUNCTIONS[value])
            raise ParseError(msg("cannot read {value!r} here", value=value))
        if value == "(":
            inner = self.sum()
            self.expect(")")
            return inner
        if value == "|":
            self.bars += 1
            inner = self.sum()
            self.expect("|")
            self.bars -= 1
            return Call("abs", inner)
        raise ParseError(msg("cannot read the {value!r} here", value=value))

    def _function(self, name: str):
        exponent = None
        if self.peek() == ("op", "^"):
            self.take()
            exponent = self.signed()
        call = Call(name, self._argument())
        return call if exponent is None else Power(call, exponent)

    def _argument(self):
        if self.peek() == ("op", "("):
            self.take()
            inner = self.sum()
            self.expect(")")
            return inner
        if self.peek() is None:
            raise ParseError(msg("a function needs something to work on"))
        return self.power()


def negate(node: Num) -> Num:
    if node.style == "frac":
        return fraction(-node.top, node.bottom, node.keep)
    return Num(-node.value, node.style)


def settle_fraction(node: Frac):
    """Two whole numbers over each other are simply a fraction."""
    top, bottom = node.top, node.bottom
    if isinstance(top, Num) and isinstance(bottom, Num) and {top.style, bottom.style} == {"int"}:
        if bottom.value == 0:
            raise ParseError(msg("this divides by zero, so it has no value"))
        return fraction(int(top.value), int(bottom.value))
    return node
