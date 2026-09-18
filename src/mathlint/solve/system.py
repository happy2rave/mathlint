"""Systems of linear equations, five ways.

Every method starts from the same place — each equation written as
``a x + b y + ... = c``, fractions cleared — and ends in the same place: the
solution put back into every original equation.

* elimination — scale two equations so one unknown cancels when they are added;
* substitution — solve one equation for one unknown and put that into the other;
* Gaussian elimination — row reduce the augmented matrix ``[A | b]``;
* Cramer's rule — ``x = D_x / D``, a ratio of determinants;
* the inverse matrix — ``x = A^-1 b``.

A system can also have no solution (the equations contradict each other) or
infinitely many (one equation repeats another); both are explained, and in the
second case every unknown is written in terms of the ones that are free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from ..errors import ParseError, UnsupportedError
from ..parse.plain import latex_of
from ..steps.linalg import reduce_rows
from ..steps.matrix import format_matrix
from ..steps.solution import Solution
from . import dispatch
from .core import Equation, Work, show

_ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth"]
_CASES = re.compile(r"\\begin\{cases\}(.*?)\\end\{cases\}", re.S)

SYSTEM_METHOD_LABELS = {
    "elimination": "Elimination",
    "substitution": "Substitution",
    "gaussian": "Gaussian elimination",
    "cramer": "Cramer's rule",
    "inverse": "Inverse matrix",
}


def split_equations(text: str) -> list[str]:
    """Several equations: one per line, separated by ';', or a LaTeX cases block."""
    cases = _CASES.search(text)
    if cases:
        return [part.strip() for part in cases.group(1).split("\\\\") if part.strip()]
    return [part.strip() for part in re.split(r"[\n;]", text) if part.strip()]


@dataclass
class SystemSolution(Solution):
    kind: str = "linear-system"
    method: str = ""
    methods: list[str] = field(default_factory=list)
    unknowns: list[sp.Symbol] = field(default_factory=list)
    assignments: list[dict[sp.Symbol, sp.Expr]] = field(default_factory=list)
    free: list[sp.Symbol] = field(default_factory=list)
    answer_latex: str = ""

    def finish(self, assignments: list[dict], free: list[sp.Symbol]) -> None:
        self.assignments = assignments
        self.free = free
        if not assignments:
            self.summary = "no solution"
            self.answer_latex = r"\text{no solution}"
            return
        solution = assignments[0]
        shown = [name for name in self.unknowns if name not in free]
        text = ", ".join(f"{name} = {show(solution[name])}" for name in shown)
        latex = r",\quad ".join(f"{latex_of(name)} = {latex_of(solution[name])}" for name in shown)
        if free:
            names = ", ".join(str(name) for name in free)
            verb = "can be any real number" if len(free) == 1 else "can be any real numbers"
            text += f", where {names} {verb}"
            latex += r",\quad " + ", ".join(latex_of(name) for name in free) + r" \in \mathbb{R}"
        self.summary = text
        self.answer_latex = latex

    def to_text(self) -> str:
        text = super().to_text()
        others = [method for method in self.methods if method != self.method]
        if others:
            text += "\nOther ways to solve it: " + ", ".join(f"--method {m}" for m in others) + "\n"
        return text

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "kind": self.kind,
                "kind_label": "System of linear equations",
                "method": self.method,
                "methods": [
                    {"id": method, "label": SYSTEM_METHOD_LABELS[method]} for method in self.methods
                ],
                "variables": [str(name) for name in self.unknowns],
                "answers": [
                    {str(name): sp.sstr(value) for name, value in assignment.items()}
                    for assignment in self.assignments
                ],
                "free": [str(name) for name in self.free],
                "answer_text": self.summary,
                "answer_latex": self.answer_latex,
                "everything": False,
            }
        )
        return data


# ---------------------------------------------------------------- entry point


def solve_system(equations: list[Equation], method: str | None = None) -> SystemSolution:
    unknowns = sorted(
        set().union(*[eq.lhs.free_symbols | eq.rhs.free_symbols for eq in equations]),
        key=lambda symbol: symbol.name,
    )
    if not unknowns:
        raise ParseError("these equations have no unknowns to solve for")
    for index, eq in enumerate(equations, start=1):
        if not _is_linear(eq, unknowns):
            raise UnsupportedError(
                f"equation {index} is not linear; systems with squares, products or "
                "functions of the unknowns are coming later in v0.6"
            )

    matrix, right = sp.linear_eq_to_matrix([eq.lhs - eq.rhs for eq in equations], unknowns)
    methods = _methods(matrix, unknowns)
    if "substitution" in methods and any(_solved_for_one(eq) for eq in equations):
        # y = 2x - 1 is already solved for y: substituting it is the natural move
        methods.remove("substitution")
        methods.insert(0, "substitution")
    if method is not None and method not in methods:
        raise UnsupportedError(
            f"the method '{method}' does not apply here — try {', '.join(methods)}"
        )
    chosen = method or methods[0]

    solution = SystemSolution(
        operation="solve",
        title="Solve the system",
        method=chosen,
        methods=methods,
        unknowns=list(unknowns),
    )
    work = Work(solution, unknowns[0])
    _show_system(work, "Start from", equations)

    # substitution into y = 2x - 1 needs no "-2x + y = -1" detour first
    detour = not (chosen == "substitution" and any(_solved_for_one(eq) for eq in equations))
    rows = _standard_rows(matrix, right, work, equations, show_standard=detour)
    solver = {
        "elimination": _elimination,
        "substitution": _substitution,
        "gaussian": _gaussian,
        "cramer": _cramer,
        "inverse": _inverse,
    }[chosen]
    assignments, free = solver(rows, list(unknowns), work)
    if assignments:
        _check(equations, assignments[0], work)
    solution.finish(assignments, free)
    return solution


def _solved_for_one(equation: Equation) -> bool:
    for side, other in ((equation.lhs, equation.rhs), (equation.rhs, equation.lhs)):
        if side.is_Symbol and not other.has(side):
            return True
    return False


def _is_linear(equation: Equation, unknowns: list[sp.Symbol]) -> bool:
    expr = sp.expand(equation.lhs - equation.rhs)
    if not expr.is_polynomial(*unknowns):
        return False
    return sp.Poly(expr, *unknowns).total_degree() <= 1


def _methods(matrix: sp.Matrix, unknowns: list[sp.Symbol]) -> list[str]:
    square_and_regular = matrix.rows == matrix.cols and matrix.det() != 0
    methods: list[str] = []
    if len(unknowns) == 2 and matrix.rows == 2:
        methods += ["elimination", "substitution"]
    methods.append("gaussian")
    if square_and_regular:
        if len(unknowns) <= 3:
            methods.append("cramer")
        methods.append("inverse")
    return methods


# ---------------------------------------------------------------- display


def _show_system(work: Work, text: str, equations: list[Equation]) -> None:
    work.show(
        text,
        "\n".join(f"{show(eq.lhs)} = {show(eq.rhs)}" for eq in equations),
        r"\begin{cases} "
        + r" \\ ".join(f"{latex_of(eq.lhs)} = {latex_of(eq.rhs)}" for eq in equations)
        + r" \end{cases}",
    )


def _row_equation(row: list[sp.Expr], unknowns: list[sp.Symbol]) -> Equation:
    *coefficients, constant = row
    terms = zip(coefficients, unknowns, strict=True)
    return Equation(sp.Add(*[coefficient * name for coefficient, name in terms]), constant)


def _standard_rows(
    matrix: sp.Matrix,
    right: sp.Matrix,
    work: Work,
    equations: list[Equation],
    show_standard: bool = True,
) -> list[list[sp.Expr]]:
    """Each equation as ``[a, b, ..., c]`` for ``a x + b y + ... = c``, fractions cleared."""
    unknowns = work.solution.unknowns
    rows = [list(matrix.row(index)) + [right[index]] for index in range(matrix.rows)]
    standard = [_row_equation(row, unknowns) for row in rows]
    if show_standard and any(
        (sp.expand(eq.lhs), sp.expand(eq.rhs)) != (std.lhs, std.rhs)
        for eq, std in zip(equations, standard, strict=True)
    ):
        _show_system(work, "Write each equation with the unknowns on the left", standard)

    cleared = []
    for row in rows:
        denominators = [entry.q for entry in row if entry.is_Rational]
        multiplier = sp.ilcm(*denominators) if len(denominators) > 1 else (denominators or [1])[0]
        cleared.append([sp.expand(entry * multiplier) for entry in row])
    if cleared != rows:
        _show_system(
            work,
            "Clear the fractions: multiply each equation by its common denominator",
            [_row_equation(row, unknowns) for row in cleared],
        )
    return cleared


# ---------------------------------------------------------------- two unknowns


def _elimination(rows, unknowns, work):
    first, second = rows
    candidates = [index for index in range(2) if first[index] != 0 and second[index] != 0]
    if not candidates:
        return _substitution(rows, unknowns, work)
    # cancel the unknown whose coefficients need the smallest multipliers
    index = min(candidates, key=lambda i: (sp.ilcm(abs(first[i]), abs(second[i])), -i))
    target = sp.ilcm(abs(first[index]), abs(second[index]))
    m1, m2 = target / abs(first[index]), target / abs(second[index])
    scaled1 = [entry * m1 for entry in first]
    scaled2 = [entry * m2 for entry in second]
    if m1 != 1:
        _show_system(
            work,
            f"Multiply the first equation by {show(m1)}",
            [_row_equation(scaled1, unknowns), _row_equation(second, unknowns)],
        )
    if m2 != 1:
        _show_system(
            work,
            f"Multiply the second equation by {show(m2)}",
            [_row_equation(scaled1, unknowns), _row_equation(scaled2, unknowns)],
        )
    name = unknowns[index]
    if (first[index] > 0) == (second[index] > 0):
        combined = [a - b for a, b in zip(scaled1, scaled2, strict=True)]
        text = f"Subtract the second equation from the first, so {name} cancels"
    else:
        combined = [a + b for a, b in zip(scaled1, scaled2, strict=True)]
        text = f"Add the two equations, so {name} cancels"
    single = _row_equation(combined, unknowns)
    work.equation(text, single)

    other = unknowns[1 - index]
    if combined[1 - index] == 0:
        return _degenerate(combined[2], first, unknowns, work)
    found = dispatch.solve_equation(single, other, work)
    value = found.values[0]
    return _back_substitute(first, unknowns, other, value, work, "first")


def _substitution(rows, unknowns, work):
    # an unknown with coefficient 1 or -1 is the easiest to solve for
    options = [
        (abs(rows[r][c]) != 1, r, c) for r in range(2) for c in range(2) if rows[r][c] != 0
    ]
    if not options:
        return _degenerate(rows[0][2], rows[0], unknowns, work)
    _, r, c = min(options)
    name, other = unknowns[c], unknowns[1 - c]
    source, target = rows[r], rows[1 - r]
    expression = sp.expand((source[2] - source[1 - c] * other) / source[c])
    work.equation(f"Solve the {_ORDINALS[r]} equation for {name}", Equation(name, expression))

    substituted = Equation(
        sp.expand(target[c] * expression + target[1 - c] * other), target[2]
    )
    work.equation(
        f"Substitute {name} = {show(expression)} into the {_ORDINALS[1 - r]} equation",
        substituted,
    )
    if not substituted.lhs.has(other):
        return _degenerate(sp.expand(substituted.rhs - substituted.lhs), source, unknowns, work)
    found = dispatch.solve_equation(substituted, other, work)
    value = found.values[0]
    answer = sp.simplify(expression.subs(other, value))
    work.equation(
        f"Put {other} = {show(value)} into {name} = {show(expression)}", Equation(name, answer)
    )
    found_values = {name: answer, other: value}
    return [{unknown: found_values[unknown] for unknown in unknowns}], []


def _back_substitute(row, unknowns, known, value, work, which):
    unknown = unknowns[0] if known == unknowns[1] else unknowns[1]
    equation = _row_equation(row, unknowns)
    placed = Equation(equation.lhs.subs(known, value), equation.rhs)
    work.equation(f"Put {known} = {show(value)} into the {which} equation", placed)
    found = dispatch.solve_equation(placed, unknown, work)
    answer = {known: value, unknown: found.values[0]}
    return [{name: answer[name] for name in unknowns}], []


def _degenerate(constant, row, unknowns, work):
    """After eliminating, ``0 = constant``: no solution, or infinitely many."""
    if constant != 0:
        work.note(
            f"This says 0 = {show(constant)}, which is impossible: the equations "
            "contradict each other (for two unknowns: parallel lines), so there is no solution"
        )
        return [], []
    work.note(
        "This says 0 = 0, which is always true: one equation is a multiple of the "
        "other (for two unknowns: the same line), so there are infinitely many solutions"
    )
    return _parametric([row], unknowns, work)


def _parametric(rows, unknowns, work):
    """Write the first unknown of the remaining equation in terms of the others."""
    row = next(r for r in rows if any(entry != 0 for entry in r[:-1]))
    index = next(i for i, entry in enumerate(row[:-1]) if entry != 0)
    name = unknowns[index]
    free = [other for other in unknowns if other != name]
    rest = sum(row[i] * unknowns[i] for i in range(len(unknowns)) if i != index)
    expression = sp.expand((row[-1] - rest) / row[index])
    work.equation(
        f"Solve for {name}; {', '.join(map(str, free))} can be anything", Equation(name, expression)
    )
    assignment = {other: other for other in unknowns}
    assignment[name] = expression
    return [assignment], free


# ---------------------------------------------------------------- matrices


def _gaussian(rows, unknowns, work):
    augmented = sp.Matrix(rows)
    work.solution.add(
        "Write the augmented matrix [A | b]: the coefficients, then the right-hand sides",
        matrix=augmented,
    )
    reduced, pivots = reduce_rows(sp.Matrix(augmented), work.solution)
    width = len(unknowns)
    if width in pivots:
        row = pivots.index(width)
        work.note(
            f"Row {row + 1} now says 0 = {show(reduced[row, width])}, which is impossible, "
            "so there is no solution"
        )
        return [], []

    free = [unknowns[column] for column in range(width) if column not in pivots]
    assignment = {name: name for name in unknowns}
    for row, column in enumerate(pivots):
        others = sum(reduced[row, k] * unknowns[k] for k in range(width) if k not in pivots)
        assignment[unknowns[column]] = sp.expand(reduced[row, width] - others)
    text = "Read the solution off the reduced matrix"
    if free:
        text += f" ({', '.join(map(str, free))} can be anything)"
    pinned = [name for name in unknowns if name not in free]
    work.show(
        text,
        ", ".join(f"{name} = {show(assignment[name])}" for name in pinned),
        r",\quad ".join(f"{latex_of(name)} = {latex_of(assignment[name])}" for name in pinned),
    )
    return [assignment], free


def _matrix_form(rows, unknowns, work):
    matrix = sp.Matrix([row[:-1] for row in rows])
    right = sp.Matrix([row[-1] for row in rows])
    vector = sp.Matrix(unknowns)
    work.show(
        "Write the system as a matrix equation A x = b",
        f"A =\n{format_matrix(matrix)}\nb =\n{format_matrix(right)}",
        f"{latex_of(matrix)} {latex_of(vector)} = {latex_of(right)}",
    )
    return matrix, right


def _cramer(rows, unknowns, work):
    matrix, right = _matrix_form(rows, unknowns, work)
    determinant = matrix.det()
    work.show(
        "Work out the determinant of A",
        f"D = {show(determinant)}",
        rf"D = \det {latex_of(matrix)} = {latex_of(determinant)}",
    )
    assignment = {}
    for column, name in enumerate(unknowns):
        replaced = matrix.copy()
        replaced[:, column] = right
        value = replaced.det()
        work.show(
            f"Replace the {name} column with b and take the determinant",
            f"D_{name} = {show(value)}",
            rf"D_{{{latex_of(name)}}} = \det {latex_of(replaced)} = {latex_of(value)}",
        )
        assignment[name] = sp.simplify(value / determinant)
    work.show(
        "Divide each by D",
        ", ".join(f"{name} = D_{name} / D = {show(assignment[name])}" for name in unknowns),
        r",\quad ".join(
            rf"{latex_of(name)} = \frac{{D_{{{latex_of(name)}}}}}{{D}} "
            rf"= {latex_of(assignment[name])}"
            for name in unknowns
        ),
    )
    return [assignment], []


def _inverse(rows, unknowns, work):
    matrix, right = _matrix_form(rows, unknowns, work)
    inverse = matrix.inv()
    work.solution.add("A is invertible, so x = A^-1 b; the inverse of A is", matrix=inverse)
    result = inverse * right
    work.solution.add("Multiply A^-1 by b", matrix=result)
    return [{name: sp.simplify(result[i]) for i, name in enumerate(unknowns)}], []


# ---------------------------------------------------------------- the check


def _check(equations: list[Equation], assignment: dict, work: Work) -> None:
    parts = []
    parts_latex = []
    for index, equation in enumerate(equations, start=1):
        left = sp.simplify(equation.lhs.subs(assignment))
        right = sp.simplify(equation.rhs.subs(assignment))
        mark = "OK" if sp.simplify(left - right) == 0 else "does not hold"
        parts.append(f"equation {index}: {show(left)} = {show(right)} {mark}")
        parts_latex.append(rf"{latex_of(left)} = {latex_of(right)}")
    work.show(
        "Check: put the solution into every original equation",
        "\n".join(parts),
        r"\begin{cases} " + r" \\ ".join(parts_latex) + r" \end{cases}",
    )
