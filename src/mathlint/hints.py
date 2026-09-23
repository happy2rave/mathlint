"""Guess what went wrong in a step, once we know it is wrong.

Every hint is a guess about the *kind* of slip, never about the verdict. The
verdict is decided by :mod:`mathlint.equivalence` with a counterexample.
"""

from __future__ import annotations

import sympy as sp

from .i18n import msg
from .parse.plain import read_as

MAX_HINTS = 3
_COMPLEXITY_LIMIT = 200


def find_hints(left: sp.Expr, right: sp.Expr) -> list[str]:
    """Describe how ``right`` differs from ``left`` in plain words."""
    hints: list[str] = []
    if _is_small(left) and _is_small(right):
        if _looks_zero(left + right):
            hints.append(msg("the sign of the whole expression flipped"))
        else:
            difference = sp.expand(left - right)
            if difference.is_number and difference != 0:
                hints.append(msg("off by a constant: {difference}", difference=read_as(difference)))
            ratio = _ratio(left, right)
            if ratio is not None:
                hints.append(msg("off by a factor of {ratio}", ratio=read_as(ratio)))
    hints.extend(_term_hints(left, right))
    return hints[:MAX_HINTS]


def _term_hints(left: sp.Expr, right: sp.Expr) -> list[str]:
    left_terms = set(sp.Add.make_args(sp.expand(left)))
    right_terms = set(sp.Add.make_args(sp.expand(right)))
    common = left_terms & right_terms
    missing = left_terms - right_terms
    extra = right_terms - left_terms
    # Only talk about terms when the two sides are mostly the same expression.
    if not common or len(missing) > 2 or len(extra) > 2:
        return []

    hints: list[str] = []
    unmatched_extra = set(extra)
    for term in sorted(missing, key=sp.default_sort_key):
        if -term in unmatched_extra:
            unmatched_extra.discard(-term)
            hints.append(msg("the sign of {term} flipped", term=read_as(term)))
        else:
            hints.append(msg("the term {term} disappeared", term=read_as(term)))
    for term in sorted(unmatched_extra, key=sp.default_sort_key):
        hints.append(msg("the term {term} appeared out of nowhere", term=read_as(term)))
    return hints


def _ratio(left: sp.Expr, right: sp.Expr) -> sp.Expr | None:
    if right == 0 or not _is_small(left) or not _is_small(right):
        return None
    try:
        ratio = sp.simplify(left / right)
    except Exception:
        return None
    if ratio.is_number and ratio != 1 and ratio.is_finite:
        return ratio
    return None


def _looks_zero(expr: sp.Expr) -> bool:
    try:
        return sp.simplify(expr) == 0
    except Exception:
        return False


def _is_small(expr: sp.Expr) -> bool:
    return sp.count_ops(expr) <= _COMPLEXITY_LIMIT
