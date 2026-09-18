"""A worked solution: the steps, and how to print them."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..parse.plain import read_as
from .matrix import format_matrix


@dataclass
class SolutionStep:
    """One step of a worked solution."""

    text: str
    operation: str = ""
    matrix: sp.Matrix | None = None
    expression: sp.Expr | None = None
    # for math that is not one expression, such as "x = 2 or x = 3"
    display: str = ""
    display_latex: str = ""

    def rendered(self) -> str:
        if self.matrix is not None:
            return format_matrix(self.matrix)
        if isinstance(self.expression, sp.Equality):
            left, right = self.expression.args
            return f"{_plain(left)} = {_plain(right)}"
        if self.expression is not None:
            return _plain(self.expression)
        return self.display

    def latex(self) -> str:
        if self.matrix is not None:
            return sp.latex(self.matrix)
        if self.expression is not None:
            return sp.latex(self.expression)
        return self.display_latex

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "operation": self.operation,
            "math": self.rendered(),
            "math_latex": self.latex(),
        }


@dataclass
class Solution:
    """Everything needed to show how an answer was reached."""

    operation: str
    title: str
    steps: list[SolutionStep] = field(default_factory=list)
    summary: str = ""
    result: sp.Matrix | sp.Expr | None = None

    def add(
        self,
        text: str,
        operation: str = "",
        matrix: sp.Matrix | None = None,
        expression: sp.Expr | None = None,
    ) -> None:
        self.steps.append(
            SolutionStep(text=text, operation=operation, matrix=matrix, expression=expression)
        )

    def to_text(self) -> str:
        lines = [self.title, "=" * len(self.title), ""]
        for index, step in enumerate(self.steps, start=1):
            headline = f"{index}. {step.text}"
            if step.operation:
                headline += f"    {step.operation}"
            lines.append(headline)
            body = step.rendered()
            if body:
                lines.extend("      " + row for row in body.splitlines())
            lines.append("")
        if self.summary:
            lines.append(self.summary)
        return "\n".join(lines).rstrip() + "\n"

    def to_markdown(self) -> str:
        lines = [f"### {self.title}", "", "| # | Step | Result |", "| --- | --- | --- |"]
        for index, step in enumerate(self.steps, start=1):
            what = step.text + (f" — `{step.operation}`" if step.operation else "")
            body = step.rendered().replace("\n", "<br>")
            lines.append(f"| {index} | {what} | <code>{body}</code> |")
        if self.summary:
            lines += ["", self.summary]
        return "\n".join(lines)

    def to_latex(self) -> str:
        lines = [f"\\textbf{{{self.title}}}", "", "\\begin{enumerate}"]
        for step in self.steps:
            what = step.text + (f" (${_latex_escape(step.operation)}$)" if step.operation else "")
            lines.append(f"  \\item {what}")
            body = step.latex()
            if body:
                lines.append(f"  \\[ {body} \\]")
        lines.append("\\end{enumerate}")
        if self.summary:
            lines += ["", self.summary]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "title": self.title,
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary,
            "result": None if self.result is None else sp.sstr(self.result),
            "result_latex": None if self.result is None else sp.latex(self.result),
        }


def _plain(expression: sp.Expr) -> str:
    return read_as(expression)


def _latex_escape(operation: str) -> str:
    return operation.replace("->", r"\to ").replace("<->", r"\leftrightarrow ")
