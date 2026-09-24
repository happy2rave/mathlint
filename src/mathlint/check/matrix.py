"""Check a row reduction the student did by hand.

"Same reduced form" is too weak to be useful: every invertible matrix reduces
to the identity, so an arithmetic slip inside an invertible matrix would sail
through. What actually has to hold is that each line *is* the line above with
row operations applied to it.

So mathlint solves for the coefficient matrix ``M`` in ``after = M @ before``.
That answers everything at once: no solution means a row is not a combination
of the rows above; a singular ``M`` means the step threw information away; and
a row of ``M`` with three or more non-zero entries means that row is not one
row operation but a mixture — which, in a hand-written reduction, is an
arithmetic slip. When it all checks out, ``M`` even says which operations were
used, so the report can name them back.
"""

from __future__ import annotations

import sympy as sp

from ..document import Document
from ..equivalence import Verdict
from ..i18n import msg
from ..parse.plain import read_as
from ..report import Report, Step

MAX_SOURCE_ROWS = 2


def check_matrix(document: Document) -> Report:
    """Compare each matrix with the one above it."""
    steps: list[Step] = []
    previous = None
    for line in document.lines:
        assert line.matrix is not None
        step = Step(
            line=line.number,
            raw=line.raw,
            read_as=line.read_as,
            read_as_latex=line.read_as_latex,
            warnings=list(line.warnings),
        )
        if previous is not None:
            step.compared_to = previous.number
            assert previous.matrix is not None
            _judge(step, previous.matrix, line.matrix, line.arrow)
        steps.append(step)
        previous = line
    return Report(mode="matrix", steps=steps)


def _judge(step: Step, before: sp.Matrix, after: sp.Matrix, arrow: str) -> None:
    if before.shape != after.shape:
        step.verdict = Verdict.WRONG
        step.message = msg(
            "the size changed: {rows}x{cols} became {rows2}x{cols2}",
            rows=before.rows,
            cols=before.cols,
            rows2=after.rows,
            cols2=after.cols,
        )
        step.hints = [msg("row operations never add or remove rows or columns")]
        return

    if sp.simplify(before - after) == sp.zeros(*before.shape):
        step.verdict = Verdict.OK
        step.message = msg("same matrix as the line above")
        return

    coefficients = _coefficients(before, after)

    if coefficients is None:
        _judge_by_reduced_form(step, before, after, arrow)
        return

    if sp.simplify(coefficients.det()) == 0:
        step.verdict = Verdict.WRONG
        step.message = msg(
            "this step cannot be undone — a row was replaced by "
            "something that loses information, so the solutions change"
        )
        step.hints = [msg("multiplying a row by 0, or overwriting a row with a copy of another")]
        return

    stray = _row_with_too_many_sources(coefficients)
    if stray is not None:
        step.verdict = Verdict.WRONG
        step.message = msg(
            "row {stray} is not one row operation applied to line above "
            "— it mixes {count} or more rows together",
            stray=stray,
            count=MAX_SOURCE_ROWS + 1,
        )
        step.hints = [msg("check the arithmetic in row {stray}", stray=stray)]
        return

    operations = _describe(coefficients)
    performed = ", ".join(operations) if operations else msg("the rows were reordered")

    odd = _rescaled_and_mixed(coefficients)
    if odd is not None:
        step.verdict = Verdict.WARNING
        step.message = msg(
            "this line only works out as {performed} — if you meant to "
            "keep row {odd} as it was, the arithmetic in that row is off",
            performed=performed,
            odd=odd,
        )
        return

    if arrow == "~" or arrow == "":
        step.verdict = Verdict.OK
        step.message = msg("row operation checks out: {performed}", performed=performed)
        return

    step.verdict = Verdict.WARNING
    step.message = msg(
        "{performed} — this is a row operation, not an equality, so write ~ instead of =",
        performed=performed,
    )


def _judge_by_reduced_form(step: Step, before: sp.Matrix, after: sp.Matrix, arrow: str) -> None:
    """Fallback when the coefficients are not unique (dependent rows above)."""
    stray = _stray_row(before, after)
    if stray is not None:
        step.verdict = Verdict.WRONG
        step.message = msg(
            "row {stray} is not a combination of the rows in the line above", stray=stray
        )
        step.hints = [msg("check the arithmetic in row {stray}", stray=stray)]
        return
    if before.rref()[0] != after.rref()[0]:
        step.verdict = Verdict.WRONG
        step.message = msg("not row-equivalent to the line above — this step changes the solutions")
        return
    if arrow == "=":
        step.verdict = Verdict.WARNING
        step.message = msg(
            "row-equivalent to the line above, but not equal to it — write ~ instead of ="
        )
        return
    step.verdict = Verdict.OK
    step.message = msg("row-equivalent to the line above (same reduced form)")


def _coefficients(before: sp.Matrix, after: sp.Matrix) -> sp.Matrix | None:
    """Solve ``after = M @ before`` for ``M``, or return None if it is not unique."""
    if before.rank() < before.rows:
        return None
    try:
        solution, parameters = before.T.gauss_jordan_solve(after.T)
    except ValueError:
        return None
    if parameters.free_symbols:
        solution = solution.subs({symbol: 0 for symbol in parameters.free_symbols})
    return sp.simplify(solution.T)


def _row_with_too_many_sources(coefficients: sp.Matrix) -> int | None:
    for index in range(coefficients.rows):
        used = sum(1 for column in range(coefficients.cols) if coefficients[index, column] != 0)
        if used > MAX_SOURCE_ROWS:
            return index + 1
    return None


def _rescaled_and_mixed(coefficients: sp.Matrix) -> int | None:
    """A row that was scaled *and* mixed with another row.

    ``R2 -> 2 R2 + R1`` is legal, and some courses teach it to avoid fractions,
    but it is also what an arithmetic slip looks like from the outside: the only
    way to explain the new row is an operation nobody would write by choice.
    """
    for index in range(coefficients.rows):
        own = coefficients[index, index]
        others = [
            column
            for column in range(coefficients.cols)
            if column != index and coefficients[index, column] != 0
        ]
        if others and own not in (sp.Integer(0), sp.Integer(1)):
            return index + 1
    return None


def _describe(coefficients: sp.Matrix) -> list[str]:
    """Turn the coefficient matrix back into ``R2 -> R2 + (3) R1`` notation."""
    operations: list[str] = []
    for index in range(coefficients.rows):
        used = [
            (column, coefficients[index, column])
            for column in range(coefficients.cols)
            if coefficients[index, column] != 0
        ]
        if used == [(index, sp.Integer(1))]:
            continue
        label = f"R{index + 1} ->"
        if len(used) == 1:
            column, factor = used[0]
            operations.append(f"{label} ({_show(factor)}) R{column + 1}")
            continue
        own = [pair for pair in used if pair[0] == index]
        others = [pair for pair in used if pair[0] != index]
        if own and others:
            factor, (column, other) = own[0][1], others[0]
            head = f"R{index + 1}" if factor == 1 else f"({_show(factor)}) R{index + 1}"
            operations.append(f"{label} {head} + ({_show(other)}) R{column + 1}")
            continue
        parts = " + ".join(f"({_show(factor)}) R{column + 1}" for column, factor in used)
        operations.append(f"{label} {parts}")
    return operations


def _stray_row(before: sp.Matrix, after: sp.Matrix) -> int | None:
    rank = before.rank()
    for index in range(after.rows):
        if before.col_join(after.row(index)).rank() > rank:
            return index + 1
    return None


def _show(value: sp.Expr) -> str:
    return read_as(value)
