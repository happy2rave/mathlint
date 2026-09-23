"""Absolute-value equations: isolate, then split into two cases.

``|u| = k`` means ``u = k`` or ``u = -k``; ``|u| = |v|`` means ``u = v`` or
``u = -v``. When ``k`` itself contains the unknown, a case can produce an answer
that makes ``k`` negative; the check at the end drops it, with the reason.
"""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from . import dispatch
from .core import Equation, Outcome, Work, show
from .dispatch import register
from .isolate import already_isolated, isolate


@register("absolute", methods=lambda equation, variable: ["cases"])
def solve_absolute(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    pieces = [node for node in equation.expr.atoms(sp.Abs) if node.has(variable)]

    both = _abs_equals_abs(equation, variable)
    if both is not None:
        left, right = both
        return _cases(left, right, variable, work, depth, msg("|u| = |v| means u = v or u = -v"))

    if len(pieces) != 1:
        return dispatch.SOLVERS["other"](equation, variable, work, None, depth)

    piece = pieces[0]
    isolated = isolate(equation, piece)
    if isolated is None:
        return dispatch.SOLVERS["other"](equation, variable, work, None, depth)
    if not already_isolated(equation, piece):
        work.equation(msg("Isolate the absolute value on one side"), isolated)

    inside, value = piece.args[0], isolated.rhs
    if value.is_number and value.is_negative:
        work.note(
            msg(
                "An absolute value is never negative, but here it would "
                "equal {value}, so there is no solution",
                value=show(value),
            )
        )
        return Outcome.none()
    if value == 0:
        zero = Equation(inside, 0)
        work.equation(msg("An absolute value is zero only when what is inside is zero"), zero)
        return dispatch.solve_equation(zero, variable, work, depth=depth + 1)
    return _cases(inside, value, variable, work, depth, msg("|u| = k means u = k or u = -k"))


def _abs_equals_abs(equation: Equation, variable: sp.Symbol) -> tuple[sp.Expr, sp.Expr] | None:
    lhs, rhs = equation.lhs, equation.rhs
    both = isinstance(lhs, sp.Abs) and isinstance(rhs, sp.Abs)
    if both and lhs.has(variable) and rhs.has(variable):
        return lhs.args[0], rhs.args[0]
    return None


def _cases(
    inside: sp.Expr, value: sp.Expr, variable: sp.Symbol, work: Work, depth: int, rule: str
) -> Outcome:
    first, second = Equation(inside, value), Equation(inside, -value)
    work.alternatives(msg("Split into two cases: {rule}", rule=rule), [first, second])
    work.equation(msg("Case 1"), first)
    outcome = dispatch.solve_equation(first, variable, work, depth=depth + 1)
    work.equation(msg("Case 2"), second)
    return outcome.merge(dispatch.solve_equation(second, variable, work, depth=depth + 1))
