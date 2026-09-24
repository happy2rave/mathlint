"""Rewrite calculus notation into SymPy calls.

``d/dx x^2 sin x``  ->  ``Derivative((x^2 sin x), x)``
``int_0^1 x^2 dx``  ->  ``Integral((x^2), (x, 0, 1))``

The rewrite happens on the text, before parsing, because ``d/dx`` and ``dx``
mean nothing to an expression parser — it would read them as ``d`` divided by
``d*x``.
"""

from __future__ import annotations

import re

from ..errors import ParseError
from ..i18n import msg

_DERIVATIVE = re.compile(
    r"(?<![A-Za-z0-9_])d(?:\s*\^\s*(\d+))?\s*/\s*d\s*([A-Za-z][A-Za-z0-9_]*)(?:\s*\^\s*(\d+))?"
)
# the lookahead allows ``int_0^1``: a following ``_`` starts the limits
_INTEGRAL = re.compile(r"(?<![A-Za-z0-9_])int(?![A-Za-z0-9])")
_DIFFERENTIAL = re.compile(r"(?<![A-Za-z0-9_])d\s*([A-Za-z][A-Za-z0-9_]*)(?![A-Za-z0-9_(])")
_BRACKETED_OPERATOR = re.compile(
    r"\(\s*(d(?:\s*\^\s*\d+)?\s*/\s*d\s*[A-Za-z][A-Za-z0-9_]*(?:\s*\^\s*\d+)?)\s*\)"
)
_NUMBER_OR_NAME = re.compile(r"-?\s*(?:\d+(?:\.\d*)?|[A-Za-z_][A-Za-z0-9_]*)")


def rewrite_calculus(text: str) -> str:
    """Replace derivative and integral notation with SymPy constructors."""
    text = _BRACKETED_OPERATOR.sub(r"\1", text)
    return _rewrite(text)


def _rewrite(text: str) -> str:
    derivative = _DERIVATIVE.search(text)
    integral = _INTEGRAL.search(text)
    if derivative is None and integral is None:
        return text
    if integral is None or (derivative is not None and derivative.start() < integral.start()):
        assert derivative is not None
        return _rewrite_derivative(text, derivative)
    return _rewrite_integral(text, integral)


def _rewrite_derivative(text: str, match: re.Match[str]) -> str:
    order = int(match.group(1) or match.group(3) or 1)
    variable = match.group(2)
    start = _skip_spaces(text, match.end())
    if start < len(text) and text[start] == "(":
        operand, end = _balanced(text, start)
        rest = text[end:]
    else:
        operand, rest = text[start:], ""
    if not operand.strip():
        raise ParseError(msg("d/d{variable} needs something to differentiate", variable=variable))
    spec = variable if order == 1 else f"({variable}, {order})"
    return f"{text[: match.start()]}Derivative(({_rewrite(operand)}), {spec}){_rewrite(rest)}"


def _rewrite_integral(text: str, match: re.Match[str]) -> str:
    index = _skip_spaces(text, match.end())
    lower = upper = None
    if index < len(text) and text[index] == "_":
        lower, index = _read_bound(text, index + 1)
        index = _skip_spaces(text, index)
        if index < len(text) and text[index] == "^":
            upper, index = _read_bound(text, index + 1)
        else:
            raise ParseError(msg("this integral has a lower limit but no upper limit"))

    closing = _find_differential(text, index)
    if closing is None:
        raise ParseError(
            msg("this integral needs a dx at the end (which variable do you integrate?)")
        )
    integrand = text[index : closing.start()].strip().rstrip("*").strip()
    if not integrand:
        raise ParseError(msg("this integral has nothing to integrate"))
    variable = closing.group(1)
    rest = text[closing.end() :]

    spec = variable if lower is None else f"({variable}, {lower}, {upper})"
    return f"{text[: match.start()]}Integral(({_rewrite(integrand)}), {spec}){_rewrite(rest)}"


def _find_differential(text: str, index: int) -> re.Match[str] | None:
    """Find the ``dx`` that closes this integral, skipping nested integrals."""
    depth = 0
    while index < len(text):
        derivative = _DERIVATIVE.search(text, index)
        integral = _INTEGRAL.search(text, index)
        differential = _DIFFERENTIAL.search(text, index)
        candidates = [m for m in (derivative, integral, differential) if m is not None]
        if not candidates:
            return None
        first = min(candidates, key=lambda m: m.start())
        if first is derivative:
            index = first.end()
        elif first is integral:
            depth += 1
            index = first.end()
        else:
            if depth == 0:
                return first
            depth -= 1
            index = first.end()
    return None


def _read_bound(text: str, index: int) -> tuple[str, int]:
    index = _skip_spaces(text, index)
    if index < len(text) and text[index] == "(":
        inner, end = _balanced(text, index)
        return f"({inner})", end
    match = _NUMBER_OR_NAME.match(text, index)
    if match is None:
        raise ParseError(msg("cannot read the limits of this integral"))
    return match.group(0).replace(" ", ""), match.end()


def _balanced(text: str, index: int) -> tuple[str, int]:
    depth = 0
    for position in range(index, len(text)):
        if text[position] == "(":
            depth += 1
        elif text[position] == ")":
            depth -= 1
            if depth == 0:
                return text[index + 1 : position], position + 1
    raise ParseError(msg("unbalanced bracket"))


def _skip_spaces(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index
