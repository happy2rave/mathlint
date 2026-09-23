"""Quadratic equations, four ways.

* square roots — for ``(x + 1)^2 = 4`` or ``2x^2 = 8``, where there is no x-term;
* factoring — when the roots are rational: find two numbers, set each factor to 0;
* the quadratic formula — always works, and explains itself with the discriminant;
* completing the square — the method the formula comes from.

Every method lands on the same answers; the switcher on the page shows each.
"""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from ..parse.plain import latex_of
from .core import Equation, Outcome, Work, show
from .dispatch import register
from .polyform import standard_form


def _methods(equation: Equation, variable: sp.Symbol) -> list[str]:
    methods: list[str] = []
    a, b, c = _abc(sp.expand(equation.expr), variable)
    if _bracket_squared(equation, variable) is not None or b == 0:
        methods.append("square-root")
    if _rational_roots(a, b, c):
        methods.append("factoring")
    methods += ["formula", "completing-square"]
    return methods


@register("quadratic", methods=_methods)
def solve_quadratic(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    method = method or _methods(equation, variable)[0]

    if method == "square-root":
        squared = _bracket_squared(equation, variable)
        if squared is not None:
            inner, value = squared
            return _take_root(inner, value, variable, work)

    a, b, c = _standard_form(equation, variable, work)
    if method == "square-root":
        return _by_square_root(a, c, variable, work)
    if method == "factoring":
        return _by_factoring(a, b, c, variable, work)
    if method == "completing-square":
        return _by_completing_square(a, b, c, variable, work)
    return _by_formula(a, b, c, variable, work)


# ---------------------------------------------------------------- standard form


def _standard_form(
    equation: Equation, variable: sp.Symbol, work: Work
) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    """Bring the equation to ``a x^2 + b x + c = 0`` with nice coefficients."""
    return _abc(standard_form(equation, variable, work), variable)


def _abc(polynomial: sp.Expr, variable: sp.Symbol) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    coefficients = sp.Poly(polynomial, variable).all_coeffs()
    coefficients = [sp.Integer(0)] * (3 - len(coefficients)) + coefficients
    return tuple(coefficients[-3:])  # type: ignore[return-value]


def _quadratic(a: sp.Expr, b: sp.Expr, c: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    return a * variable**2 + b * variable + c


# ---------------------------------------------------------------- square roots


def _bracket_squared(equation: Equation, variable: sp.Symbol) -> tuple[sp.Expr, sp.Expr] | None:
    """``(x + 1)^2 = 4`` -> ``(x + 1, 4)``."""
    for square, other in ((equation.lhs, equation.rhs), (equation.rhs, equation.lhs)):
        if (
            isinstance(square, sp.Pow)
            and square.exp == 2
            and not other.has(variable)
            and sp.expand(square.base).is_polynomial(variable)
            and sp.Poly(sp.expand(square.base), variable).degree() == 1
        ):
            return square.base, other
    return None


def _by_square_root(a: sp.Expr, c: sp.Expr, variable: sp.Symbol, work: Work) -> Outcome:
    right = -c
    if c != 0:
        work.equation(msg("Move the constant to the right side"), Equation(a * variable**2, right))
    if a != 1:
        right = right / a
        work.equation(msg("Divide both sides by {a}", a=show(a)), Equation(variable**2, right))
    return _take_root(variable, right, variable, work)


def _take_root(inner: sp.Expr, value: sp.Expr, variable: sp.Symbol, work: Work) -> Outcome:
    value = sp.simplify(value)
    if value.is_negative:
        work.note(
            msg(
                "A square is never negative, and here it would equal "
                "{value}, so there is no real solution",
                value=show(value),
            )
        )
        return Outcome.none()
    if value == 0:
        work.equation(msg("Take the square root of both sides"), Equation(inner, 0))
        return Outcome.of([_solve_linear(inner, 0, variable)])
    root = sp.sqrt(value)
    work.alternatives(
        msg("Take the square root of both sides (a square root can be positive or negative)"),
        [Equation(inner, -root), Equation(inner, root)],
    )
    roots = [_solve_linear(inner, -root, variable), _solve_linear(inner, root, variable)]
    if inner != variable:
        work.alternatives(msg("Solve each one"), [Equation(variable, root) for root in roots])
    return Outcome.of(roots)


def _solve_linear(left: sp.Expr, right: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    return sp.simplify(sp.solve(sp.Eq(left, right), variable)[0])


# ---------------------------------------------------------------- factoring


def _rational_roots(a: sp.Expr, b: sp.Expr, c: sp.Expr) -> bool:
    if not all(coefficient.is_rational for coefficient in (a, b, c)):
        return False
    discriminant = b**2 - 4 * a * c
    return bool(discriminant >= 0) and sp.sqrt(discriminant).is_rational


def _by_factoring(a: sp.Expr, b: sp.Expr, c: sp.Expr, variable: sp.Symbol, work: Work) -> Outcome:
    polynomial = _quadratic(a, b, c, variable)
    factored = sp.factor(polynomial)
    discriminant = b**2 - 4 * a * c
    roots = sorted(sp.roots(sp.Poly(polynomial, variable)).keys(), key=lambda root: float(root))

    if c == 0:
        text = msg("Factor out the common factor {variable}", variable=variable)
    elif b == 0:
        text = msg("Factor the difference of two squares: a^2 - b^2 = (a - b)(a + b)")
    elif discriminant == 0:
        text = msg("Factor the perfect square: a^2 + 2ab + b^2 = (a + b)^2")
    else:
        first, second = roots
        if a == 1:
            text = msg(
                "Factor: find two numbers that multiply to {c} and add up to "
                "{b}: {first} and {second}",
                c=show(c),
                b=show(b),
                first=show(-first),
                second=show(-second),
            )
        else:
            text = msg(
                "Factor: find two numbers that multiply to a*c = {a} and add "
                "up to {b}: {first} and {second}",
                a=show(a * c),
                b=show(b),
                first=show(-a * first),
                second=show(-a * second),
            )
    work.equation(text, Equation(factored, 0))

    factors = [factor for factor, _ in sp.factor_list(polynomial)[1] if factor.has(variable)]
    if len(factors) == 1:
        work.equation(
            msg("A square is zero only when the bracket is zero"), Equation(factors[0], 0)
        )
    else:
        work.alternatives(
            msg("A product is zero exactly when one of its factors is zero"),
            [Equation(factor, 0) for factor in factors],
        )
    values = sorted({_solve_linear(factor, 0, variable) for factor in factors}, key=float)
    if any(factor != variable for factor in factors):
        work.alternatives(msg("Solve each one"), [Equation(variable, value) for value in values])
    return Outcome.of(values)


# ---------------------------------------------------------------- the formula


def _needs_brackets(value: sp.Expr) -> bool:
    return value.could_extract_minus_sign() or not value.is_Atom


def _paren(value: sp.Expr) -> str:
    text = show(value)
    return f"({text})" if _needs_brackets(value) else text


def _paren_latex(value: sp.Expr) -> str:
    text = latex_of(value)
    return rf"\left({text}\right)" if _needs_brackets(value) else text


def _by_formula(a: sp.Expr, b: sp.Expr, c: sp.Expr, variable: sp.Symbol, work: Work) -> Outcome:
    work.show(
        msg("Read off the coefficients of a x^2 + b x + c = 0"),
        f"a = {show(a)}, b = {show(b)}, c = {show(c)}",
        rf"a = {latex_of(a)},\quad b = {latex_of(b)},\quad c = {latex_of(c)}",
    )
    discriminant = sp.simplify(b**2 - 4 * a * c)
    work.show(
        msg("Work out the discriminant D = b^2 - 4ac"),
        f"D = {_paren(b)}^2 - 4*{_paren(a)}*{_paren(c)} = {show(discriminant)}",
        rf"D = {_paren_latex(b)}^2 - 4 \cdot {_paren_latex(a)} \cdot {_paren_latex(c)} "
        rf"= {latex_of(discriminant)}",
    )

    v = latex_of(variable)
    if discriminant.is_negative:
        low = sp.simplify((-b - sp.sqrt(discriminant)) / (2 * a))
        high = sp.simplify((-b + sp.sqrt(discriminant)) / (2 * a))
        work.note(
            msg(
                "D is negative, so there is no real solution (in the complex "
                "numbers: {variable} = {low} or {variable} = {high})",
                variable=variable,
                low=show(low),
                high=show(high),
            )
        )
        return Outcome.none()

    if discriminant == 0:
        root = sp.simplify(-b / (2 * a))
        work.show(
            msg(
                "D = 0, so there is exactly one solution: {variable} = -b / (2a)", variable=variable
            ),
            f"{variable} = {show(root)}",
            rf"{v} = {latex_of(root)}",
        )
        return Outcome.of([root])

    work.show(
        msg("Use the quadratic formula {variable} = (-b +/- sqrt(D)) / (2a)", variable=variable),
        f"{variable} = (-{_paren(b)} +/- sqrt({show(discriminant)})) / (2*{_paren(a)})",
        rf"{v} = \frac{{-{_paren_latex(b)} \pm \sqrt{{{latex_of(discriminant)}}}}}"
        rf"{{2 \cdot {_paren_latex(a)}}}",
    )
    low = sp.simplify((-b - sp.sqrt(discriminant)) / (2 * a))
    high = sp.simplify((-b + sp.sqrt(discriminant)) / (2 * a))
    work.alternatives(
        msg("Work out both signs"), [Equation(variable, low), Equation(variable, high)]
    )
    return Outcome.of([low, high])


# ---------------------------------------------------------------- completing the square


def _by_completing_square(
    a: sp.Expr, b: sp.Expr, c: sp.Expr, variable: sp.Symbol, work: Work
) -> Outcome:
    p, q = sp.simplify(b / a), sp.simplify(c / a)
    if a != 1:
        work.equation(
            msg("Divide both sides by {a}", a=show(a)),
            Equation(variable**2 + p * variable + q, 0),
            operation=f"/ {show(a)}",
        )
    if q != 0:
        work.equation(
            msg("Move the constant to the right side"), Equation(variable**2 + p * variable, -q)
        )
    half = p / 2
    added = sp.simplify(half**2)
    work.equation(
        msg(
            "Add (half of the {variable} coefficient)^2 = ({half})^2 = "
            "{added} to both sides to complete the square",
            variable=variable,
            half=show(half),
            added=show(added),
        ),
        Equation(variable**2 + p * variable + added, sp.simplify(-q + added)),
        operation=f"+ {show(added)}",
    )
    value = sp.simplify(-q + added)
    inner = variable + half
    work.equation(
        msg("The left side is now a perfect square"),
        Equation(sp.Pow(inner, 2, evaluate=False), value),
    )
    return _take_root(inner, value, variable, work)
