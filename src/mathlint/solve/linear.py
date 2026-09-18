"""Linear equations: the balance method.

Whatever you do to one side, do to the other — expand, clear fractions, move the
unknown to the left and the numbers to the right, divide.
"""

from __future__ import annotations

import sympy as sp

from .core import Equation, Outcome, Work, show
from .dispatch import register


def _methods(equation: Equation, variable: sp.Symbol) -> list[str]:
    return ["balance"]


@register("linear", methods=_methods)
def solve_linear(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    lhs, rhs = equation.lhs, equation.rhs

    expanded = (sp.expand(lhs), sp.expand(rhs))
    if expanded != (lhs, rhs):
        lhs, rhs = expanded
        work.equation("Expand the brackets", Equation(lhs, rhs))

    denominator = _common_denominator(lhs, rhs, variable)
    if denominator != 1:
        lhs, rhs = sp.expand(lhs * denominator), sp.expand(rhs * denominator)
        work.equation(
            f"Multiply both sides by {denominator} to clear the fractions",
            Equation(lhs, rhs),
            operation=f"* {denominator}",
        )

    left_x, left_c = _split(lhs, variable)
    right_x, right_c = _split(rhs, variable)

    # keep the unknown's coefficient positive: x + 1 = 2x is easier read as 2x = x + 1
    more_on_right = right_x.is_number and left_x.is_number and right_x > left_x
    if right_x != 0 and (left_x == 0 or more_on_right):
        lhs, rhs = rhs, lhs
        left_x, left_c, right_x, right_c = right_x, right_c, left_x, left_c
        work.equation(
            f"Swap the sides, so the side with more {variable} is on the left",
            Equation(lhs, rhs),
        )

    if right_x != 0:
        term = right_x * variable
        lhs, rhs = sp.expand(lhs - term), sp.expand(rhs - term)
        work.equation(_move_text(term), Equation(lhs, rhs), operation=_operation(-term))
        left_x -= right_x

    if left_c != 0:
        lhs, rhs = sp.expand(lhs - left_c), sp.expand(rhs - left_c)
        work.equation(_move_text(left_c), Equation(lhs, rhs), operation=_operation(-left_c))

    coefficient = left_x
    value = sp.expand(right_c - left_c)

    if coefficient == 0:
        if value == 0:
            work.note(f"Both sides are equal for every {variable}")
            return Outcome.all()
        work.note(f"This says 0 = {show(value)}, which is never true")
        return Outcome.none()

    answer = sp.simplify(value / coefficient)
    if coefficient != 1:
        work.equation(
            f"Divide both sides by {show(coefficient)}",
            Equation(variable, answer),
            operation=f"/ {show(coefficient)}",
        )
    return Outcome.of([answer])


def _split(side: sp.Expr, variable: sp.Symbol) -> tuple[sp.Expr, sp.Expr]:
    """``a*x + b`` -> ``(a, b)``."""
    polynomial = sp.Poly(side, variable)
    return polynomial.coeff_monomial(variable), polynomial.coeff_monomial(1)


def _common_denominator(lhs: sp.Expr, rhs: sp.Expr, variable: sp.Symbol) -> int:
    denominators = []
    for side in (lhs, rhs):
        for coefficient in sp.Poly(side, variable).coeffs():
            if coefficient.is_Rational:
                denominators.append(int(coefficient.q))
    if not denominators:
        return 1
    return int(sp.ilcm(*denominators)) if len(denominators) > 1 else denominators[0]


def _move_text(term: sp.Expr) -> str:
    if term.could_extract_minus_sign():
        return f"Add {show(-term)} to both sides"
    return f"Subtract {show(term)} from both sides"


def _operation(change: sp.Expr) -> str:
    return f"+ {show(change)}" if not change.could_extract_minus_sign() else f"- {show(-change)}"
