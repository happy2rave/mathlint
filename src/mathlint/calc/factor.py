"""Factoring with steps, in the order a teacher checks for things.

1. a common factor (a number, a power of a letter, a minus sign);
2. two terms: a difference of squares, or a sum or difference of cubes;
3. three terms: a perfect square, two numbers that multiply to c and add to b
   (splitting the middle term when x^2 has a number in front), or a quadratic
   in disguise such as x^4 - 5x^2 + 4;
4. four terms: grouping in pairs;
5. higher powers: a root found by trying the divisors (the factor theorem).

Every new factor goes through the list again, so x^4 - 16 becomes
(x^2 - 4)(x^2 + 4) and then (x - 2)(x + 2)(x^2 + 4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import sympy as sp
from sympy.core.parameters import distribute

from ..parse.plain import latex_of, read_as
from .expression import Steps, method, show

MAX_ROUNDS = 20
MAX_CANDIDATES = 10**6


@dataclass
class Found:
    factors: list[tuple[sp.Expr, int]]
    text: str
    # the working in between, as (text, plain, latex) of the factor being worked on
    working: list[tuple[str, str, str]] = field(default_factory=list)


def can_factor(expression: sp.Expr) -> bool:
    symbols = expression.free_symbols
    if not symbols or not expression.is_polynomial(*symbols):
        return False
    return _differs(sp.factor(expression), expression)


def _differs(factored: sp.Expr, expression: sp.Expr) -> bool:
    return read_as(factored) != read_as(expression) and isinstance(factored, sp.Mul | sp.Pow)


@method("factor", applies=can_factor)
def factor_steps(expression: sp.Expr, steps: Steps) -> sp.Expr:
    polynomial = _expanded(expression)
    if read_as(polynomial) != read_as(expression):
        steps.show("Multiply out first", polynomial)
    outside, rest = common_factor(polynomial)
    if outside != 1:
        text = (
            "Take out a minus sign"
            if outside == -1
            else f"Take out the common factor {show(outside)}"
        )
        steps.show(text, _product(outside, [(rest, 1)]))
    done: list[tuple[sp.Expr, int]] = []
    pending: list[tuple[sp.Expr, int]] = [(rest, 1)]
    for _ in range(MAX_ROUNDS):
        if not pending:
            break
        current, power = pending.pop(0)
        found = factor_once(current)
        if found is None:
            done.append((current, power))
            continue
        others = _product(outside, done + pending)
        for text, plain, latex in found.working:
            steps.show_text(text, *_framed(others, plain, latex, power))
        new = [(factor, count * power) for factor, count in found.factors]
        pending = new + pending
        steps.show(found.text, _product(outside, done + pending))
    return _product(outside, done + pending)


def common_factor(polynomial: sp.Expr) -> tuple[sp.Expr, sp.Expr]:
    """``6x^2 + 9x`` -> ``(3x, 2x + 3)``; a negative first term gives a negative factor."""
    terms = polynomial.as_ordered_terms()
    if len(terms) < 2:
        return sp.Integer(1), polynomial
    coefficients = [term.as_coeff_Mul()[0] for term in terms]
    if all(coefficient.is_Rational for coefficient in coefficients):
        numerator = math.gcd(*[int(coefficient.p) for coefficient in coefficients])
        denominator = math.lcm(*[int(coefficient.q) for coefficient in coefficients])
        number = sp.Rational(numerator, denominator)
    else:
        number = sp.Integer(1)
    letters = sp.Integer(1)
    symbols = sorted(polynomial.free_symbols, key=lambda symbol: symbol.name)
    for symbol in symbols:
        lowest = min(sp.degree(term, symbol) for term in terms)
        letters *= symbol**lowest
    outside = number * letters
    # the sign of the highest power, not of whichever term happens to print first
    if symbols and sp.Poly(polynomial, *symbols).LC() < 0:
        outside = -outside
    return outside, _expanded(polynomial / outside)


def factor_once(polynomial: sp.Expr) -> Found | None:
    """One factoring move on ``polynomial``, or None if it does not factor."""
    symbols = sorted(polynomial.free_symbols, key=lambda symbol: symbol.name)
    if not symbols:
        return None
    terms = polynomial.as_ordered_terms()
    found = None
    if len(terms) == 2:
        found = _difference_of_squares(terms) or _cubes(terms)
    elif len(terms) == 3:
        found = _perfect_square(terms) or _trinomial(polynomial, symbols)
    elif len(terms) == 4:
        found = _grouping(terms)
    if found is None and len(symbols) == 1 and sp.degree(polynomial, symbols[0]) >= 3:
        found = _rational_root(polynomial, symbols[0])
    return found or _computer(polynomial)


def _expanded(expression: sp.Expr) -> sp.Expr:
    """Multiplied out, even while the display keeps ``2(x + 1)`` as it is."""
    with distribute(True):
        return sp.expand(expression)


# --- two terms ------------------------------------------------------------------------


def root_of(term: sp.Expr, degree: int) -> sp.Expr | None:
    """The exact ``degree``-th root of a monomial such as ``9x^2``, or None."""
    coefficient, rest = term.as_coeff_Mul()
    if not coefficient.is_Rational or coefficient <= 0:
        return None
    root = sp.root(coefficient, degree)
    if not root.is_Rational:
        return None
    result = root
    for base, exponent in rest.as_powers_dict().items():
        if base == 1:
            continue
        if not base.is_Symbol or not exponent.is_Integer or exponent % degree:
            return None
        result *= base ** (exponent // degree)
    return result


def _difference_of_squares(terms: list[sp.Expr]) -> Found | None:
    positive = [term for term in terms if not term.could_extract_minus_sign()]
    negative = [term for term in terms if term.could_extract_minus_sign()]
    if len(positive) != 1 or len(negative) != 1:
        return None
    a, b = root_of(positive[0], 2), root_of(-negative[0], 2)
    if a is None or b is None:
        return None
    return Found(
        [(a - b, 1), (a + b, 1)],
        f"Difference of squares: a^2 - b^2 = (a - b)(a + b), with a = {show(a)} and b = {show(b)}",
    )


def _cubes(terms: list[sp.Expr]) -> Found | None:
    first, second = terms
    a = root_of(first, 3)
    if a is None:
        return None
    if second.could_extract_minus_sign():
        b = root_of(-second, 3)
        if b is None:
            return None
        return Found(
            [(a - b, 1), (_expanded(a**2 + a * b + b**2), 1)],
            "Difference of cubes: a^3 - b^3 = (a - b)(a^2 + ab + b^2), "
            f"with a = {show(a)} and b = {show(b)}",
        )
    b = root_of(second, 3)
    if b is None:
        return None
    return Found(
        [(a + b, 1), (_expanded(a**2 - a * b + b**2), 1)],
        f"Sum of cubes: a^3 + b^3 = (a + b)(a^2 - ab + b^2), with a = {show(a)} and b = {show(b)}",
    )


# --- three terms ----------------------------------------------------------------------


def _perfect_square(terms: list[sp.Expr]) -> Found | None:
    first, middle, last = terms
    a, b = root_of(first, 2), root_of(last, 2)
    if a is None or b is None:
        return None
    if _expanded(2 * a * b - middle) == 0:
        return Found(
            [(a + b, 2)],
            f"Perfect square: a^2 + 2ab + b^2 = (a + b)^2, with a = {show(a)} and b = {show(b)}",
        )
    if _expanded(2 * a * b + middle) == 0:
        return Found(
            [(a - b, 2)],
            f"Perfect square: a^2 - 2ab + b^2 = (a - b)^2, with a = {show(a)} and b = {show(b)}",
        )
    return None


def _trinomial(polynomial: sp.Expr, symbols: list[sp.Symbol]) -> Found | None:
    """``a u^2 + b u + c`` with whole numbers, where u is x, or x^k, or x/y when homogeneous."""
    if len(symbols) != 1:
        return _homogeneous(polynomial, symbols)
    x = symbols[0]
    poly = sp.Poly(polynomial, x)
    degrees = sorted((monomial[0] for monomial in poly.monoms()), reverse=True)
    if len(degrees) != 3 or degrees[2] != 0 or degrees[0] != 2 * degrees[1]:
        return None
    step = degrees[1]
    u = x**step
    a, b, c = (poly.coeff_monomial(x ** (step * power)) for power in (2, 1, 0))
    if not all(coefficient.is_Integer for coefficient in (a, b, c)):
        return None
    pair = two_numbers(int(a * c), int(b))
    if pair is None:
        return None
    m, n = pair
    disguise = f"This is a quadratic in {show(u)}. " if step > 1 else ""
    if a == 1:
        return Found(
            [(u + m, 1), (u + n, 1)],
            f"{disguise}Find two numbers that multiply to {c} and add to {b}: {m} and {n}",
        )
    return _split_middle(a, b, c, m, n, u, disguise)


def _homogeneous(polynomial: sp.Expr, symbols: list[sp.Symbol]) -> Found | None:
    """``x^2 + 5xy + 6y^2`` factors like ``x^2 + 5x + 6``, with y alongside every number."""
    if len(symbols) != 2:
        return None
    x, y = symbols
    poly = sp.Poly(polynomial, x, y)
    if not poly.is_homogeneous or poly.total_degree() != 2:
        return None
    a, b, c = (poly.coeff_monomial(x ** (2 - power) * y**power) for power in (0, 1, 2))
    if a != 1 or not all(coefficient.is_Integer for coefficient in (b, c)):
        return None
    pair = two_numbers(int(c), int(b))
    if pair is None:
        return None
    m, n = pair
    return Found(
        [(x + m * y, 1), (x + n * y, 1)],
        f"Find two terms that multiply to {show(c * y**2)} and add to {show(b * y)}: "
        f"{show(m * y)} and {show(n * y)}",
    )


def two_numbers(product: int, total: int) -> tuple[int, int] | None:
    """Two whole numbers with this product and this sum, smallest first."""
    if product == 0:
        return tuple(sorted((0, total)))  # type: ignore[return-value]
    if abs(product) > MAX_CANDIDATES:
        return None
    for divisor in sp.divisors(abs(product)):
        for first in (divisor, -divisor):
            second = product // first
            if first + second == total:
                return (min(first, second), max(first, second))
    return None


def _split_middle(a, b, c, m, n, u, disguise: str) -> Found:
    split = sp.Add(a * u**2, m * u, n * u, c, evaluate=False)
    first_factor = math.gcd(int(a), int(m)) * u
    first_inner = _expanded((a * u**2 + m * u) / first_factor)
    second_factor = sp.Integer(math.gcd(int(n), int(c)))
    second_inner = _expanded((n * u + c) / second_factor)
    if _expanded(second_inner + first_inner) == 0:
        second_factor, second_inner = -second_factor, _expanded(-second_inner)
    grouped = _pairs([(first_factor, first_inner), (second_factor, second_inner)])
    return Found(
        [(first_inner, 1), (first_factor + second_factor, 1)],
        f"Take out the common bracket {show(first_inner)}",
        [
            (
                f"{disguise}Find two numbers that multiply to a*c = {a * c} and add to "
                f"b = {b}: {m} and {n}. Split the middle term with them",
                read_as(split),
                latex_of(split),
            ),
            ("Take out the common factor of each pair", *grouped),
        ],
    )


# --- four terms -----------------------------------------------------------------------


def _grouping(terms: list[sp.Expr]) -> Found | None:
    for pairs in (((0, 1), (2, 3)), ((0, 2), (1, 3))):
        first = sp.Add(*[terms[index] for index in pairs[0]])
        second = sp.Add(*[terms[index] for index in pairs[1]])
        first_factor, first_inner = common_factor(first)
        second_factor, second_inner = common_factor(second)
        if _expanded(second_inner + first_inner) == 0:
            second_factor, second_inner = -second_factor, _expanded(-second_inner)
        if _expanded(second_inner - first_inner) != 0:
            continue
        grouped_plain = f"({read_as(first)}) + ({read_as(second)})"
        grouped_latex = rf"\left({latex_of(first)}\right) + \left({latex_of(second)}\right)"
        pulled = _pairs([(first_factor, first_inner), (second_factor, second_inner)])
        return Found(
            [(first_inner, 1), (first_factor + second_factor, 1)],
            f"Take out the common bracket {show(first_inner)}",
            [
                ("Group the terms in pairs", grouped_plain, grouped_latex),
                ("Take out the common factor of each pair", *pulled),
            ],
        )
    return None


# --- higher powers --------------------------------------------------------------------


def _rational_root(polynomial: sp.Expr, x: sp.Symbol) -> Found | None:
    poly = sp.Poly(polynomial, x)
    coefficients = poly.all_coeffs()
    if not all(coefficient.is_Integer for coefficient in coefficients):
        return None
    lead, constant = int(coefficients[0]), int(coefficients[-1])
    if constant == 0 or max(abs(lead), abs(constant)) > MAX_CANDIDATES:
        return None
    candidates = sorted(
        {
            sign * sp.Rational(p, q)
            for p in sp.divisors(abs(constant))
            for q in sp.divisors(abs(lead))
            for sign in (1, -1)
        },
        key=lambda value: (abs(value), bool(value.is_negative)),
    )
    for root in candidates:
        if poly.eval(root) == 0:
            linear = root.q * x - root.p
            quotient = sp.quo(poly, sp.Poly(linear, x)).as_expr()
            return Found(
                [(linear, 1), (quotient, 1)],
                f"{x} = {show(root)} makes it 0, so {show(linear)} is a factor "
                f"(the factor theorem). Divide it out",
            )
    return None


def _computer(polynomial: sp.Expr) -> Found | None:
    _, factors = sp.factor_list(polynomial)
    if sum(count for _, count in factors) < 2:
        return None
    return Found([(factor, count) for factor, count in factors], "Factor (computer algebra)")


def _pairs(parts: list[tuple[sp.Expr, sp.Expr]]) -> tuple[str, str]:
    """``2x(x + 1) + 3(x + 1)``, written out so SymPy cannot tidy the brackets away."""
    plain, latex = "", ""
    for index, (factor, bracket) in enumerate(parts):
        negative = factor.could_extract_minus_sign()
        size = -factor if negative else factor
        if size == 1:
            body_plain = f"({read_as(bracket)})"
            body_latex = rf"\left({latex_of(bracket)}\right)"
        else:
            body_plain = f"{read_as(size)}*({read_as(bracket)})"
            body_latex = rf"{latex_of(size)} \left({latex_of(bracket)}\right)"
        signs = ("-", "") if index == 0 else (" - ", " + ")
        sign = signs[0] if negative else signs[1]
        plain += sign + body_plain
        latex += sign + body_latex
    return plain, latex


# --- display --------------------------------------------------------------------------


def _product(outside: sp.Expr, factors: list[tuple[sp.Expr, int]]) -> sp.Expr:
    return outside * sp.Mul(*[factor**count for factor, count in factors])


def _framed(others: sp.Expr, plain: str, latex: str, power: int) -> tuple[str, str]:
    """The working on one factor, with the factors around it."""
    if power != 1:
        plain, latex = f"({plain})^{power}", rf"\left({latex}\right)^{{{power}}}"
    if others == 1:
        return plain, latex
    if others == -1:
        return f"-({plain})", rf"-\left({latex}\right)"
    return f"{read_as(others)}*({plain})", rf"{latex_of(others)} \left({latex}\right)"
