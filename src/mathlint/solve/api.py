"""``mathlint.solve``: one equation in, the answer and the steps out."""

from __future__ import annotations

import re

import sympy as sp
from sympy.core.parameters import distribute

from ..document import _PLAIN_EQUALS
from ..errors import ParseError, UnsupportedError
from ..parse.latex import latex_to_plain
from ..parse.plain import parse_expression
from ..parse.unicode_math import normalize_unicode
from . import dispatch
from .classify import classify
from .core import Equation, Work, show
from .solution import EquationSolution
from .system import SystemSolution, solve_system, split_equations
from .verify import verify

_SOLVE_PREFIX = re.compile(r"^solve\s+", re.IGNORECASE)


def solve(text: str, method: str | None = None) -> EquationSolution | SystemSolution:
    """Solve an equation, or a system of equations, showing every step.

    One equation gives an :class:`EquationSolution`; several (one per line,
    separated by ``;``, or a LaTeX ``cases`` block) give a :class:`SystemSolution`.
    ``method`` picks one of the solution's ``methods`` (for a quadratic:
    ``"factoring"``, ``"formula"``, ...); by default the most natural one is used.
    """
    parts = split_equations(text)
    if len(parts) > 1:
        return solve_system([parse_equation(part) for part in parts], method)
    equation = parse_equation(text)
    variable = _unknown(equation)

    solution = EquationSolution(
        operation="solve",
        title=f"Solve {show(equation.lhs)} = {show(equation.rhs)}",
        variable=variable,
    )
    work = Work(solution, variable)
    work.equation("Start from", equation)

    if equation.lhs.has(sp.Float) or equation.rhs.has(sp.Float):
        equation = Equation(
            sp.nsimplify(equation.lhs, rational=True), sp.nsimplify(equation.rhs, rational=True)
        )
        work.equation("Write the decimals as fractions, so the answer stays exact", equation)

    solution.kind = classify(equation, variable)
    solution.methods = dispatch.methods_for(solution.kind, equation, variable)
    if method is not None and method not in solution.methods:
        options = ", ".join(solution.methods)
        raise UnsupportedError(f"the method '{method}' does not apply here — try {options}")
    solution.method = method or solution.methods[0]

    outcome = dispatch.solve_equation(equation, variable, work, method=solution.method)
    solution.finish(verify(equation, variable, outcome, work))
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


def _unknown(equation: Equation) -> sp.Symbol:
    unknowns = sorted(
        equation.lhs.free_symbols | equation.rhs.free_symbols, key=lambda symbol: symbol.name
    )
    if not unknowns:
        raise ParseError("there is nothing to solve for — this equation has no unknown")
    if len(unknowns) > 1:
        names = ", ".join(symbol.name for symbol in unknowns)
        raise UnsupportedError(
            f"this equation has more than one unknown ({names}); systems of equations "
            "and solving for one letter are coming in v0.6"
        )
    return unknowns[0]
