"""The pieces every solver shares: an equation, a result, and a way to write steps."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..parse.plain import read_as
from ..steps.solution import Solution


@dataclass
class Equation:
    """``lhs = rhs``."""

    lhs: sp.Expr
    rhs: sp.Expr

    @property
    def expr(self) -> sp.Expr:
        return self.lhs - self.rhs

    def display(self) -> sp.Equality:
        return sp.Eq(self.lhs, self.rhs, evaluate=False)

    def swapped(self) -> Equation:
        return Equation(self.rhs, self.lhs)


@dataclass
class Outcome:
    """What a solver found: some values, every real number, or nothing.

    ``solution_set`` holds an answer that is not a finite list, such as the
    general solution of a trigonometric equation.
    """

    values: list[sp.Expr] = field(default_factory=list)
    everything: bool = False
    solution_set: sp.Set | None = None

    @classmethod
    def of(cls, values) -> Outcome:
        return cls(values=[sp.sympify(value) for value in values])

    @classmethod
    def none(cls) -> Outcome:
        return cls()

    @classmethod
    def all(cls) -> Outcome:
        return cls(everything=True)

    @classmethod
    def as_set(cls, solution_set: sp.Set) -> Outcome:
        return cls(solution_set=solution_set)

    def merge(self, other: Outcome) -> Outcome:
        if self.everything or other.everything:
            return Outcome.all()
        return Outcome.of(self.values + other.values)


class Work:
    """Writes the steps of solving an equation into a :class:`Solution`."""

    def __init__(self, solution: Solution, variable: sp.Symbol) -> None:
        self.solution = solution
        self.variable = variable

    def equation(self, text: str, equation: Equation, operation: str = "") -> None:
        self.solution.add(text, operation=operation, expression=equation.display())

    def note(self, text: str, expression: sp.Expr | None = None) -> None:
        self.solution.add(text, expression=expression)

    def show(self, text: str, display: str, display_latex: str) -> None:
        self.solution.add(text)
        step = self.solution.steps[-1]
        step.display = display
        step.display_latex = display_latex

    def alternatives(self, text: str, equations: list[Equation]) -> None:
        """A step that branches: ``x - 2 = 0  or  x - 3 = 0``."""
        self.show(
            text,
            " or ".join(f"{read_as(eq.lhs)} = {read_as(eq.rhs)}" for eq in equations),
            r" \quad\text{or}\quad ".join(
                f"{sp.latex(eq.lhs)} = {sp.latex(eq.rhs)}" for eq in equations
            ),
        )


def show(value: sp.Expr) -> str:
    return read_as(value)


def answer_text(variable: sp.Symbol, outcome: Outcome) -> str:
    if outcome.everything:
        return "every real number is a solution"
    if outcome.solution_set is not None:
        return f"{variable} in {sp.sstr(outcome.solution_set)}"
    if not outcome.values:
        return "no real solution"
    return " or ".join(f"{variable} = {show(value)}" for value in outcome.values)


def answer_latex(variable: sp.Symbol, outcome: Outcome) -> str:
    if outcome.everything:
        return rf"{sp.latex(variable)} \in \mathbb{{R}}"
    if outcome.solution_set is not None:
        return rf"{sp.latex(variable)} \in {sp.latex(outcome.solution_set)}"
    if not outcome.values:
        return r"\text{no real solution}"
    return r" \quad\text{or}\quad ".join(
        f"{sp.latex(variable)} = {sp.latex(value)}" for value in outcome.values
    )


def sort_values(values: list[sp.Expr]) -> list[sp.Expr]:
    """Distinct values, smallest first."""
    distinct: list[sp.Expr] = []
    for value in values:
        if not any(sp.simplify(value - other) == 0 for other in distinct):
            distinct.append(value)
    try:
        return sorted(distinct, key=lambda value: float(sp.N(value)))
    except TypeError:
        return distinct
