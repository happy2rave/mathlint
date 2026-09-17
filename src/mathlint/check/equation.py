"""Check the steps of solving an equation.

Two slips matter here, and they are not the same slip. Losing a solution (by
dividing by ``x``) is always wrong. Gaining one (by squaring both sides) is
allowed as long as the student throws it out at the end — so a gained solution
is a warning, and the final answer is checked against the original equation.
"""

from __future__ import annotations

import sympy as sp

from ..document import Document, Line
from ..equivalence import Verdict
from ..numeric import evaluate
from ..parse.plain import read_as
from ..report import Report, Step


def check_equation(document: Document) -> Report:
    """Compare the solutions of each line with the line above it."""
    variable = document.variable
    assert variable is not None
    original = document.lines[0].equation
    assert original is not None

    steps: list[Step] = []
    previous_line: Line | None = None
    previous_set: sp.Set | None = None

    for line in document.lines:
        current_set = _solution_set(line, variable)
        step = Step(
            line=line.number,
            raw=line.raw,
            read_as=line.read_as,
            read_as_latex=line.read_as_latex,
            warnings=list(line.warnings),
        )
        if previous_line is not None:
            step.compared_to = previous_line.number
            _judge(step, previous_set, current_set, line.arrow, variable, original)
        steps.append(step)
        previous_line, previous_set = line, current_set

    notes = _check_final_answer(steps, document, variable, original)
    return Report(mode="equation", steps=steps, notes=notes)


def _judge(
    step: Step,
    previous_set: sp.Set | None,
    current_set: sp.Set | None,
    arrow: str,
    variable: sp.Symbol,
    original: tuple[sp.Expr, sp.Expr],
) -> None:
    if previous_set is None or current_set is None:
        step.verdict = Verdict.UNSURE
        step.message = "cannot work out the solutions of this line"
        return

    lost = _difference(previous_set, current_set)
    gained = _difference(current_set, previous_set)
    if lost is None or gained is None:
        step.verdict = Verdict.UNSURE
        step.message = "cannot compare the solutions of these two lines"
        return

    real_losses = [value for value in lost if _satisfies(original, variable, value)]
    if real_losses:
        value = read_as(real_losses[0])
        step.verdict = Verdict.WRONG
        step.message = f"the solution {variable.name} = {value} was lost"
        step.hints = [
            f"did you divide by something that is zero when {variable.name} = {value}?"
        ]
        return

    if lost:
        dropped = ", ".join(f"{variable.name} = {read_as(value)}" for value in lost)
        step.verdict = Verdict.OK
        step.message = f"dropped {dropped}, which does not solve the original equation — good"
        return

    if gained:
        added = ", ".join(f"{variable.name} = {read_as(value)}" for value in gained)
        if arrow == "=>":
            step.verdict = Verdict.OK
            step.message = f"adds {added}; an implication (=>) is allowed to do that"
            return
        step.verdict = Verdict.WARNING
        step.message = (
            f"this step introduces {added} — check it against the original equation "
            "before writing it in the answer"
        )
        return

    step.verdict = Verdict.OK
    step.message = "same solutions as the line above"


def _check_final_answer(
    steps: list[Step],
    document: Document,
    variable: sp.Symbol,
    original: tuple[sp.Expr, sp.Expr],
) -> list[str]:
    last_line, last_step = document.lines[-1], steps[-1]
    if last_line.kind != "solutions" or not last_line.solutions:
        return []
    if last_step.verdict is Verdict.WRONG:
        return []
    for value in last_line.solutions:
        if not _satisfies(original, variable, value):
            last_step.verdict = Verdict.WRONG
            last_step.message = (
                f"{variable.name} = {read_as(value)} does not satisfy the original "
                f"equation on line {document.lines[0].number}"
            )
            last_step.hints = ["always put your answers back into the first line"]
            return []
    return []


def _solution_set(line: Line, variable: sp.Symbol) -> sp.Set | None:
    if line.kind == "solutions":
        if not line.solutions:
            return sp.S.EmptySet
        return sp.FiniteSet(*line.solutions)
    assert line.equation is not None
    left, right = line.equation
    try:
        return sp.solveset(sp.Eq(left, right), variable, domain=sp.S.Reals)
    except Exception:
        return None


def _difference(first: sp.Set, second: sp.Set) -> list[sp.Expr] | None:
    """Elements of ``first`` that are not in ``second``, or None if unknown."""
    left = _elements(first)
    right = _elements(second)
    if left is None or right is None:
        return None
    return [value for value in left if not any(_same(value, other) for other in right)]


def _elements(candidate: sp.Set) -> list[sp.Expr] | None:
    if candidate == sp.S.EmptySet:
        return []
    if isinstance(candidate, sp.FiniteSet):
        return list(candidate.args)
    return None


def _same(first: sp.Expr, second: sp.Expr) -> bool:
    if first == second:
        return True
    try:
        return sp.simplify(first - second) == 0
    except Exception:
        return False


def _satisfies(equation: tuple[sp.Expr, sp.Expr], variable: sp.Symbol, value: sp.Expr) -> bool:
    left, right = equation
    residual = (left - right).subs(variable, value)
    try:
        if sp.simplify(residual) == 0:
            return True
    except Exception:
        pass
    number = evaluate(residual, {})
    if number is None:
        return False
    return abs(number) < sp.Float("1e-10")
