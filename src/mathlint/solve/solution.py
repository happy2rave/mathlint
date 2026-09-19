"""The result of solving an equation: the worked steps plus the answers."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..calc.computation import approximate
from ..parse.plain import latex_of
from ..steps.solution import Solution
from .core import Outcome, answer_latex, answer_text, show
from .dispatch import METHOD_LABELS

KIND_LABELS = {
    "linear": "Linear equation",
    "quadratic": "Quadratic equation",
    "polynomial": "Polynomial equation",
    "rational": "Rational equation",
    "radical": "Equation with roots",
    "absolute": "Absolute-value equation",
    "exponential": "Exponential equation",
    "logarithmic": "Logarithmic equation",
    "other": "Equation",
}


@dataclass
class EquationSolution(Solution):
    kind: str = ""
    method: str = ""
    methods: list[str] = field(default_factory=list)
    variable: sp.Symbol | None = None
    answers: list[sp.Expr] = field(default_factory=list)
    everything: bool = False
    solution_set: sp.Set | None = None
    answer_latex: str = ""
    letters: list[str] = field(default_factory=list)
    #: each answer as a decimal, or None where the exact answer already is one
    answers_decimal: list[str | None] = field(default_factory=list)
    decimal: str | None = None
    decimal_latex: str | None = None

    def finish(self, outcome: Outcome) -> None:
        assert self.variable is not None
        self.answers = list(outcome.values)
        self.everything = outcome.everything
        self.solution_set = outcome.solution_set
        self.summary = answer_text(self.variable, outcome)
        self.answer_latex = answer_latex(self.variable, outcome)
        self._decimals()
        if outcome.everything:
            self.result = sp.S.Reals
        elif outcome.solution_set is not None:
            self.result = outcome.solution_set
        else:
            self.result = sp.FiniteSet(*self.answers)

    def _decimals(self) -> None:
        """``x = (1 + sqrt(5))/2`` is also about 1.618 — say so when it helps."""
        if self.everything or self.solution_set is not None or not self.answers:
            return
        pairs = [approximate(value, show(value)) for value in self.answers]
        self.answers_decimal = [text for text, _ in pairs]
        if not any(self.answers_decimal):
            return
        plain, latex = [], []
        for value, (text, number) in zip(self.answers, pairs, strict=True):
            if text is None:
                plain.append(f"{self.variable} = {show(value)}")
                latex.append(f"{latex_of(self.variable)} = {latex_of(value)}")
            else:
                plain.append(f"{self.variable} = {text}")
                latex.append(rf"{latex_of(self.variable)} \approx {number}")
        self.decimal = " or ".join(plain)
        self.decimal_latex = r" \quad\text{or}\quad ".join(latex)
        self.summary += f" (about {self.decimal})"

    def to_text(self) -> str:
        text = super().to_text()
        others = [method for method in self.methods if method != self.method]
        if others:
            options = ", ".join(f"--method {method}" for method in others)
            text += f"\nOther ways to solve it: {options}\n"
        return text

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "kind": self.kind,
                "kind_label": (
                    f"Formula, solved for {self.variable}"
                    if len(self.letters) > 1
                    else KIND_LABELS.get(self.kind, "Equation")
                ),
                "letters": list(self.letters),
                "method": self.method,
                "methods": [
                    {"id": method, "label": METHOD_LABELS.get(method, method)}
                    for method in self.methods
                ],
                "variable": str(self.variable),
                "answers": [sp.sstr(value) for value in self.answers],
                "answers_latex": [latex_of(value) for value in self.answers],
                "answer_text": self.summary,
                "answer_latex": self.answer_latex,
                "answers_decimal": list(self.answers_decimal),
                "decimal": self.decimal,
                "decimal_latex": self.decimal_latex,
                "everything": self.everything,
            }
        )
        return data
