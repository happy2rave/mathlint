"""Decide what kind of equation this is, so the right method can solve it.

The order of the checks matters: an equation with a square root of a fraction is
a radical equation first, because squaring is what gets rid of the root.
"""

from __future__ import annotations

import sympy as sp

from .core import Equation

KINDS = (
    "linear",
    "quadratic",
    "polynomial",
    "rational",
    "radical",
    "absolute",
    "exponential",
    "logarithmic",
    "other",
)

_TRIG = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.atan)


def classify(equation: Equation, variable: sp.Symbol) -> str:
    expr = equation.expr
    if any(node.has(variable) for node in expr.atoms(sp.Abs)):
        return "absolute"
    if has_radical(expr, variable):
        return "radical"
    if any(node.has(variable) for node in expr.atoms(sp.log)):
        return "logarithmic"
    if has_exponential(expr, variable):
        return "exponential"
    if any(node.has(variable) for node in expr.atoms(*_TRIG)):
        return "other"

    # term by term: combining both sides first could cancel the denominator away,
    # and x/(x-2) = 2/(x-2) would lose the fact that x = 2 is excluded
    if any(
        sp.fraction(sp.together(term))[1].has(variable)
        for side in (equation.lhs, equation.rhs)
        for term in sp.Add.make_args(side)
    ):
        return "rational"

    expanded = sp.expand(expr)
    if expanded.is_polynomial(variable):
        degree = sp.Poly(expanded, variable).degree() if expanded.has(variable) else 0
        if degree <= 1:
            return "linear"
        if degree == 2:
            return "quadratic"
        return "polynomial"
    return "other"


def has_radical(expr: sp.Expr, variable: sp.Symbol) -> bool:
    return any(
        node.base.has(variable) and node.exp.is_Rational and not node.exp.is_Integer
        for node in expr.atoms(sp.Pow)
    )


def has_exponential(expr: sp.Expr, variable: sp.Symbol) -> bool:
    if any(node.has(variable) for node in expr.atoms(sp.exp)):
        return True
    return any(node.exp.has(variable) for node in expr.atoms(sp.Pow))
