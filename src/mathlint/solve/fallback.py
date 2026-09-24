"""Equations mathlint has no by-hand method for yet: SymPy solves them, labelled."""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from .core import Equation, Outcome, Work
from .dispatch import register


@register("other")
def solve_other(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    work.note(
        msg(
            "mathlint has no by-hand method for this kind of equation "
            "yet, so this answer comes straight from SymPy"
        )
    )
    try:
        result = sp.solveset(sp.Eq(equation.lhs, equation.rhs), variable, domain=sp.S.Reals)
    except Exception:
        work.note(msg("SymPy could not solve it either"))
        return Outcome.none()
    if result == sp.S.Reals:
        return Outcome.all()
    if result == sp.S.EmptySet:
        return Outcome.none()
    if isinstance(result, sp.FiniteSet):
        return Outcome.of(list(result))
    return Outcome.as_set(result)
