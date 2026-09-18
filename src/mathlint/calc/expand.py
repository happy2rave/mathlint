"""Expanding: multiply out every bracket, then collect like terms.

One kind of bracket is opened per step, the way it is done by hand: the special
products first (``(a + b)^2``, ``(a + b)(a - b)``, ``(a + b)^3``), then a number
or a letter in front of a bracket, then two brackets multiplied together.
"""

from __future__ import annotations

import sympy as sp

from .expression import Steps, method, show, sum_of, terms_of

MAX_ROUNDS = 30

SQUARE_PLUS = "Use (a + b)^2 = a^2 + 2ab + b^2"
SQUARE_MINUS = "Use (a - b)^2 = a^2 - 2ab + b^2"
CUBE_PLUS = "Use (a + b)^3 = a^3 + 3a^2 b + 3a b^2 + b^3"
CUBE_MINUS = "Use (a - b)^3 = a^3 - 3a^2 b + 3a b^2 - b^3"
CONJUGATES = "Use (a + b)(a - b) = a^2 - b^2"
TWO_BRACKETS = "Multiply every term in the first bracket by every term in the second"
MINUS_SIGN = "A minus sign in front of a bracket changes the sign of every term inside"


def has_brackets(expression: sp.Expr) -> bool:
    return any(_open_term(term) is not None for term in terms_of(expression))


@method("expand", applies=has_brackets)
def expand_steps(expression: sp.Expr, steps: Steps) -> sp.Expr:
    terms = terms_of(expression)
    for _ in range(MAX_ROUNDS):
        collected = [_collect_inside(term) for term in terms]
        if any(term is not None for term in collected):
            terms = [
                new if new is not None else old for new, old in zip(collected, terms, strict=True)
            ]
            steps.show("Collect like terms inside the brackets", sum_of(terms))
            continue
        opened: list[sp.Expr] = []
        texts: list[str] = []
        for term in terms:
            result = _open_term(term)
            if result is None:
                opened.append(term)
                continue
            pieces, text = result
            opened.extend(pieces)
            if text not in texts:
                texts.append(text)
        if not texts:
            break
        terms = opened
        steps.show(texts[0] if len(texts) == 1 else "Multiply out the brackets", sum_of(terms))
    result = sp.expand(expression)
    if len(terms_of(result)) < len(terms) or show(result) != show(sum_of(terms)):
        steps.show("Collect like terms", result)
    return result


def _open_term(term: sp.Expr) -> tuple[list[sp.Expr], str] | None:
    """Open one bracket (or one pair of brackets) in ``term``."""
    coefficient, factors = term.as_coeff_mul()
    factors = list(factors)
    brackets = [index for index, factor in enumerate(factors) if _is_bracket(factor)]
    if not brackets:
        return None

    def rest_without(*indices: int) -> sp.Expr:
        return coefficient * sp.Mul(
            *[factor for index, factor in enumerate(factors) if index not in indices]
        )

    # a special product first
    for index in brackets:
        factor = factors[index]
        if isinstance(factor, sp.Pow) and len(factor.base.args) == 2 and factor.exp in (2, 3):
            first, second = _ordered(factor.base)
            rest = rest_without(index)
            if factor.exp == 2:
                pieces = [first**2, 2 * first * second, second**2]
                text = SQUARE_MINUS if second.could_extract_minus_sign() else SQUARE_PLUS
            else:
                pieces = [first**3, 3 * first**2 * second, 3 * first * second**2, second**3]
                text = CUBE_MINUS if second.could_extract_minus_sign() else CUBE_PLUS
            return _times(rest, pieces), text
    sums = [index for index in brackets if isinstance(factors[index], sp.Add)]
    for position, left in enumerate(sums):
        for right in sums[position + 1 :]:
            pair = _conjugates(factors[left], factors[right])
            if pair is not None:
                first, second = pair
                rest = rest_without(left, right)
                return _times(rest, [first**2, -(second**2)]), CONJUGATES

    if len(sums) >= 2:
        left, right = sums[0], sums[1]
        rest = rest_without(left, right)
        pieces = [a * b for a in _ordered(factors[left]) for b in _ordered(factors[right])]
        return _times(rest, pieces), TWO_BRACKETS
    if sums:
        index = sums[0]
        rest = rest_without(index)
        pieces = [rest * piece for piece in _ordered(factors[index])]
        if rest == -1:
            return pieces, MINUS_SIGN
        return pieces, f"Multiply each term in the bracket by {show(rest)}"
    # a power of a bracket with no formula: take one copy out and multiply it in
    index = brackets[0]
    power = factors[index]
    outside = rest_without(index)
    terms = _ordered(power.base)
    if power.exp == 2:  # three or more terms, squared
        return _times(outside, [a * b for a in terms for b in terms]), TWO_BRACKETS
    lower = power.base ** (power.exp - 1)
    text = f"Write {show(power)} as ({show(power.base)}) * {show(lower)}, then multiply out"
    return [outside * lower * piece for piece in terms], text


def _times(rest: sp.Expr, pieces: list[sp.Expr]) -> list[sp.Expr]:
    """The multiplied-out pieces, still in a bracket when something stands in front."""
    if rest == 1:
        return pieces
    return [rest * sp.Add(*pieces, evaluate=False)]


def _collect_inside(term: sp.Expr) -> sp.Expr | None:
    """``2(x^2 + x + 2x + 2)`` -> ``2(x^2 + 3x + 2)``, or None when there is nothing to collect."""
    replacements = {}
    for node in sp.preorder_traversal(term):
        if isinstance(node, sp.Add) and node is not term:
            tidy = sp.Add(*node.args)
            if len(sp.Add.make_args(tidy)) < len(node.args):
                replacements[node] = tidy
    return term.xreplace(replacements) if replacements else None


def _is_bracket(factor: sp.Expr) -> bool:
    if isinstance(factor, sp.Add):
        return True
    return (
        isinstance(factor, sp.Pow)
        and isinstance(factor.base, sp.Add)
        and factor.exp.is_Integer
        and factor.exp >= 2
    )


def _ordered(bracket: sp.Expr) -> list[sp.Expr]:
    """The terms of a bracket in the order they are printed."""
    return list(bracket.as_ordered_terms())


def _conjugates(left: sp.Expr, right: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """``(a + b)`` and ``(a - b)`` give ``(a, b)``."""
    if len(left.args) != 2 or len(right.args) != 2:
        return None
    for a in left.args:
        if a in right.args:
            b = next(term for term in left.args if term != a)
            other = next(term for term in right.args if term != a)
            if other == -b:
                return a, b
    return None
