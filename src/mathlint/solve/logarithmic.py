"""Logarithmic equations.

A logarithm is only defined for positive numbers, so that goes down first. Then:
one logarithm is isolated and undone (``ln(u) = k`` means ``u = e^k``); several
are combined with ``ln a + ln b = ln(ab)`` until one is left on each side, and
``ln(u) = ln(v)`` means ``u = v``. The check at the end drops any answer outside
the domain, with the reason.
"""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from ..parse.plain import latex_of
from . import dispatch
from .core import Equation, Outcome, Work, show
from .dispatch import register
from .isolate import already_isolated, isolate


def _logs(expr: sp.Expr, variable: sp.Symbol) -> list[sp.log]:
    return sorted(
        {node for node in expr.atoms(sp.log) if node.has(variable)}, key=sp.default_sort_key
    )


@register("logarithmic", methods=lambda equation, variable: ["combine-logs"])
def solve_logarithmic(
    equation: Equation, variable: sp.Symbol, work: Work, method: str | None, depth: int
) -> Outcome:
    logs = _logs(equation.expr, variable)
    arguments = [log.args[0] for log in logs]
    work.show(
        msg("A logarithm is only defined for positive numbers, so"),
        ", ".join(f"{show(argument)} > 0" for argument in arguments),
        r",\quad ".join(f"{latex_of(argument)} > 0" for argument in arguments),
    )

    current = equation
    if len(logs) > 1:
        combined = Equation(
            sp.logcombine(equation.lhs, force=True), sp.logcombine(equation.rhs, force=True)
        )
        if (combined.lhs, combined.rhs) != (equation.lhs, equation.rhs):
            work.equation(
                msg("Combine the logarithms: ln a + ln b = ln(ab), ln a - ln b = ln(a/b)"),
                combined,
            )
            current = combined

    if isinstance(current.lhs, sp.log) and isinstance(current.rhs, sp.log):
        inside = Equation(current.lhs.args[0], current.rhs.args[0])
        work.equation(msg("Equal logarithms have equal insides: ln(u) = ln(v) means u = v"), inside)
        return dispatch.solve_equation(inside, variable, work, depth=depth + 1)

    remaining = _logs(current.expr, variable)
    if len(remaining) == 1:
        log = remaining[0]
        isolated = isolate(current, log)
        if isolated is not None and not isolated.rhs.has(variable):
            if not already_isolated(current, log):
                work.equation(msg("Isolate the logarithm on one side"), isolated)
            undone = Equation(log.args[0], sp.exp(isolated.rhs))
            work.equation(msg("Undo the logarithm: ln(u) = k means u = e^k"), undone)
            return dispatch.solve_equation(undone, variable, work, depth=depth + 1)

    return dispatch.SOLVERS["other"](current, variable, work, None, depth)
