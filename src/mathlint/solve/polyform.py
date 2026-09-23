"""Bring a polynomial equation to ``p(x) = 0`` with tidy coefficients.

Shared by the quadratic and higher-degree solvers: move every term to the left,
clear fractions, make the leading coefficient positive, divide out a common
whole-number factor — each change shown as its own step.
"""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from .core import Equation, Work


def standard_form(equation: Equation, variable: sp.Symbol, work: Work) -> sp.Expr:
    polynomial = sp.expand(equation.expr)
    already = equation.rhs == 0 and sp.expand(equation.lhs) == equation.lhs
    if not already:
        expanded = (sp.expand(equation.lhs), sp.expand(equation.rhs)) != (
            equation.lhs,
            equation.rhs,
        )
        text = (
            msg("Expand the brackets and move every term to the left side")
            if expanded
            else msg("Move every term to the left side")
        )
        work.equation(text, Equation(polynomial, 0))

    coefficients = sp.Poly(polynomial, variable).coeffs()
    if all(coefficient.is_Rational for coefficient in coefficients):
        denominator = sp.ilcm(*[coefficient.q for coefficient in coefficients])
        if denominator != 1:
            polynomial = sp.expand(polynomial * denominator)
            work.equation(
                msg(
                    "Multiply both sides by {denominator} to clear the fractions",
                    denominator=denominator,
                ),
                Equation(polynomial, 0),
                operation=f"* {denominator}",
            )

    leading = sp.Poly(polynomial, variable)
    if leading.LC().is_negative:
        polynomial = sp.expand(-polynomial)
        work.equation(
            msg(
                "Multiply both sides by -1 so the {variable}^{degree} term is positive",
                variable=variable,
                degree=leading.degree(),
            ),
            Equation(polynomial, 0),
            operation="* (-1)",
        )

    coefficients = sp.Poly(polynomial, variable).coeffs()
    if all(coefficient.is_Integer for coefficient in coefficients):
        divisor = sp.gcd_list(coefficients)
        if divisor > 1:
            polynomial = sp.expand(polynomial / divisor)
            work.equation(
                msg("Divide both sides by {divisor}", divisor=divisor),
                Equation(polynomial, 0),
                operation=f"/ {divisor}",
            )
    return polynomial
