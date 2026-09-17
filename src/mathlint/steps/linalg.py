"""Linear algebra, worked out the way it is taught.

Every row operation is written down the way a student would write it in the
margin — ``R2 -> R2 - (3/2) R1`` — and every intermediate matrix is kept in
exact fractions, never decimals.
"""

from __future__ import annotations

import sympy as sp

from ..errors import UnsupportedError
from .solution import Solution

LAMBDA = sp.Symbol("lambda")
_TIMES = {1: "once", 2: "twice", 3: "three times", 4: "four times"}


def solve_linalg(operation: str, matrix: sp.Matrix) -> Solution:
    """Work out ``operation`` on ``matrix``, keeping every step."""
    solvers = {
        "rref": rref_solution,
        "det": determinant_solution,
        "inverse": inverse_solution,
        "eigen": eigen_solution,
    }
    if operation not in solvers:
        raise UnsupportedError(f"mathlint cannot do '{operation}' yet")
    return solvers[operation](matrix)


def rref_solution(matrix: sp.Matrix) -> Solution:
    solution = Solution(
        operation="rref",
        title="Row reduction to reduced row echelon form",
    )
    solution.add("Start from this matrix", matrix=matrix)
    work, pivots = _reduce(sp.Matrix(matrix), solution)
    solution.result = work

    rank = len(pivots)
    zero_rows = work.rows - rank
    if zero_rows:
        solution.summary = (
            f"Rank {rank}: {zero_rows} row(s) of zeros, so those rows were "
            "combinations of the others."
        )
    else:
        solution.summary = f"Rank {rank}: every row has a pivot."
    return solution


def determinant_solution(matrix: sp.Matrix) -> Solution:
    _require_square(matrix, "a determinant")
    size = matrix.rows
    solution = Solution(operation="det", title=f"Determinant of a {size}x{size} matrix")
    solution.add("Start from this matrix", matrix=matrix)

    if size == 1:
        solution.result = matrix[0, 0]
        solution.summary = f"det = {_show(matrix[0, 0])}"
        return solution

    if size == 2:
        a, b, c, d = matrix[0, 0], matrix[0, 1], matrix[1, 0], matrix[1, 1]
        solution.add("For a 2x2 matrix the determinant is ad - bc")
        solution.add(
            f"ad - bc = ({_show(a)})({_show(d)}) - ({_show(b)})({_show(c)})",
            expression=sp.simplify(a * d - b * c),
        )
        solution.result = sp.simplify(a * d - b * c)
        solution.summary = f"det = {_show(solution.result)}"
        return solution

    work = sp.Matrix(matrix)
    sign = 1
    for column in range(size):
        pivot = next((row for row in range(column, size) if work[row, column] != 0), None)
        if pivot is None:
            solution.add(
                f"Column {column + 1} is all zeros from row {column + 1} down, so the "
                "rows are dependent"
            )
            solution.result = sp.Integer(0)
            solution.summary = "det = 0, so this matrix is singular."
            return solution
        if pivot != column:
            work.row_swap(pivot, column)
            sign = -sign
            solution.add(
                "Swap rows to get a non-zero pivot — a swap flips the sign of the determinant",
                operation=f"R{column + 1} <-> R{pivot + 1}",
                matrix=sp.Matrix(work),
            )
        for row in range(column + 1, size):
            if work[row, column] == 0:
                continue
            factor = sp.simplify(work[row, column] / work[column, column])
            work[row, :] = sp.simplify(work[row, :] - factor * work[column, :])
            solution.add(
                "Adding a multiple of one row to another leaves the determinant unchanged",
                operation=f"R{row + 1} -> R{row + 1} - ({_show(factor)}) R{column + 1}",
                matrix=sp.Matrix(work),
            )

    diagonal = [work[index, index] for index in range(size)]
    product = sp.simplify(sp.prod(diagonal))
    shown = " * ".join(_show(entry) for entry in diagonal)
    note = " and flip the sign for the row swap" if sign < 0 else ""
    solution.add(
        f"The matrix is upper triangular now, so multiply the diagonal{note}: {shown}",
        expression=sp.simplify(sign * product),
    )
    solution.result = sp.simplify(sign * product)
    solution.summary = f"det = {_show(solution.result)}"
    return solution


def inverse_solution(matrix: sp.Matrix) -> Solution:
    _require_square(matrix, "an inverse")
    size = matrix.rows
    solution = Solution(operation="inverse", title=f"Inverse of a {size}x{size} matrix")
    solution.add("Start from this matrix", matrix=matrix)

    determinant = sp.simplify(matrix.det())
    if determinant == 0:
        solution.add("Check the determinant first", expression=determinant)
        solution.result = None
        solution.summary = "det = 0, so this matrix has no inverse."
        return solution

    augmented = sp.Matrix(matrix).row_join(sp.eye(size))
    solution.add(
        "Write the identity beside it and row reduce until the left half is the identity",
        matrix=augmented,
    )
    work, _ = _reduce(augmented, solution)
    inverse = work[:, size:]
    solution.add("The left half is the identity, so the right half is the inverse", matrix=inverse)
    solution.result = inverse
    solution.summary = f"det = {_show(determinant)}, so the inverse exists."
    return solution


def eigen_solution(matrix: sp.Matrix) -> Solution:
    _require_square(matrix, "eigenvalues")
    size = matrix.rows
    solution = Solution(operation="eigen", title=f"Eigenvalues and eigenvectors ({size}x{size})")
    solution.add("Start from this matrix", matrix=matrix)

    shifted = matrix - LAMBDA * sp.eye(size)
    solution.add("Subtract lambda from the diagonal: A - lambda*I", matrix=shifted)
    characteristic = sp.expand(shifted.det())
    solution.add(
        "The characteristic polynomial is det(A - lambda*I) = 0",
        expression=sp.Eq(characteristic, 0),
    )
    factored = sp.factor(characteristic)
    if factored != characteristic:
        solution.add("Factor it", expression=sp.Eq(factored, 0))

    roots = sp.roots(sp.Poly(characteristic, LAMBDA))
    if not roots:
        solution.summary = "This polynomial has no roots mathlint can write down exactly."
        return solution

    for value, multiplicity in sorted(roots.items(), key=lambda pair: sp.default_sort_key(pair[0])):
        times = _TIMES.get(multiplicity, f"{multiplicity} times")
        solution.add(f"lambda = {_show(value)} is a root of the polynomial, {times}")
        block = sp.simplify(matrix - value * sp.eye(size))
        solution.add(
            f"Solve (A - lambda*I)v = 0 for lambda = {_show(value)}",
            matrix=block,
        )
        solution.add("Row reduce it", matrix=block.rref()[0])
        vectors = block.nullspace()
        if not vectors:
            solution.add("No eigenvector could be found for this root")
            continue
        for vector in vectors:
            scaled = _clear_fractions(vector)
            solution.add(f"An eigenvector for lambda = {_show(value)}", matrix=scaled)

    listed = ", ".join(
        f"{_show(value)} ({_TIMES.get(multiplicity, f'{multiplicity} times')})"
        for value, multiplicity in sorted(
            roots.items(), key=lambda pair: sp.default_sort_key(pair[0])
        )
    )
    solution.summary = f"Eigenvalues: {listed}."
    solution.result = sp.Matrix(sorted(roots, key=sp.default_sort_key))
    return solution


def _reduce(work: sp.Matrix, solution: Solution) -> tuple[sp.Matrix, list[int]]:
    """Gauss-Jordan elimination, writing each row operation into ``solution``."""
    pivot_row = 0
    pivots: list[int] = []
    for column in range(work.cols):
        if pivot_row >= work.rows:
            break
        pivot = next((row for row in range(pivot_row, work.rows) if work[row, column] != 0), None)
        if pivot is None:
            continue
        if pivot != pivot_row:
            work.row_swap(pivot, pivot_row)
            solution.add(
                f"Column {column + 1} needs a pivot, so swap the rows",
                operation=f"R{pivot_row + 1} <-> R{pivot + 1}",
                matrix=sp.Matrix(work),
            )
        value = work[pivot_row, column]
        if value != 1:
            work[pivot_row, :] = sp.simplify(work[pivot_row, :] / value)
            solution.add(
                "Divide the pivot row so the pivot becomes 1",
                operation=f"R{pivot_row + 1} -> ({_show(sp.simplify(1 / value))}) R{pivot_row + 1}",
                matrix=sp.Matrix(work),
            )
        for row in range(work.rows):
            if row == pivot_row or work[row, column] == 0:
                continue
            factor = work[row, column]
            work[row, :] = sp.simplify(work[row, :] - factor * work[pivot_row, :])
            solution.add(
                f"Clear the rest of column {column + 1}",
                operation=f"R{row + 1} -> R{row + 1} - ({_show(factor)}) R{pivot_row + 1}",
                matrix=sp.Matrix(work),
            )
        pivots.append(column)
        pivot_row += 1
    return work, pivots


def _clear_fractions(vector: sp.Matrix) -> sp.Matrix:
    """Scale an eigenvector so its entries are whole numbers when possible."""
    denominators = [sp.denom(entry) for entry in vector if entry.is_Rational]
    if not denominators:
        return vector
    multiplier = sp.ilcm(*[int(value) for value in denominators]) if denominators else 1
    return sp.simplify(vector * multiplier)


def _require_square(matrix: sp.Matrix, what: str) -> None:
    if matrix.rows != matrix.cols:
        raise UnsupportedError(
            f"only square matrices have {what}, and this one is {matrix.rows}x{matrix.cols}"
        )


def _show(value: sp.Expr) -> str:
    return sp.sstr(value).replace("**", "^")
