"""``mathlint.solve``: one equation in, the answer and the steps out."""

from __future__ import annotations

import re

import sympy as sp
from sympy.core.parameters import distribute

from ..calc.computation import Computation
from ..document import _PLAIN_EQUALS
from ..errors import ParseError, UnsupportedError
from ..parse.latex import latex_to_plain
from ..parse.plain import parse_expression
from ..parse.unicode_math import normalize_unicode
from ..steps.derivatives import looks_like_implicit, looks_like_tangent
from ..steps.limits import looks_like_limit
from . import dispatch
from .classify import classify
from .core import Equation, Work, show
from .inequality import InequalitySolution, looks_like_inequality, solve_inequality
from .solution import EquationSolution
from .system import SystemSolution, solve_system, split_equations
from .verify import verify

_SOLVE_PREFIX = re.compile(r"^solve\s+", re.IGNORECASE)
_FOR_SUFFIX = re.compile(r"\s+for\s+([A-Za-z][A-Za-z0-9_]*)\s*$", re.IGNORECASE)


def solve(
    text: str, method: str | None = None, variable: str | None = None
) -> EquationSolution | SystemSolution | InequalitySolution | Computation:
    """Solve an equation, or a system of equations, showing every step.

    One equation gives an :class:`EquationSolution`; several (one per line,
    separated by ``;``, or a LaTeX ``cases`` block) give a :class:`SystemSolution`.
    ``method`` picks one of the solution's ``methods`` (for a quadratic:
    ``"factoring"``, ``"formula"``, ...); by default the most natural one is used.

    With several letters in one equation, ``variable`` (or ``"... for t"`` at the
    end of the text) says which one to solve for; the others are treated as known.
    ``x`` is chosen when it is there and nothing else is asked for.

    An inequality (``<``, ``<=``, ``>``, ``>=``) gives an :class:`InequalitySolution`.
    Other text without an ``=`` has nothing to solve; it is worked out by
    :func:`mathlint.compute` instead, so one input takes everything.
    """
    if looks_like_limit(text) or looks_like_tangent(text) or looks_like_implicit(text):
        # an arrow is not an inequality, and a tangent or dy/dx is worked out, not solved
        from ..calc import compute

        return compute(text, method)
    if looks_like_inequality(text):
        return solve_inequality(text, method=method, variable=variable)
    if "=" not in text:
        from ..calc import compute

        return compute(text, method)
    suffix = _FOR_SUFFIX.search(text)
    if suffix:
        variable = variable or suffix.group(1)
        text = text[: suffix.start()]
    parts = split_equations(text)
    if len(parts) > 1:
        return solve_system([parse_equation(part) for part in parts], method)
    equation = parse_equation(text)
    letters = sorted(
        equation.lhs.free_symbols | equation.rhs.free_symbols, key=lambda symbol: symbol.name
    )
    unknown = _unknown(letters, variable, text)

    title = f"Solve {show(equation.lhs)} = {show(equation.rhs)}"
    if len(letters) > 1:
        title += f" for {unknown}"
    solution = EquationSolution(
        operation="solve",
        title=title,
        variable=unknown,
        letters=[letter.name for letter in letters],
    )
    work = Work(solution, unknown)
    work.equation("Start from", equation)

    if equation.lhs.has(sp.Float) or equation.rhs.has(sp.Float):
        equation = Equation(
            sp.nsimplify(equation.lhs, rational=True), sp.nsimplify(equation.rhs, rational=True)
        )
        work.equation("Write the decimals as fractions, so the answer stays exact", equation)

    solution.kind = classify(equation, unknown)
    solution.methods = dispatch.methods_for(solution.kind, equation, unknown)
    if method is not None and method not in solution.methods:
        options = ", ".join(solution.methods)
        raise UnsupportedError(f"the method '{method}' does not apply here — try {options}")
    solution.method = method or solution.methods[0]

    outcome = dispatch.solve_equation(equation, unknown, work, method=solution.method)
    solution.finish(verify(equation, unknown, outcome, work))
    return solution


def parse_equation(text: str) -> Equation:
    body = _SOLVE_PREFIX.sub("", normalize_unicode(text).strip())
    if "\\" in body:
        body = latex_to_plain(body).strip()
    sides = _PLAIN_EQUALS.split(body)
    if len(sides) == 1:
        raise ParseError("an equation needs an '=' sign — for example 2x + 3 = 7")
    if len(sides) > 2:
        raise ParseError("write one equation at a time (this line has more than one '=')")
    # keep 3(x - 1) as written, so "Expand the brackets" is a step the student sees
    with distribute(False):
        left, right = (parse_expression(side).expr for side in sides)
    return Equation(left, right)


def _unknown(letters: list[sp.Symbol], variable: str | None, text: str) -> sp.Symbol:
    if not letters:
        raise ParseError("there is nothing to solve for — this equation has no unknown")
    if variable:
        chosen = next((letter for letter in letters if letter.name == variable), None)
        if chosen is None:
            raise ParseError(f"{variable} does not appear in this equation")
        return chosen
    if len(letters) == 1:
        return letters[0]
    x = next((letter for letter in letters if letter.name == "x"), None)
    if x is not None:
        return x
    names = ", ".join(letter.name for letter in letters)
    raise UnsupportedError(
        f"this equation has several letters ({names}) — say which one to solve for by "
        f"adding 'for {letters[-1].name}' at the end"
    )
