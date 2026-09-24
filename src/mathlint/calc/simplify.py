"""Simplifying: the rules a student knows, one at a time, then SymPy if needed.

Algebraic fractions get the full treatment — a common denominator, the
numerators added, the top and bottom factored, the common factors cancelled —
together with the values of the letter the answer must not take, because
cancelling ``(x + 2)`` hides that ``x = -2`` was never allowed.
"""

from __future__ import annotations

from functools import reduce

import sympy as sp
from sympy.core.parameters import distribute

from ..i18n import msg
from ..parse.plain import latex_of, read_as
from .expand import expand_steps, has_brackets
from .expression import Steps, method, show

#: rewrites that only ever apply one rule, tried in this order
RULES = [
    (
        msg(
            "Combine the logarithms: ln(a) + ln(b) = ln(ab), ln(a) - "
            "ln(b) = ln(a/b), k ln(a) = ln(a^k)"
        ),
        lambda expression: expression.has(sp.log),
        lambda expression: sp.logcombine(expression, force=True),
    ),
    (
        msg("Use the exponent rules: a^m a^n = a^(m+n), (a^m)^n = a^(mn)"),
        lambda expression: expression.has(sp.Pow) or expression.has(sp.exp),
        lambda expression: sp.powsimp(expression),
    ),
    (
        msg("Use the trigonometric identities, such as sin^2 x + cos^2 x = 1"),
        lambda expression: expression.has(sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc),
        sp.trigsimp,
    ),
    (
        msg("Rationalise the denominator"),
        lambda expression: _has_root(sp.denom(expression)),
        sp.radsimp,
    ),
]


@method("simplify", applies=lambda expression: True)
def simplify_steps(expression: sp.Expr, steps: Steps) -> sp.Expr:
    current = expression
    if _denominators(current):
        current = _fractions(current, steps)
    elif has_brackets(current) and _shorter(_expanded(current), current):
        current = expand_steps(current, steps)
    for text, applies, rewrite in RULES:
        if not applies(current):
            continue
        with distribute(True):
            rewritten = rewrite(current)
        if _changed(rewritten, current) and _shorter(rewritten, current, strictly=False):
            steps.show(text, rewritten)
            current = rewritten
    with distribute(True):
        final = sp.simplify(current)
    if _changed(final, current) and _shorter(final, current, strictly=True):
        steps.show(msg("Simplify"), final)
        current = final
    return current


# --- algebraic fractions -----------------------------------------------------------------


def _fractions(expression: sp.Expr, steps: Steps) -> sp.Expr:
    excluded = _excluded_values(expression)
    terms = expression.as_ordered_terms()
    if len(terms) > 1:
        top, bottom = _common_denominator(terms, steps)
    else:
        top, bottom = sp.fraction(sp.together(expression))
    with distribute(True):
        factored_top, factored_bottom = sp.factor(top), sp.factor(bottom)
        common = sp.gcd(top, bottom)
    if _changed(factored_top, top) or _changed(factored_bottom, bottom):
        steps.show_text(
            msg("Factor the numerator and the denominator"),
            *fraction_text(factored_top, factored_bottom),
        )
    result = _quotient(factored_top, factored_bottom)
    if common.free_symbols:
        with distribute(True):
            result = sp.factor(sp.cancel(top / bottom))
        steps.show(msg("Cancel the common factor {factor}", factor=show(sp.factor(common))), result)
    remaining = _excluded_values(result)
    for symbol, values in excluded.items():
        lost = [value for value in values if value not in remaining.get(symbol, [])]
        if lost:
            steps.condition(", ".join(f"{symbol} != {show(value)}" for value in lost))
    if steps.computation.conditions:
        steps.note(
            msg(
                "The original is not defined for {values}, so the answer keeps that condition",
                values=", ".join(steps.computation.conditions).replace("!=", "="),
            )
        )
    return result


def _common_denominator(terms, steps: Steps) -> tuple[sp.Expr, sp.Expr]:
    parts = [sp.fraction(term) for term in terms]
    with distribute(True):
        bottom = sp.factor(reduce(sp.lcm, [denominator for _, denominator in parts]))
        scaled = [
            (numerator, sp.factor(sp.cancel(bottom / denominator)))
            for numerator, denominator in parts
        ]
    pieces = [numerator * multiplier for numerator, multiplier in scaled]
    same_bottom = all(multiplier == 1 for _, multiplier in scaled)
    plain, latex = [], []
    for index, piece in enumerate(pieces):
        negative = piece.could_extract_minus_sign()
        shown = -piece if negative else piece
        top_plain, top_latex = fraction_text(shown, bottom)
        sign = ("-" if negative else "") if index == 0 else (" - " if negative else " + ")
        plain.append(sign + top_plain)
        latex.append(sign + top_latex)
    if not same_bottom:
        steps.show_text(
            msg("Write every fraction over the common denominator {bottom}", bottom=show(bottom)),
            "".join(plain),
            "".join(latex),
        )
    # a bracket that was only there to multiply by keeps no brackets in the sum
    flat = [part for piece in pieces for part in sp.Add.make_args(piece)]
    added = sp.Add(*flat, evaluate=False)
    text = (
        msg("The denominators are the same, so add the numerators")
        if same_bottom
        else (msg("Add the numerators"))
    )
    steps.show_text(text, *fraction_text(added, bottom))
    with distribute(True):
        top = sp.expand(sp.Add(*pieces))
    if _changed(top, added):
        steps.show_text(
            msg("Multiply out the numerator and collect like terms"), *fraction_text(top, bottom)
        )
    return top, bottom


def _denominators(expression: sp.Expr) -> list[sp.Expr]:
    """Every expression with a letter that the input divides by."""
    found = []
    for node in sp.preorder_traversal(expression):
        if (
            isinstance(node, sp.Pow)
            and node.exp.is_negative
            and node.base.free_symbols
            and node.base not in found
        ):
            found.append(node.base)
    return found


def _excluded_values(expression: sp.Expr) -> dict[sp.Symbol, list[sp.Expr]]:
    """The real values that make a denominator zero, by letter (one-letter denominators only)."""
    excluded: dict[sp.Symbol, list[sp.Expr]] = {}
    for denominator in _denominators(expression):
        symbols = list(denominator.free_symbols)
        if len(symbols) != 1:
            continue
        roots = sp.solveset(denominator, symbols[0], domain=sp.S.Reals)
        if not isinstance(roots, sp.FiniteSet):
            continue
        values = excluded.setdefault(symbols[0], [])
        values.extend(value for value in sorted(roots, key=float) if value not in values)
    return excluded


def fraction_text(top: sp.Expr, bottom: sp.Expr) -> tuple[str, str]:
    top_plain, bottom_plain = read_as(top), read_as(bottom)
    if isinstance(top, sp.Add) or top.could_extract_minus_sign():
        top_plain = f"({top_plain})"
    if not (bottom.is_Symbol or bottom.is_Number or isinstance(bottom, sp.Pow | sp.Function)):
        bottom_plain = f"({bottom_plain})"
    return f"{top_plain}/{bottom_plain}", rf"\frac{{{latex_of(top)}}}{{{latex_of(bottom)}}}"


def _quotient(top: sp.Expr, bottom: sp.Expr) -> sp.Expr:
    return top * sp.Pow(bottom, -1)


# --- helpers ------------------------------------------------------------------------


def _expanded(expression: sp.Expr) -> sp.Expr:
    with distribute(True):
        return sp.expand(expression)


def _changed(new: sp.Expr, old: sp.Expr) -> bool:
    return read_as(new) != read_as(old)


def _shorter(new: sp.Expr, old: sp.Expr, strictly: bool = False) -> bool:
    new_size, old_size = sp.count_ops(new), sp.count_ops(old)
    return new_size < old_size if strictly else new_size <= old_size


def _has_root(expression: sp.Expr) -> bool:
    return any(
        isinstance(node, sp.Pow) and node.exp.is_Rational and not node.exp.is_Integer
        for node in sp.preorder_traversal(expression)
    )
