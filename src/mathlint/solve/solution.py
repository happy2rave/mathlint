"""The result of solving an equation: the worked steps plus the answers."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..parse.plain import latex_of
from ..steps.solution import Solution
from .core import Outcome, answer_latex, answer_text
from .dispatch import METHOD_LABELS


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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "kind": self.kind,
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
