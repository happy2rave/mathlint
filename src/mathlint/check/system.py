"""Check the steps of solving a system: each line is the whole system so far.

Two lines are equivalent when they have the same solutions. A solution of the
line above that the next line no longer has means an arithmetic slip, and the
report names it; extra solutions mean an equation was lost or combined in a way
that cannot be undone, which is a warning. The last line is also checked against
the first, so an answer that does not solve the original system is caught.
"""

from __future__ import annotations

import sympy as sp

from ..document import Document, Line
from ..equivalence import Verdict
from ..i18n import msg
from ..parse.plain import read_as
from ..report import Report, Step


def check_system(document: Document) -> Report:
    letters = [
        lhs.free_symbols | rhs.free_symbols for line in document.lines for lhs, rhs in line.system
    ]
    unknowns = sorted(set().union(*letters), key=lambda symbol: symbol.name)
    steps: list[Step] = []
    previous: Line | None = None
    previous_solutions: list[dict] | None = None
    for line in document.lines:
        solutions = _solutions(line.system, unknowns)
        step = Step(
            line=line.number,
            raw=line.raw,
            read_as=line.read_as,
            read_as_latex=line.read_as_latex,
            warnings=list(line.warnings),
        )
        if previous is not None:
            step.compared_to = previous.number
            _judge(step, previous, previous_solutions, line, solutions)
        steps.append(step)
        previous, previous_solutions = line, solutions

    _check_against_first(document, steps, previous_solutions)
    return Report(mode="system", steps=steps)


def _judge(
    step: Step,
    previous: Line,
    previous_solutions: list[dict] | None,
    line: Line,
    solutions: list[dict] | None,
) -> None:
    if previous_solutions is None or solutions is None:
        step.verdict = Verdict.UNSURE
        step.message = msg("cannot work out the solutions of these systems to compare them")
        return
    lost = [s for s in previous_solutions if not _satisfies(line.system, s)]
    if lost:
        step.verdict = Verdict.WRONG
        step.message = msg(
            "the solution {lost} of the line above does not satisfy this line",
            lost=_describe(lost[0]),
        )
        failing = _failing_equation(line.system, lost[0])
        if failing is not None:
            step.hints = [msg("check equation {failing} of this line", failing=failing)]
        return
    gained = [s for s in solutions if not _satisfies(previous.system, s)]
    if gained and line.arrow != "=>":
        step.verdict = Verdict.WARNING
        step.message = msg(
            "this line has more solutions than the one above (for "
            "example {gained}) — an equation was lost or combined in a "
            "way that cannot be undone",
            gained=_describe(gained[0]),
        )
        return
    step.verdict = Verdict.OK
    step.message = msg("same solutions as the line above")


def _check_against_first(document: Document, steps: list[Step], last: list[dict] | None) -> None:
    if len(document.lines) < 2 or last is None or steps[-1].verdict is not Verdict.OK:
        return
    # only an answer that pins every unknown down is checked against the start
    if any(value.free_symbols for solution in last for value in solution.values()):
        return
    first = document.lines[0]
    for solution in last:
        if not _satisfies(first.system, solution):
            steps[-1].verdict = Verdict.WRONG
            steps[-1].message = msg(
                "{solution} does not satisfy the original system on line {number}",
                solution=_describe(solution),
                number=first.number,
            )
            steps[-1].hints = [msg("always put your answer back into the first system")]
            return


def _solutions(
    system: list[tuple[sp.Expr, sp.Expr]], unknowns: list[sp.Symbol]
) -> list[dict] | None:
    try:
        found = sp.solve([sp.Eq(lhs, rhs) for lhs, rhs in system], unknowns, dict=True)
    except Exception:
        return None
    return [s for s in found if all(value.is_real is not False for value in s.values())]


def _satisfies(system: list[tuple[sp.Expr, sp.Expr]], solution: dict) -> bool:
    return _failing_equation(system, solution) is None


def _failing_equation(system: list[tuple[sp.Expr, sp.Expr]], solution: dict) -> int | None:
    for index, (lhs, rhs) in enumerate(system, start=1):
        try:
            difference = sp.simplify((lhs - rhs).subs(solution))
        except Exception:
            return index
        if difference != 0:
            return index
    return None


def _describe(solution: dict) -> str:
    return ", ".join(
        f"{name} = {read_as(value)}"
        for name, value in sorted(solution.items(), key=lambda item: item[0].name)
    )
