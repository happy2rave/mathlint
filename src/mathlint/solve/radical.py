"""Radical equations: isolate the root, raise both sides to its power, check.

Squaring is not reversible — ``x = -3`` and ``x = 3`` square to the same thing —
so it can add answers that do not solve the original equation. That is fine as
long as every answer is checked at the end, and the check says why a rejected one
fails. Two roots take two rounds.
"""

from __future__ import annotations

import sympy as sp

from . import dispatch
from .classify import has_radical
from .core import Equation, Outcome, Work, show
from .dispatch import register
from .isolate import already_isolated, isolate

_ROUNDS = 3
_POWER_WORDS = {2: "Square", 3: "Cube"}


@register("radical", methods=lambda equation, variable: ["isolate-and-square"])
def solve_radical(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    current = equation
    for _ in range(_ROUNDS):
        radicals = sorted(
            (
                node
                for node in current.expr.atoms(sp.Pow)
                if node.base.has(variable) and node.exp.is_Rational and not node.exp.is_Integer
            ),
            key=sp.default_sort_key,
        )
        if not radicals:
            break
        root = radicals[0]
        isolated = isolate(current, root)
        if isolated is None:
            return dispatch.SOLVERS["other"](current, variable, work, None, depth)
        if not already_isolated(current, root):
            work.equation("Isolate the root on one side", isolated)

        index = int(root.exp.q)
        value = isolated.rhs
        if index % 2 == 0 and value.is_number and value.is_negative:
            work.note(
                f"A square root is never negative, but here it would equal {show(value)}, "
                "so there is no solution"
            )
            return Outcome.none()

        current = Equation(
            sp.expand(root.base ** root.exp.p), sp.expand(value**index)
        )
        action = (
            f"{_POWER_WORDS[index]} both sides"
            if index in _POWER_WORDS
            else f"Raise both sides to the power {index}"
        )
        text = (
            f"{action} (this can add answers that do not work, "
            "so every answer is checked at the end)"
        )
        work.equation(text, current, operation=f"^{index}")

    if has_radical(current.expr, variable):
        return dispatch.SOLVERS["other"](current, variable, work, None, depth)
    return dispatch.solve_equation(current, variable, work, depth=depth + 1)
