"""Exponential equations: the unknown is in an exponent.

* same base — ``9^x = 3^(x+1)`` is ``3^(2x) = 3^(x+1)``, so ``2x = x + 1``;
* logarithms — take ln of both sides and use ``ln(a^u) = u ln(a)``;
* substitution — ``e^(2x) - 3e^x + 2 = 0`` is a quadratic in ``t = e^x``.

A power of a positive number is always positive; an equation that needs it to
be zero or negative has no solution, and says so.
"""

from __future__ import annotations

import sympy as sp

from ..parse.plain import latex_of
from . import dispatch
from .core import Equation, Outcome, Work, show, sort_values
from .dispatch import register
from .isolate import already_isolated, isolate

_T = sp.Symbol("t")


def _powers(expr: sp.Expr, variable: sp.Symbol) -> list[sp.Expr]:
    found = [node for node in expr.atoms(sp.exp) if node.has(variable)]
    found += [node for node in expr.atoms(sp.Pow) if node.exp.has(variable)]
    return sorted(set(found), key=sp.default_sort_key)


def _base_and_exponent(power: sp.Expr) -> tuple[sp.Expr, sp.Expr]:
    if isinstance(power, sp.exp):
        return sp.E, power.args[0]
    return power.base, power.exp


def _as_power(value: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """``8 -> (2, 3)``, ``1/9 -> (3, -2)``: the smallest whole-number base."""
    if not value.is_Rational or value <= 0:
        return None
    if value == 1:
        return None
    numerator, denominator = value.p, value.q
    if denominator == 1:
        root = sp.perfect_power(numerator)
        return (sp.Integer(root[0]), sp.Integer(root[1])) if root else (sp.Integer(numerator), 1)
    if numerator == 1:
        root = sp.perfect_power(denominator)
        base, exponent = root if root else (denominator, 1)
        return sp.Integer(base), -sp.Integer(exponent)
    return None


def _common_base(first: sp.Expr, second: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Write both numbers as powers of one base: ``(4, 8) -> (2, 2, 3)``."""
    one, two = _as_power(first), _as_power(second)
    if one is None or two is None or one[0] != two[0]:
        return None
    return one[0], sp.Integer(one[1]), sp.Integer(two[1])


def _single_power(side: sp.Expr, variable: sp.Symbol) -> bool:
    powers = _powers(side, variable)
    return len(powers) == 1 and side == powers[0] and not _base_and_exponent(side)[0].has(variable)


def _methods(equation: Equation, variable: sp.Symbol) -> list[str]:
    if _single_power(equation.lhs, variable) and _single_power(equation.rhs, variable):
        bases = (_base_and_exponent(equation.lhs)[0], _base_and_exponent(equation.rhs)[0])
        if bases[0] == bases[1] or _common_base(*bases):
            return ["same-base", "logarithms"]
        return ["logarithms"]
    powers = _powers(equation.expr, variable)
    if len(powers) > 1:
        return ["substitution"]
    if len(powers) == 1:
        isolated = isolate(equation, powers[0])
        base = _base_and_exponent(powers[0])[0]
        if isolated is not None and (
            isolated.rhs == 1 or _common_base(base, isolated.rhs) is not None
        ):
            return ["same-base", "logarithms"]
    return ["logarithms"]


@register("exponential", methods=_methods)
def solve_exponential(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    method = method or _methods(equation, variable)[0]
    if _single_power(equation.lhs, variable) and _single_power(equation.rhs, variable):
        return _power_equals_power(equation, variable, work, method, depth)

    powers = _powers(equation.expr, variable)
    if len(powers) == 1:
        return _one_power(equation, powers[0], variable, work, method, depth)

    substituted = _substitute(equation, powers, variable, work, depth)
    if substituted is not None:
        return substituted
    return dispatch.SOLVERS["other"](equation, variable, work, None, depth)


def _power_equals_power(
    equation: Equation, variable: sp.Symbol, work: Work, method: str, depth: int
) -> Outcome:
    (b1, u1), (b2, u2) = _base_and_exponent(equation.lhs), _base_and_exponent(equation.rhs)
    if method == "same-base":
        if b1 == b2:
            base, m1, m2 = b1, sp.Integer(1), sp.Integer(1)
        else:
            base, m1, m2 = _common_base(b1, b2)
            work.equation(
                f"Write both sides as powers of {show(base)}",
                Equation(
                    sp.Pow(base, sp.expand(m1 * u1), evaluate=False),
                    sp.Pow(base, sp.expand(m2 * u2), evaluate=False),
                ),
            )
        exponents = Equation(sp.expand(m1 * u1), sp.expand(m2 * u2))
        work.equation("The bases are the same, so the exponents are equal", exponents)
        return dispatch.solve_equation(exponents, variable, work, depth=depth + 1)

    logged = Equation(sp.expand(u1 * sp.log(b1)), sp.expand(u2 * sp.log(b2)))
    work.equation("Take the natural logarithm of both sides, using ln(a^u) = u*ln(a)", logged)
    return dispatch.solve_equation(logged, variable, work, depth=depth + 1)


def _one_power(
    equation: Equation,
    power: sp.Expr,
    variable: sp.Symbol,
    work: Work,
    method: str,
    depth: int,
) -> Outcome:
    isolated = isolate(equation, power)
    if isolated is None:
        substituted = _substitute(equation, [power], variable, work, depth)
        if substituted is not None:
            return substituted
        return dispatch.SOLVERS["other"](equation, variable, work, None, depth)
    if not already_isolated(equation, power):
        work.equation("Isolate the power on one side", isolated)

    value = isolated.rhs
    base, exponent = _base_and_exponent(power)
    if value.is_number and not value.is_positive:
        work.note(
            f"A power of a positive number is always positive, so it can never equal "
            f"{show(value)}: there is no solution"
        )
        return Outcome.none()

    if method == "same-base":
        if value == 1:
            exponents = Equation(exponent, 0)
            work.equation("Any number to the power 0 is 1, so the exponent is 0", exponents)
            return dispatch.solve_equation(exponents, variable, work, depth=depth + 1)
        common = _common_base(base, value)
        if common is not None:
            new_base, m1, m2 = common
            work.equation(
                f"Write both sides as powers of {show(new_base)}",
                Equation(
                    sp.Pow(new_base, sp.expand(m1 * exponent), evaluate=False),
                    sp.Pow(new_base, m2, evaluate=False),
                ),
            )
            exponents = Equation(sp.expand(m1 * exponent), m2)
            work.equation("The bases are the same, so the exponents are equal", exponents)
            return dispatch.solve_equation(exponents, variable, work, depth=depth + 1)

    if base == sp.E:
        logged = Equation(exponent, sp.log(value))
        work.equation("Take the natural logarithm of both sides, using ln(e^u) = u", logged)
    else:
        logged = Equation(sp.expand(exponent * sp.log(base)), sp.log(value))
        work.equation("Take the natural logarithm of both sides, using ln(a^u) = u*ln(a)", logged)
    return dispatch.solve_equation(logged, variable, work, depth=depth + 1)


def _substitute(
    equation: Equation, powers: list[sp.Expr], variable: sp.Symbol, work: Work, depth: int
) -> Outcome | None:
    """``e^(2x) - 3e^x + 2 = 0`` -> ``t^2 - 3t + 2 = 0`` with ``t = e^x``."""
    bases = {_base_and_exponent(power)[0] for power in powers}
    if len(bases) != 1:
        return None
    base = bases.pop()
    replacements = {}
    for power in powers:
        multiple = sp.simplify(_base_and_exponent(power)[1] / variable)
        if not (multiple.is_Integer and multiple > 0):
            return None
        replacements[power] = _T**multiple
    reduced = sp.expand(equation.expr.xreplace(replacements))
    if reduced.has(variable):
        return None

    simple = sp.exp(variable) if base == sp.E else sp.Pow(base, variable, evaluate=False)
    work.show(
        f"Substitute t = {show(simple)}",
        f"{show(reduced)} = 0",
        f"{latex_of(reduced)} = 0",
    )
    found = dispatch.solve_equation(Equation(reduced, 0), _T, work, depth=depth + 1)
    positive = [value for value in sort_values(found.values) if value.is_positive]
    dropped = [value for value in found.values if not value.is_positive]
    if dropped:
        work.note(
            f"t = {show(simple)} is always positive, so "
            + ", ".join(f"t = {show(value)}" for value in dropped)
            + " gives no solution"
        )
    answers = [sp.simplify(sp.log(value) / sp.log(base)) for value in positive]
    if answers:
        work.alternatives(
            f"Put {show(simple)} back in place of t and take the natural logarithm",
            [Equation(variable, answer) for answer in answers],
        )
    return Outcome.of(answers)
