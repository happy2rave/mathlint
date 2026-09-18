"""Send an equation to the solver for its kind.

Solvers register themselves here. They call :func:`solve_equation` again for the
equation they reduce to — a rational equation becomes a polynomial one, a radical
equation becomes the squared equation — so each method is written once.
"""

from __future__ import annotations

from collections.abc import Callable

import sympy as sp

from .classify import classify
from .core import Equation, Outcome, Work

Solver = Callable[[Equation, sp.Symbol, Work, "str | None", int], Outcome]
MethodChooser = Callable[[Equation, sp.Symbol], list[str]]

MAX_DEPTH = 6

SOLVERS: dict[str, Solver] = {}
METHODS: dict[str, MethodChooser] = {}

#: What the method switcher calls each method.
METHOD_LABELS = {
    "balance": "Balance both sides",
    "factoring": "Factoring",
    "formula": "Quadratic formula",
    "completing-square": "Completing the square",
    "square-root": "Square roots",
    "roots": "Factor theorem",
    "denominators": "Clear the denominators",
    "isolate-and-square": "Isolate and square",
    "cases": "Split into cases",
    "same-base": "Same base",
    "logarithms": "Take logarithms",
    "combine-logs": "Combine the logarithms",
    "sympy": "Computer algebra",
}


def register(kind: str, methods: MethodChooser | None = None):
    """Decorator: make ``function`` the solver for ``kind``."""

    def decorator(function: Solver) -> Solver:
        SOLVERS[kind] = function
        if methods is not None:
            METHODS[kind] = methods
        return function

    return decorator


def methods_for(kind: str, equation: Equation, variable: sp.Symbol) -> list[str]:
    """The methods that apply, the default first."""
    chooser = METHODS.get(kind)
    return chooser(equation, variable) if chooser else ["sympy"]


def solve_equation(
    equation: Equation,
    variable: sp.Symbol,
    work: Work,
    method: str | None = None,
    depth: int = 0,
) -> Outcome:
    kind = classify(equation, variable) if depth <= MAX_DEPTH else "other"
    solver = SOLVERS.get(kind) or SOLVERS["other"]
    return solver(equation, variable, work, method, depth)
