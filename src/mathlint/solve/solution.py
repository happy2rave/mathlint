"""The result of solving an equation: the worked steps plus the answers."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..parse.plain import latex_of
from ..steps.solution import Solution
from .core import Outcome, answer_latex, answer_text
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

    def finish(self, outcome: Outcome) -> None:
        assert self.variable is not None
        self.answers = list(outcome.values)
        self.everything = outcome.everything
        self.solution_set = outcome.solution_set
        self.summary = answer_text(self.variable, outcome)
        self.answer_latex = answer_latex(self.variable, outcome)
        if outcome.everything:
            self.result = sp.S.Reals
        elif outcome.solution_set is not None:
            self.result = outcome.solution_set
        else:
            self.result = sp.FiniteSet(*self.answers)

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
                "everything": self.everything,
            }
        )
        return data
