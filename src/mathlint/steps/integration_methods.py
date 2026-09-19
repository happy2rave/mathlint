"""Two integration methods written out in full, the way a course teaches them.

Partial fractions: divide first if the top is not smaller than the bottom,
factor the bottom, write the fraction as a sum with unknown numbers on top,
find the numbers (by putting in the roots, or by comparing coefficients), and
integrate each piece — the logarithms with absolute values, as they should be.

Trigonometric substitution: a square root of a^2 - x^2, a^2 + x^2 or x^2 - a^2
becomes a cosine, a secant or a tangent after x = a sin t, a tan t or a sec t,
the integral is done in t, and the triangle takes it back to x.

Each method returns None when it does not apply; the caller checks the answer
by differentiating it before using it.
"""

from __future__ import annotations

import math
import string

import sympy as sp

from ..parse.plain import latex_of, read_as
from .solution import Solution, SolutionStep

MAX_DEGREE = 6
THETA = sp.Symbol("theta")


def _show(solution: Solution, text: str, plain: str = "", latex: str = "") -> None:
    solution.steps.append(SolutionStep(text=text, display=plain, display_latex=latex))


def _expr(solution: Solution, text: str, expression: sp.Expr) -> None:
    _show(solution, text, read_as(expression), latex_of(expression))


def _eq(solution: Solution, text: str, left: sp.Expr, right: sp.Expr) -> None:
    _show(
        solution,
        text,
        f"{read_as(left)} = {read_as(right)}",
        f"{latex_of(left)} = {latex_of(right)}",
    )


# --- partial fractions --------------------------------------------------------------------


def partial_fractions(f: sp.Expr, x: sp.Symbol, solution: Solution) -> sp.Expr | None:
    top, bottom = sp.fraction(sp.together(f))
    if not (top.is_polynomial(x) and bottom.is_polynomial(x)) or not bottom.has(x):
        return None
    top_poly, bottom_poly = sp.Poly(top, x), sp.Poly(bottom, x)
    if bottom_poly.degree() < 2 or bottom_poly.degree() > MAX_DEGREE:
        return None  # 1/(ax + b) is a plain substitution; very high degrees are not by hand
    constant, factors = sp.factor_list(bottom, x)
    if any(sp.degree(factor, x) > 2 for factor, _ in factors):
        return None
    if len(factors) == 1 and factors[0][1] == 1 and sp.degree(factors[0][0], x) == 2:
        return None  # one irreducible quadratic: an arctangent, not partial fractions

    quotient, remainder = sp.div(top_poly, bottom_poly)
    quotient, remainder = quotient.as_expr(), remainder.as_expr()
    if quotient != 0:
        _show(
            solution,
            "The top's degree is not smaller than the bottom's, so divide first "
            "(polynomial long division)",
            f"{read_as(quotient)} + ({read_as(remainder)})/({read_as(bottom)})",
            rf"{latex_of(quotient)} + \frac{{{latex_of(remainder)}}}{{{latex_of(bottom)}}}",
        )
    if remainder == 0:
        return _integrate_polynomial(quotient, x, solution)

    factored = constant * sp.Mul(*[factor**power for factor, power in factors])
    if read_as(factored) != read_as(bottom):
        _show(
            solution,
            "Factor the bottom",
            f"{_top(remainder)}/{_bottom(factored)}",
            rf"\frac{{{latex_of(remainder)}}}{{{latex_of(factored)}}}",
        )

    names = iter(string.ascii_uppercase)
    pieces: list[tuple[sp.Expr, sp.Expr]] = []  # (numerator with unknowns, denominator)
    unknowns: list[sp.Symbol] = []
    for factor, power in factors:
        for j in range(1, power + 1):
            if sp.degree(factor, x) == 1:
                a = sp.Symbol(next(names))
                unknowns.append(a)
                pieces.append((a, factor**j))
            else:
                b, c = sp.Symbol(next(names)), sp.Symbol(next(names))
                unknowns.extend([b, c])
                pieces.append((b * x + c, factor**j))
    template_plain = " + ".join(f"{_top(n)}/{_bottom(d)}" for n, d in pieces)
    template_latex = " + ".join(rf"\frac{{{latex_of(n)}}}{{{latex_of(d)}}}" for n, d in pieces)
    _show(
        solution,
        "Write it as a sum of simpler fractions, with unknown numbers on top",
        template_plain,
        template_latex,
    )

    whole = sp.Mul(*[factor**power for factor, power in factors])
    identity_terms = [n * sp.cancel(whole / d) for n, d in pieces]
    scaled_remainder = sp.expand(remainder / constant)
    _show(
        solution,
        "Multiply both sides by the bottom",
        f"{read_as(scaled_remainder)} = "
        + " + ".join(f"{_top(n)}*{_top(sp.factor(sp.cancel(whole / d)))}" for n, d in pieces),
        f"{latex_of(scaled_remainder)} = "
        + " + ".join(
            rf"{_latex_top(n)} {_latex_bottom(sp.factor(sp.cancel(whole / d)))}" for n, d in pieces
        ),
    )
    difference = sp.expand(scaled_remainder - sp.Add(*identity_terms))
    values = sp.solve(sp.Poly(difference, x).all_coeffs(), unknowns, dict=True)
    if not values:
        return None
    values = values[0]
    if all(sp.degree(d, x) == 1 for _, d in pieces):
        for (numerator, denominator), term in zip(pieces, identity_terms, strict=True):
            root = sp.solve(denominator, x)[0]
            at_root = scaled_remainder.subs(x, root)
            cofactor = sp.cancel(term / numerator).subs(x, root)
            _show(
                solution,
                f"Put {x} = {read_as(root)}: every other term has a factor that is 0 there",
                f"{read_as(at_root)} = {read_as(cofactor)}*{numerator}, so {numerator} = "
                f"{read_as(values[numerator])}",
                rf"{latex_of(at_root)} = {latex_of(cofactor)} {numerator} \quad\Rightarrow\quad "
                rf"{numerator} = {latex_of(values[numerator])}",
            )
    else:
        _show(
            solution,
            "Compare the numbers in front of each power of x on both sides, and solve",
            ", ".join(f"{name} = {read_as(values[name])}" for name in unknowns),
            r",\ ".join(f"{latex_of(name)} = {latex_of(values[name])}" for name in unknowns),
        )

    known = [(n.subs(values), d) for n, d in pieces]
    known = [(sp.expand(n / constant), d) for n, d in known]
    total = sp.Integer(0)
    if quotient != 0:
        total += _integrate_polynomial(quotient, x, solution)
    for numerator, denominator in known:
        if numerator == 0:
            continue
        total += _integrate_piece(numerator, denominator, x, solution)
    _expr(solution, "Add the pieces", total)
    return total


def _top(numerator: sp.Expr) -> str:
    text = read_as(numerator)
    return f"({text})" if isinstance(numerator, sp.Add) else text


def _bottom(denominator: sp.Expr) -> str:
    text = read_as(denominator)
    return text if denominator.is_Symbol or isinstance(denominator, sp.Pow) else f"({text})"


def _latex_top(numerator: sp.Expr) -> str:
    text = latex_of(numerator)
    return rf"\left({text}\right)" if isinstance(numerator, sp.Add) else text


def _latex_bottom(expression: sp.Expr) -> str:
    text = latex_of(expression)
    return (
        text if expression.is_Symbol or isinstance(expression, sp.Pow) else rf"\left({text}\right)"
    )


def _integrate_polynomial(polynomial: sp.Expr, x: sp.Symbol, solution: Solution) -> sp.Expr:
    result = sp.integrate(polynomial, x)
    _eq(
        solution,
        "The polynomial part, with the power rule",
        sp.Integral(polynomial, x),
        result,
    )
    return result


def _integrate_piece(numerator, denominator, x, solution: Solution) -> sp.Expr:
    base, power = denominator.as_base_exp()
    integral = sp.Integral(numerator / denominator, x)
    if sp.degree(base, x) == 1:
        slope = sp.Poly(base, x).LC()
        if power == 1:
            result = numerator / slope * sp.log(sp.Abs(base))
            text = f"int c/(ax + b) dx = (c/a) ln|ax + b|, with a = {read_as(slope)}"
        else:
            result = numerator / (slope * (1 - power)) * base ** (1 - power)
            text = "Power rule on the bracket: int c (ax + b)^(-n) dx = c (ax + b)^(1-n) / (a(1-n))"
        _eq(solution, text, integral, result)
        return result
    result = sp.integrate(numerator / denominator, x)
    _eq(
        solution,
        "Split the top into a multiple of the bottom's derivative (which gives a logarithm) "
        "and a number (which gives an arctangent)",
        integral,
        result,
    )
    return result


# --- trigonometric substitution --------------------------------------------------------------


def trig_substitution(f: sp.Expr, x: sp.Symbol, solution: Solution) -> sp.Expr | None:
    radicands = {
        node.base
        for node in sp.preorder_traversal(f)
        if isinstance(node, sp.Pow) and node.exp.is_Rational and node.exp.q == 2
    }
    if len(radicands) != 1:
        return None
    (radicand,) = radicands
    if not radicand.is_polynomial(x):
        return None
    poly = sp.Poly(radicand, x)
    if poly.degree() != 2 or poly.coeff_monomial(x) != 0:
        return None
    square, constant = poly.coeff_monomial(x**2), poly.coeff_monomial(1)
    if not (square.is_number and constant.is_number) or constant == 0:
        return None
    a = sp.sqrt(abs(constant / square))
    k = sp.sqrt(abs(square))

    s, c, t = sp.sin(THETA), sp.cos(THETA), sp.tan(THETA)
    side = sp.sqrt(sp.expand(radicand / abs(square)))  # the right triangle's third side
    if square < 0 < constant:
        pattern, x_of_t, dx = "a^2 - x^2", a * s, a * c
        root_of_t = k * a * c
        back = sp.asin(x / a)
        triangle = {s: x / a, c: side / a, t: x / side}
    elif square > 0 and constant > 0:
        pattern, x_of_t, dx = "a^2 + x^2", a * t, a * sp.sec(THETA) ** 2
        root_of_t = k * a * sp.sec(THETA)
        back = sp.atan(x / a)
        triangle = {s: x / side, c: a / side, t: x / a}
    elif square > 0 > constant:
        pattern, x_of_t, dx = "x^2 - a^2", a * sp.sec(THETA), a * sp.sec(THETA) * t
        root_of_t = k * a * t
        back = sp.asec(x / a)
        triangle = {s: side / x, c: a / x, t: side / a}
    else:
        return None
    _show(
        solution,
        f"The square root has the shape sqrt({pattern}) with a = {read_as(a)}, so substitute "
        f"{x} = {read_as(x_of_t)}. Then d{x} = {read_as(dx)} d(theta), and the square root "
        "becomes a single trigonometric function",
        f"sqrt({read_as(radicand)}) = {read_as(root_of_t)}",
        rf"\sqrt{{{latex_of(radicand)}}} = {latex_of(root_of_t)}",
    )
    replaced = f.xreplace(
        {
            node: root_of_t ** (2 * node.exp)
            for node in sp.preorder_traversal(f)
            if isinstance(node, sp.Pow) and node.base == radicand
        }
    )
    substituted = replaced.subs(x, x_of_t) * dx
    in_theta = sp.trigsimp(sp.simplify(substituted))
    if read_as(in_theta) != read_as(substituted):
        _eq(
            solution,
            "The integral in theta, simplified",
            sp.Integral(substituted, THETA),
            sp.Integral(in_theta, THETA),
        )
    else:
        _expr(solution, "The integral in theta", sp.Integral(in_theta, THETA))
    if sp.simplify(in_theta - sp.sec(THETA)) == 0:
        antiderivative = sp.log(sp.Abs(sp.sec(THETA) + t))
        text = "int sec(theta) dtheta = ln|sec(theta) + tan(theta)|"
    else:
        antiderivative = sp.integrate(in_theta, THETA)
        if antiderivative.has(sp.Integral):
            return None
        antiderivative = sp.simplify(antiderivative)
        text = "Integrate in theta"
    _eq(solution, text, sp.Integral(in_theta, THETA), antiderivative)
    # sin(2t) = 2 sin(t) cos(t) and friends, so only sin, cos and tan of t are left
    written = sp.expand_trig(antiderivative).subs(
        {sp.sec(THETA): 1 / c, sp.csc(THETA): 1 / s, sp.cot(THETA): c / s}
    )
    result = sp.simplify(written.xreplace(triangle).xreplace({THETA: back}))
    relations = ", ".join(f"{read_as(key)} = {read_as(value)}" for key, value in triangle.items())
    _show(
        solution,
        f"Back to {x} with the right triangle for theta = {read_as(back)}: {relations}",
        read_as(result),
        latex_of(result),
    )
    return result


# --- checking ----------------------------------------------------------------------------------

_POINTS = (0.37, 0.61, 1.3, 1.73, 2.9, 4.6, -0.45, -1.4, -3.3, 7.1)


def differentiates_back(antiderivative: sp.Expr, f: sp.Expr, x: sp.Symbol) -> bool:
    """True when the derivative of ``antiderivative`` equals ``f`` at several real points."""
    real = sp.Symbol(x.name, real=True)
    derivative = sp.diff(antiderivative.subs(x, real), real)
    integrand = f.subs(x, real)
    agreed = 0
    for point in _POINTS:
        try:
            want = complex(sp.N(integrand.subs(real, point)))
            got = complex(sp.N(derivative.subs(real, point)))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if not all(map(math.isfinite, (want.real, want.imag, got.real, got.imag))):
            continue
        if abs(want.imag) > 1e-9:
            continue  # outside the real domain
        if abs(got - want) > 1e-6 * max(1.0, abs(want)):
            return False
        agreed += 1
    return agreed >= 2
