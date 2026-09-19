"""Taylor and Maclaurin series: derivatives at a point, turned into a polynomial.

The table of derivatives and their values at the point, each term
f^(k)(a)/k! (x - a)^k, and the polynomial. For the series every course
memorises (e^x, sin, cos, ln(1 + x), 1/(1 - x), arctan...) the general term is
given too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp
from sympy.core.parameters import distribute

from ..errors import ParseError, UnsupportedError
from ..parse.plain import latex_of, parse_expression, read_as
from .solution import Solution, SolutionStep

MAX_ORDER = 12
DEFAULT_ORDER = 5

_REQUEST = re.compile(
    r"^\s*(?P<kind>taylor|maclaurin|series)(?:\s+series)?(?:\s+(?:of|for))?\s+(?P<f>.+?)"
    r"(?:\s+(?:at|about|around)\s+(?:[a-z]\s*=\s*)?(?P<a>[^\s,]+))?"
    r"(?:\s*,?\s*(?:to\s+order|order|up\s+to|degree|n\s*=)\s*(?:[a-z]\s*\^\s*)?(?P<n>\d+))?\s*$",
    re.IGNORECASE,
)

_K = sp.Symbol("k", integer=True, nonnegative=True)


@dataclass
class SeriesProblem:
    function: sp.Expr
    x: sp.Symbol
    point: sp.Expr
    order: int


def looks_like_series(text: str) -> bool:
    return bool(_REQUEST.match(text))


def parse_series(text: str) -> SeriesProblem:
    match = _REQUEST.match(text)
    if match is None:
        raise ParseError("write it like: taylor sin(x) at 0 order 5")
    function = parse_expression(match.group("f")).expr
    letters = function.free_symbols
    if len(letters) != 1:
        raise ParseError("a series needs a function of one letter")
    (x,) = letters
    point = sp.Integer(0)
    if match.group("kind").lower() != "maclaurin" and match.group("a"):
        point = parse_expression(match.group("a")).expr
        if point.free_symbols:
            raise ParseError("the point of a Taylor series must be a number")
    order = int(match.group("n") or DEFAULT_ORDER)
    if order > MAX_ORDER:
        raise UnsupportedError(f"series are worked out up to order {MAX_ORDER}")
    return SeriesProblem(function, x, point, order)


def _known(function: sp.Expr, x: sp.Symbol) -> sp.Expr | None:
    """The general term of a series everyone learns, around 0."""
    k = _K
    table = {
        sp.exp(x): x**k / sp.factorial(k),
        sp.sin(x): (-1) ** k * x ** (2 * k + 1) / sp.factorial(2 * k + 1),
        sp.cos(x): (-1) ** k * x ** (2 * k) / sp.factorial(2 * k),
        sp.sinh(x): x ** (2 * k + 1) / sp.factorial(2 * k + 1),
        sp.cosh(x): x ** (2 * k) / sp.factorial(2 * k),
        1 / (1 - x): x**k,
        1 / (1 + x): (-1) ** k * x**k,
        sp.atan(x): (-1) ** k * x ** (2 * k + 1) / (2 * k + 1),
    }
    for known, term in table.items():
        if sp.simplify(function - known) == 0:
            return sp.Sum(term, (k, 0, sp.oo))
    if sp.simplify(function - sp.log(1 + x)) == 0:
        return sp.Sum((-1) ** (k + 1) * x**k / k, (k, 1, sp.oo))
    return None


def series_solution(problem: SeriesProblem) -> Solution:
    f, x, a, n = problem.function, problem.x, problem.point, problem.order
    name = "Maclaurin" if a == 0 else "Taylor"
    solution = Solution(
        operation="series",
        title=f"The {name} series of {read_as(f)} around {x} = {read_as(a)}, up to order {n}",
    )
    shift = x - a
    solution.steps.append(
        SolutionStep(
            text=f"A {name} series builds a polynomial from the derivatives at {x} = {read_as(a)}: "
            "the k-th term is f^(k)(a)/k! times (x - a)^k",
            display=f"f(x) = sum of f^(k)({read_as(a)})/k! * {_power(shift, 'k')}",
            display_latex=rf"f(x) = \sum_{{k=0}}^{{\infty}} \frac{{f^{{(k)}}({latex_of(a)})}}{{k!}}"
            rf"\left({latex_of(shift)}\right)^k",
        )
    )

    derivatives, values = [], []
    current = f
    for _ in range(n + 1):
        value = sp.simplify(current.subs(x, a))
        if not value.is_finite:
            raise UnsupportedError(
                f"f or one of its derivatives is not defined at {x} = {read_as(a)}, so there "
                "is no Taylor series there"
            )
        derivatives.append(sp.simplify(current))
        values.append(value)
        current = sp.diff(current, x)
    solution.steps.append(
        SolutionStep(
            text=f"The derivatives, and their values at {x} = {read_as(a)}",
            display=_table_plain(derivatives, values, x, a),
            display_latex=_table_latex(derivatives, values, x, a),
        )
    )

    terms = [values[k] / sp.factorial(k) * shift**k for k in range(n + 1)]
    polynomial = sp.Add(*terms)
    plain, latex = [], []
    for k in range(n + 1):
        if values[k] == 0:
            continue  # a zero derivative gives no term
        negative = values[k].could_extract_minus_sign()
        size = -values[k] if negative else values[k]
        sign = ("-" if negative else "") if not plain else (" - " if negative else " + ")
        power = "" if k == 0 else f"*{_power(shift, k)}"
        power_latex = "" if k == 0 else _power_latex(shift, k)
        plain.append(f"{sign}{read_as(size)}/{k}!{power}")
        latex.append(rf"{sign}\frac{{{latex_of(size)}}}{{{k}!}}{power_latex}")
    solution.steps.append(
        SolutionStep(
            text="Divide each value by k! and multiply by the matching power; a zero value "
            "gives no term",
            display="".join(plain) or "0",
            display_latex="".join(latex) or "0",
        )
    )
    remainder = sp.Order(shift ** (n + 1), (x, a))
    shown = _in_powers(values, shift, n)
    solution.steps.append(
        SolutionStep(
            text=f"So, up to order {n} (the rest is smaller than a multiple of "
            f"{_power(shift, n + 1)} near {x} = {read_as(a)})",
            display=f"{read_as(shown)} + O({_power(shift, n + 1)})",
            display_latex=rf"{latex_of(shown)} + {latex_of(remainder)}",
        )
    )
    if a == 0:
        general = _known(f, x)
        if general is not None:
            term, (k, low, _) = general.function, general.limits[0]
            solution.steps.append(
                SolutionStep(
                    text="This is a series worth knowing by heart; its general term gives all "
                    "of it",
                    display=f"sum over {k} = {low}, {low + 1}, {low + 2}, ... of {read_as(term)}",
                    display_latex=latex_of(general),
                )
            )
    solution.result = polynomial
    solution.summary = f"{read_as(shown)} + O({_power(shift, n + 1)})"
    return solution


def _in_powers(values, shift: sp.Expr, n: int) -> sp.Expr:
    """The polynomial in powers of (x - a), as it is written, not multiplied out."""
    with distribute(False):
        terms = [values[k] / sp.factorial(k) * shift**k for k in range(n + 1) if values[k] != 0]
    if not terms:
        return sp.Integer(0)
    return terms[0] if len(terms) == 1 else sp.Add(*terms, evaluate=False)


def _power(base: sp.Expr, exponent) -> str:
    text = read_as(base)
    if isinstance(base, sp.Add):
        text = f"({text})"
    return text if exponent == 1 else f"{text}^{exponent}"


def _power_latex(base: sp.Expr, exponent: int) -> str:
    text = latex_of(base)
    if isinstance(base, sp.Add):
        text = rf"\left({text}\right)"
    return text if exponent == 1 else f"{text}^{{{exponent}}}"


def _table_plain(derivatives, values, x, a) -> str:
    rows = [["k", "f^(k)(x)", f"f^(k)({read_as(a)})"]]
    rows += [
        [str(k), read_as(derivative), read_as(value)]
        for k, (derivative, value) in enumerate(zip(derivatives, values, strict=True))
    ]
    widths = [max(len(row[column]) for row in rows) for column in range(3)]
    lines = [
        " | ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
        for row in rows
    ]
    lines.insert(1, "-+-".join("-" * width for width in widths))
    return "\n".join(line.rstrip() for line in lines)


def _table_latex(derivatives, values, x, a) -> str:
    rows = [
        rf"{k} & {latex_of(derivative)} & {latex_of(value)}"
        for k, (derivative, value) in enumerate(zip(derivatives, values, strict=True))
    ]
    header = rf"k & f^{{(k)}}({latex_of(x)}) & f^{{(k)}}({latex_of(a)})"
    return r"\begin{array}{c|c|c} " + header + r" \\ \hline " + r" \\ ".join(rows) + r" \end{array}"
