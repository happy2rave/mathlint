"""Put every answer back into the original equation.

Squaring both sides, clearing denominators and undoing logarithms can all create
answers that do not solve the equation you started with. This is the step that
catches them, and it shows its work either way.
"""

from __future__ import annotations

import sympy as sp

from ..equivalence import Verdict, compare
from ..i18n import msg
from .core import Equation, Outcome, Work, show, sort_values

_TOLERANCE = sp.Float("1e-12")
_APPROXIMATE_TOLERANCE = sp.Float("1e-8")


def verify(original: Equation, variable: sp.Symbol, outcome: Outcome, work: Work) -> Outcome:
    if outcome.everything or outcome.solution_set is not None:
        return outcome
    kept = []
    for value in sort_values(outcome.values):
        verdict = _check(original, variable, value)
        label = msg("Check {variable} = {value}", variable=variable, value=show(value))
        if verdict is None:
            left = _simplify(original.lhs.subs(variable, value))
            work.note(msg("{label}: both sides equal {left}", label=label, left=show(left)))
            kept.append(value)
        else:
            work.note(
                msg(
                    "{label}: {verdict}, so {variable} = {value} is not a solution",
                    label=label,
                    verdict=verdict,
                    variable=variable,
                    value=show(value),
                )
            )
    return Outcome.of(kept)


def _check(original: Equation, variable: sp.Symbol, value: sp.Expr) -> str | None:
    """None when ``value`` solves the equation, otherwise the reason it does not."""
    letters = original.lhs.free_symbols | original.rhs.free_symbols | value.free_symbols
    if letters - {variable}:
        return _check_formula(original, variable, value)
    if not _is_real(value):
        return msg("it is not a real number")
    for side in (original.lhs, original.rhs):
        _, denominator = sp.fraction(sp.together(side))
        if denominator.has(variable) and _simplify(denominator.subs(variable, value)) == 0:
            return msg("it makes a denominator zero")
    left = _simplify(original.lhs.subs(variable, value))
    right = _simplify(original.rhs.subs(variable, value))
    for side in (left, right):
        if side.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            return msg("it makes a denominator zero")
        if not _is_real(side):
            return msg("it takes the root or the logarithm of a negative number")
    if _simplify(left - right) == 0:
        return None
    difference = sp.N(left - right, 30)
    # an approximate root (a decimal) can only agree to about as many digits as it has
    tolerance = _APPROXIMATE_TOLERANCE if value.has(sp.Float) else _TOLERANCE
    scale = max(sp.Integer(1), abs(sp.N(left, 30)), abs(sp.N(right, 30)))
    if difference.is_number and abs(difference) < tolerance * scale:
        return None
    return msg(
        "the left side is {left} but the right side is {right}", left=show(left), right=show(right)
    )


def _check_formula(original: Equation, variable: sp.Symbol, value: sp.Expr) -> str | None:
    """With other letters in play, compare the two sides as expressions."""
    left = original.lhs.subs(variable, value)
    right = original.rhs.subs(variable, value)
    result = compare(left, right)
    if result.verdict is not Verdict.WRONG:
        return None
    point = result.counterexample or {}
    where = ", ".join(f"{name} = {number}" for name, number in point.items())
    return (
        msg("the two sides differ (for example at {where})", where=where)
        if where
        else msg("the two sides differ")
    )


def _is_real(value: sp.Expr) -> bool:
    if value.is_real is True:
        return True
    number = sp.N(value, 30)
    return number.is_number and abs(sp.im(number)) < _TOLERANCE


def _simplify(value: sp.Expr) -> sp.Expr:
    try:
        return sp.simplify(value)
    except Exception:
        return value
