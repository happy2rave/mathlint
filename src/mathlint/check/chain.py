"""Check a chain of expressions: every line must equal the one before it."""

from __future__ import annotations

import sympy as sp

from ..document import Document
from ..equivalence import compare
from ..i18n import msg
from ..report import Report, Step


def check_chain(document: Document) -> Report:
    """Compare each line with the line above it."""
    variable = _integration_variable(document)
    steps: list[Step] = []
    previous = None
    for line in document.lines:
        assert line.expr is not None
        step = Step(
            line=line.number,
            raw=line.raw,
            read_as=line.read_as,
            read_as_latex=line.read_as_latex,
            warnings=list(line.warnings),
        )
        if previous is not None:
            result = compare(previous.expr, line.expr, up_to_constant_in=variable)
            step.verdict = result.verdict
            step.method = result.method
            step.message = result.message
            step.compared_to = previous.number
            step.hints = result.hints
            step.counterexample = result.counterexample
            step.values = result.values
        steps.append(step)
        previous = line

    return Report(mode="chain", steps=steps, notes=_notes(document, variable))


def _integration_variable(document: Document) -> sp.Symbol | None:
    """The variable of the indefinite integral this chain is solving, if any."""
    for line in document.lines:
        assert line.expr is not None
        for integral in line.expr.atoms(sp.Integral):
            if integral.limits and len(integral.limits[0]) == 1:
                return integral.limits[0][0]
    return None


def _notes(document: Document, variable: sp.Symbol | None) -> list[str]:
    notes: list[str] = []
    first, last = document.lines[0], document.lines[-1]
    assert first.expr is not None and last.expr is not None
    started = first.expr.atoms(sp.Derivative, sp.Integral)
    if started and last.expr.atoms(sp.Derivative, sp.Integral) and len(document.lines) > 1:
        notes.append(
            msg(
                "line {number} still contains a derivative or integral — the "
                "answer is not finished",
                number=last.number,
            )
        )
    elif variable is not None and not last.expr.atoms(sp.Integral):
        constants = {symbol for symbol in last.expr.free_symbols if symbol.name in {"C", "K"}}
        if not constants:
            notes.append(
                msg(
                    "line {number} is an indefinite integral without a constant — add + C",
                    number=last.number,
                )
            )
    return notes
