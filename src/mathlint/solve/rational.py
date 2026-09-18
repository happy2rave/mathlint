"""Rational equations: the unknown is in a denominator.

First write down which values are excluded — a denominator can never be zero.
Then multiply both sides by the common denominator, which leaves a polynomial
equation, and solve that. A root that was excluded at the start is dropped at the
end, with the reason; it is the classic way to get these wrong.
"""

from __future__ import annotations

import sympy as sp

from ..parse.plain import latex_of
from . import dispatch
from .core import Equation, Outcome, Work, show, sort_values
from .dispatch import register


@register("rational", methods=lambda equation, variable: ["denominators"])
def solve_rational(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    denominators = _denominators(equation)
    excluded = _excluded(denominators, variable)
    if excluded:
        work.show(
            "A denominator can never be zero, so these values are excluded",
            ", ".join(f"{variable} != {show(value)}" for value in excluded),
            r",\quad ".join(rf"{latex_of(variable)} \neq {latex_of(value)}" for value in excluded),
        )

    common = sp.factor(sp.lcm_list(denominators))
    lhs = sp.expand(sp.cancel(equation.lhs * common))
    rhs = sp.expand(sp.cancel(equation.rhs * common))
    work.equation(
        f"Multiply both sides by the common denominator {show(common)}",
        Equation(lhs, rhs),
        operation=f"* {show(common)}",
    )

    found = dispatch.solve_equation(Equation(lhs, rhs), variable, work, depth=depth + 1)
    if found.everything:
        allowed = sp.Complement(sp.S.Reals, sp.FiniteSet(*excluded))
        work.note(f"Every {variable} works, except the excluded values")
        return Outcome.as_set(allowed) if excluded else Outcome.all()

    kept = []
    for value in found.values:
        if any(sp.simplify(value - bad) == 0 for bad in excluded):
            work.note(
                f"{variable} = {show(value)} was excluded at the start (it makes a "
                "denominator zero), so it is not a solution"
            )
        else:
            kept.append(value)
    return Outcome.of(kept)


def _denominators(equation: Equation) -> list[sp.Expr]:
    """Every denominator in the equation, numbers included (they join the LCD)."""
    found: list[sp.Expr] = []
    for side in (equation.lhs, equation.rhs):
        for term in sp.Add.make_args(side):
            _, denominator = sp.fraction(sp.together(term))
            if denominator != 1:
                found.append(sp.factor(denominator))
    return found or [sp.Integer(1)]


def _excluded(denominators: list[sp.Expr], variable: sp.Symbol) -> list[sp.Expr]:
    values: list[sp.Expr] = []
    for denominator in denominators:
        if not denominator.has(variable):
            continue
        zeros = sp.solveset(denominator, variable, domain=sp.S.Reals)
        if isinstance(zeros, sp.FiniteSet):
            values.extend(zeros)
    return sort_values(values)
