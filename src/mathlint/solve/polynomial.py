"""Polynomial equations of degree three and up.

The by-hand toolbox, in the order a student would reach for it:

1. take out a common factor ``x^k`` — that gives the root 0;
2. if every power is a multiple of some k, substitute ``u = x^k`` and solve the
   smaller equation (``x^4 - 5x^2 + 4 = 0`` is a quadratic in ``u = x^2``);
3. the rational root theorem: try the candidates ``p/q``, and when one works,
   divide it out and carry on with a polynomial one degree lower.

What is left over when none of that applies has no "nice" roots; those are found
numerically and said to be approximate.
"""

from __future__ import annotations

import math

import sympy as sp

from ..i18n import msg
from ..parse.plain import latex_of
from . import dispatch
from .core import Equation, Outcome, Work, show, sort_values
from .dispatch import register
from .polyform import standard_form

_U = sp.Symbol("u")
_MAX_CANDIDATES_SHOWN = 12


@register("polynomial", methods=lambda equation, variable: ["roots"])
def solve_polynomial(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    polynomial = standard_form(equation, variable, work)
    poly = sp.Poly(polynomial, variable)

    lowest = min(monomial[0] for monomial in poly.monoms())
    if lowest >= 1:
        return _common_factor(polynomial, lowest, variable, work, depth)

    step = math.gcd(*[monomial[0] for monomial in poly.monoms()])
    if step >= 2:
        return _substitute(polynomial, step, variable, work, depth)

    if all(coefficient.is_Integer for coefficient in poly.all_coeffs()):
        outcome = _rational_root(poly, variable, work, depth)
        if outcome is not None:
            return outcome

    return _approximate(poly, variable, work)


def _common_factor(
    polynomial: sp.Expr, power: int, variable: sp.Symbol, work: Work, depth: int
) -> Outcome:
    factor = variable**power
    rest = sp.expand(polynomial / factor)
    work.equation(
        msg("Factor out {factor}", factor=show(factor)),
        Equation(sp.Mul(factor, rest, evaluate=False), 0),
    )
    work.alternatives(
        msg("A product is zero exactly when one of its factors is zero"),
        [Equation(variable, 0), Equation(rest, 0)],
    )
    return Outcome.of([0]).merge(
        dispatch.solve_equation(Equation(rest, 0), variable, work, depth=depth + 1)
    )


def _substitute(
    polynomial: sp.Expr, step: int, variable: sp.Symbol, work: Work, depth: int
) -> Outcome:
    power = variable**step
    reduced = sp.expand(polynomial.subs(power, _U))
    work.equation(
        msg(
            "Every power of {variable} is a multiple of {step}, so substitute u = {power}",
            variable=variable,
            step=step,
            power=show(power),
        ),
        Equation(reduced, 0),
    )
    found = dispatch.solve_equation(Equation(reduced, 0), _U, work, depth=depth + 1)
    if found.everything:
        return Outcome.all()

    values: list[sp.Expr] = []
    back: list[Equation] = []
    for u_value in found.values:
        back.append(Equation(power, u_value))
        if step % 2 == 1:
            values.append(sp.real_root(u_value, step))
        elif u_value.is_negative:
            continue
        else:
            root = sp.root(u_value, step)
            values.extend([-root, root])
    values = sort_values(values)
    if back:
        work.alternatives(msg("Put {power} back in place of u", power=show(power)), back)
    if values:
        roots_word = msg("square root") if step == 2 else msg("{step}th root", step=step)
        work.alternatives(
            msg(
                "Take the {roots_word} (a negative u gives no real {variable})",
                roots_word=roots_word,
                variable=variable,
            ),
            [Equation(variable, value) for value in values],
        )
    else:
        work.note(
            msg(
                "None of these values of {power} gives a real {variable}",
                power=show(power),
                variable=variable,
            )
        )
    return Outcome.of(values)


def _candidates(poly: sp.Poly) -> list[sp.Rational]:
    constant = abs(int(poly.all_coeffs()[-1]))
    leading = abs(int(poly.LC()))
    found = {sp.Rational(p, q) for p in sp.divisors(constant) for q in sp.divisors(leading)}
    ordered = sorted(found, key=lambda value: (abs(value), value))
    return [value for candidate in ordered for value in (candidate, -candidate)]


def _rational_root(poly: sp.Poly, variable: sp.Symbol, work: Work, depth: int) -> Outcome | None:
    candidates = _candidates(poly)
    shown = sorted({abs(value) for value in candidates}, key=float)
    listed = ", ".join(f"+/-{show(value)}" for value in shown[:_MAX_CANDIDATES_SHOWN])
    listed_latex = ", ".join(rf"\pm {latex_of(value)}" for value in shown[:_MAX_CANDIDATES_SHOWN])
    if len(shown) > _MAX_CANDIDATES_SHOWN:
        listed += ", ..."
        listed_latex += r", \ldots"

    for candidate in candidates:
        if poly.eval(candidate) != 0:
            continue
        work.show(
            msg(
                "By the rational root theorem, a root that is a whole number "
                "or a fraction must divide the constant term by the leading "
                "coefficient"
            ),
            listed,
            listed_latex,
        )
        factor = candidate.q * variable - candidate.p
        work.note(
            msg(
                "Try {variable} = {candidate}: it gives 0, so ({factor}) is a factor",
                variable=variable,
                candidate=show(candidate),
                factor=show(factor),
            )
        )
        quotient, _ = sp.div(poly.as_expr(), factor, variable)
        work.equation(
            msg("Divide by ({factor}) (synthetic division)", factor=show(factor)),
            Equation(sp.Mul(factor, quotient, evaluate=False), 0),
        )
        work.alternatives(
            msg("A product is zero exactly when one of its factors is zero"),
            [Equation(factor, 0), Equation(quotient, 0)],
        )
        return Outcome.of([candidate]).merge(
            dispatch.solve_equation(Equation(quotient, 0), variable, work, depth=depth + 1)
        )
    return None


def _approximate(poly: sp.Poly, variable: sp.Symbol, work: Work) -> Outcome:
    roots = [sp.Float(sp.N(root, 20), 12) for root in sp.real_roots(poly)]
    work.note(
        msg(
            "This polynomial has no rational root and cannot be factored "
            "by hand, so its real roots are found numerically (to about "
            "10 digits)"
        )
    )
    if roots:
        work.alternatives(msg("The real roots"), [Equation(variable, root) for root in roots])
    return Outcome.of(roots)
