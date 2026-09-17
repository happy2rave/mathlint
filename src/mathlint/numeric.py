"""Evaluating expressions at concrete values.

Numbers come first in mathlint: a counterexample is proof a student can check
by hand, while a failed symbolic simplification proves nothing at all.
"""

from __future__ import annotations

import math

import sympy as sp

PRECISION = 30

#: Values that make readable counterexamples, tried in this order.
NICE_VALUES: list[sp.Rational] = [
    sp.Integer(1),
    sp.Integer(2),
    sp.Integer(3),
    sp.Integer(-1),
    sp.Integer(-2),
    sp.Rational(1, 2),
    sp.Rational(-1, 2),
    sp.Integer(5),
    sp.Rational(3, 4),
    sp.Rational(-7, 3),
    sp.Integer(7),
    sp.Rational(-5, 2),
]


def sample_points(
    symbols: list[sp.Symbol], positive_only: bool = False
) -> list[dict[sp.Symbol, sp.Rational]]:
    """Build test points for the given symbols."""
    values = [value for value in NICE_VALUES if not positive_only or value > 0]
    if not symbols:
        return [{}]
    points = []
    for index in range(len(values)):
        point = {
            symbol: values[(index + 3 * offset) % len(values)]
            for offset, symbol in enumerate(symbols)
        }
        points.append(point)
    return points


def evaluate(expr: sp.Expr, point: dict[sp.Symbol, sp.Rational]) -> sp.Float | None:
    """Evaluate ``expr`` at ``point``, or return ``None`` if that is impossible.

    ``None`` means "no usable number here": the value is complex, infinite,
    undefined, or still symbolic (an indefinite integral, for instance).
    """
    if _has_indefinite_integral(expr):
        return None
    try:
        value = sp.N(expr.subs(point), PRECISION)
    except Exception:
        return None
    if not isinstance(value, sp.Expr) or value.free_symbols:
        return None
    if value.has(sp.zoo, sp.oo, -sp.oo, sp.nan) or not value.is_number:
        return None
    if value.is_real is not True:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(as_float):
        return None
    return value


def _has_indefinite_integral(expr: sp.Expr) -> bool:
    return any(
        len(node.limits) and len(node.limits[0]) == 1
        for node in expr.atoms(sp.Integral)
    )


def format_number(value: sp.Expr) -> str:
    """Print a value the way it should appear in a report."""
    if getattr(value, "is_Integer", False):
        return str(int(value))
    if getattr(value, "is_Rational", False):
        return str(value)
    return str(sp.N(value, 6))
