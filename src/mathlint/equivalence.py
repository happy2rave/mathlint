"""Decide whether one line really follows from the line before it.

The order matters. Numbers first: if two lines disagree at a value, that value
is shown to the student and the step is wrong, full stop. Only when the numbers
agree everywhere does mathlint try to prove the step symbolically, and if that
fails it says so ("OK, checked with numbers") instead of pretending.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import sympy as sp

from .hints import find_hints
from .numeric import evaluate, format_number, sample_points

TOLERANCE = sp.Float("1e-10")
_COMPLEXITY_LIMIT = 200


class Verdict(str, Enum):
    """What mathlint concluded about one step."""

    OK = "OK"
    WRONG = "WRONG"
    WARNING = "WARNING"
    UNSURE = "UNSURE"


@dataclass
class Comparison:
    """The result of comparing two lines."""

    verdict: Verdict
    message: str
    method: str | None = None
    counterexample: dict[str, str] | None = None
    values: tuple[str, str] | None = None
    hints: list[str] = field(default_factory=list)


def compare(
    left: sp.Expr, right: sp.Expr, up_to_constant_in: sp.Symbol | None = None
) -> Comparison:
    """Compare two expressions.

    ``up_to_constant_in`` is set when both sides are antiderivatives: then the
    sides are compared through their derivatives, so ``+ C`` is irrelevant.
    """
    if up_to_constant_in is not None:
        left_value = sp.diff(left, up_to_constant_in)
        right_value = sp.diff(right, up_to_constant_in)
        subject = "the two antiderivatives differ by more than a constant"
    else:
        left_value = _resolve(left)
        right_value = _resolve(right)
        subject = "not equal to the line above"

    difference = left_value - right_value
    if _proved_zero(difference):
        return Comparison(
            verdict=Verdict.OK,
            message="equal to the line above",
            method="exact",
        )

    symbols = sorted(difference.free_symbols, key=lambda symbol: symbol.name)
    if not symbols:
        return _compare_constants(left_value, right_value, difference, subject)
    return _compare_with_numbers(left_value, right_value, difference, symbols, subject)


def _compare_constants(
    left: sp.Expr, right: sp.Expr, difference: sp.Expr, subject: str
) -> Comparison:
    value = evaluate(difference, {})
    if value is None:
        return Comparison(
            verdict=Verdict.UNSURE,
            message="cannot tell whether these two are equal",
        )
    if abs(value) <= TOLERANCE * max(sp.Integer(1), abs(value)):
        return Comparison(
            verdict=Verdict.OK,
            message="equal to the line above",
            method="numeric",
        )
    values = _constant_values(left, right)
    return Comparison(
        verdict=Verdict.WRONG,
        message=subject,
        method="numeric",
        values=values,
        hints=find_hints(left, right),
    )


def _constant_values(left: sp.Expr, right: sp.Expr) -> tuple[str, str] | None:
    """Show exact values (``2``, ``1/3``) when we have them, decimals otherwise."""
    shown = []
    for side in (left, right):
        if side.is_Rational:
            shown.append(format_number(side))
            continue
        number = evaluate(side, {})
        if number is None:
            return None
        shown.append(format_number(number))
    return shown[0], shown[1]


def _compare_with_numbers(
    left: sp.Expr,
    right: sp.Expr,
    difference: sp.Expr,
    symbols: list[sp.Symbol],
    subject: str,
) -> Comparison:
    tested = 0
    disagreements: list[tuple[dict[sp.Symbol, sp.Rational], sp.Float, sp.Float]] = []
    for point in sample_points(symbols):
        left_number = evaluate(left, point)
        right_number = evaluate(right, point)
        if left_number is None or right_number is None:
            continue
        tested += 1
        scale = max(sp.Integer(1), abs(left_number), abs(right_number))
        if abs(left_number - right_number) > TOLERANCE * scale:
            disagreements.append((point, left_number, right_number))

    if tested == 0:
        return Comparison(
            verdict=Verdict.UNSURE,
            message="cannot tell — there are no real values to test this with",
        )

    if not disagreements:
        if _proved_zero(difference, try_hard=True):
            return Comparison(
                verdict=Verdict.OK, message="equal to the line above", method="exact"
            )
        return Comparison(
            verdict=Verdict.OK,
            message="equal to the line above",
            method="numeric",
        )

    positive_result = _positive_only(left, right, symbols)
    if positive_result is not None:
        point, _, _ = disagreements[0]
        return Comparison(
            verdict=Verdict.WARNING,
            message=(
                "only true for positive values — it fails at "
                f"{_render_point(point)}"
            ),
            method="numeric",
        )

    point, left_number, right_number = disagreements[0]
    return Comparison(
        verdict=Verdict.WRONG,
        message=subject,
        method="numeric",
        counterexample={symbol.name: format_number(value) for symbol, value in point.items()},
        values=(format_number(left_number), format_number(right_number)),
        hints=find_hints(left, right),
    )


def _positive_only(left: sp.Expr, right: sp.Expr, symbols: list[sp.Symbol]) -> bool | None:
    """Return ``True`` when the step holds wherever every variable is positive."""
    agreements = 0
    for point in sample_points(symbols, positive_only=True):
        left_number = evaluate(left, point)
        right_number = evaluate(right, point)
        if left_number is None or right_number is None:
            continue
        scale = max(sp.Integer(1), abs(left_number), abs(right_number))
        if abs(left_number - right_number) > TOLERANCE * scale:
            return None
        agreements += 1
    return True if agreements >= 2 else None


def _render_point(point: dict[sp.Symbol, sp.Rational]) -> str:
    return ", ".join(f"{symbol.name} = {format_number(value)}" for symbol, value in point.items())


def _resolve(expr: sp.Expr) -> sp.Expr:
    """Carry out derivatives and definite integrals that are still waiting."""
    try:
        return expr.doit(deep=True)
    except Exception:
        return expr


def _proved_zero(difference: sp.Expr, try_hard: bool = False) -> bool:
    if difference == 0:
        return True
    try:
        if sp.expand(difference) == 0:
            return True
    except Exception:
        return False
    if not try_hard or sp.count_ops(difference) > _COMPLEXITY_LIMIT:
        return False
    try:
        return sp.simplify(difference) == 0
    except Exception:
        return False
