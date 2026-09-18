"""Nonlinear systems in two unknowns.

* substitution — when one equation is linear in one unknown (``x + y = 5``,
  ``y = x^2``, ``xy = 6``), solve it for that unknown and put the result into the
  other equation, which leaves one equation in one unknown;
* squares as unknowns — when both unknowns only ever appear squared
  (``x^2 + y^2 = 25``, ``x^2 - y^2 = 7``), write ``u = x^2``, ``v = y^2``, solve the
  linear system, and take square roots.

Anything else is solved by SymPy and labelled as such. Every pair is checked in
both original equations, so a pair that divides by zero or does not fit is
rejected with the reason.
"""

from __future__ import annotations

import itertools

import sympy as sp

from ..errors import UnsupportedError
from ..parse.plain import latex_of
from . import dispatch
from .core import Equation, Work, show
from .system import _ORDINALS, SystemSolution, _elimination, _show_system

_TOLERANCE = sp.Float("1e-12")


def solve_nonlinear(
    equations: list[Equation], unknowns: list[sp.Symbol], method: str | None
) -> SystemSolution:
    if len(unknowns) != 2 or len(equations) != 2:
        raise UnsupportedError(
            "systems with squares, products or functions of the unknowns are solved "
            "for two equations in two unknowns for now"
        )
    methods = _methods(equations, unknowns)
    if method is not None and method not in methods:
        raise UnsupportedError(
            f"the method '{method}' does not apply here — try {', '.join(methods)}"
        )
    chosen = method or methods[0]
    solution = SystemSolution(
        operation="solve",
        title="Solve the system",
        kind="nonlinear-system",
        method=chosen,
        methods=methods,
        unknowns=list(unknowns),
    )
    work = Work(solution, unknowns[0])
    _show_system(work, "Start from", equations)

    solver = {
        "substitution": _by_substitution,
        "squares": _by_squares,
        "computer": _by_computer,
    }[chosen]
    candidates = solver(equations, unknowns, work)
    kept = _check_all(equations, unknowns, candidates, work)
    solution.finish(kept, [])
    return solution


def _methods(equations: list[Equation], unknowns: list[sp.Symbol]) -> list[str]:
    methods = []
    if _best_isolation(equations, unknowns) is not None:
        methods.append("substitution")
    if _only_squares(equations, unknowns):
        methods.append("squares")
    return methods or ["computer"]


# ---------------------------------------------------------------- substitution


def _best_isolation(
    equations: list[Equation], unknowns: list[sp.Symbol]
) -> tuple[int, sp.Symbol, sp.Expr] | None:
    """The equation and unknown that are easiest to solve for: (index, unknown, value)."""
    options = []
    for index, equation in enumerate(equations):
        expr = sp.expand(equation.lhs - equation.rhs)
        for position, name in enumerate(unknowns):
            if not expr.is_polynomial(name) or sp.degree(expr, name) != 1:
                continue
            coefficient = expr.coeff(name, 1)
            if coefficient == 0:
                continue
            # dividing by 1 is free, by a number cheap, by an unknown needs a condition
            cost = 2 if coefficient.has(*unknowns) else 0 if abs(coefficient) == 1 else 1
            value = sp.simplify(-(expr - coefficient * name) / coefficient)
            # prefer the later unknown on a tie: y = 5 - x reads more naturally than x = 5 - y
            options.append((cost, -position, index, name, value))
    if not options:
        return None
    cost, _, index, name, value = min(options, key=lambda option: option[:3])
    return index, name, value


def _by_substitution(equations, unknowns, work):
    index, name, value = _best_isolation(equations, unknowns)
    other = unknowns[0] if name == unknowns[1] else unknowns[1]
    source, target = equations[index], equations[1 - index]

    text = f"Solve the {_ORDINALS[index]} equation for {name}"
    denominator = sp.fraction(sp.together(value))[1]
    if denominator.has(other):
        text += f" ({show(denominator)} must not be 0)"
    if not (source.lhs == name and not source.rhs.has(name)):
        work.equation(text, Equation(name, value))

    substituted = Equation(target.lhs.subs(name, value), target.rhs.subs(name, value))
    work.equation(
        f"Substitute {name} = {show(value)} into the {_ORDINALS[1 - index]} equation",
        substituted,
    )
    found = dispatch.solve_equation(substituted, other, work)
    if found.everything or found.solution_set is not None:
        return _by_computer(equations, unknowns, work)

    pairs = []
    for other_value in found.values:
        pairs.append({other: other_value, name: sp.simplify(value.subs(other, other_value))})
    if pairs:
        work.show(
            f"Put each value back into {name} = {show(value)}",
            "\n".join(f"{other} = {show(p[other])}: {name} = {show(p[name])}" for p in pairs),
            r"\begin{cases} "
            + r" \\ ".join(
                rf"{latex_of(other)} = {latex_of(p[other])}:\ "
                rf"{latex_of(name)} = {latex_of(p[name])}"
                for p in pairs
            )
            + r" \end{cases}",
        )
    return [{unknown: pair[unknown] for unknown in unknowns} for pair in pairs]


# ---------------------------------------------------------------- squares


def _only_squares(equations: list[Equation], unknowns: list[sp.Symbol]) -> bool:
    for equation in equations:
        expr = sp.expand(equation.lhs - equation.rhs)
        if not expr.is_polynomial(*unknowns):
            return False
        for powers in sp.Poly(expr, *unknowns).monoms():
            if any(power not in (0, 2) for power in powers) or sum(powers) > 2:
                return False
    return True


def _by_squares(equations, unknowns, work):
    letters = [sp.Symbol(letter) for letter in ("u", "v", "p", "q")]
    names = [letter for letter in letters if letter not in unknowns]
    first, second = names[:2]
    squares = {unknowns[0] ** 2: first, unknowns[1] ** 2: second}
    rewritten = [
        Equation(sp.expand(eq.lhs).xreplace(squares), sp.expand(eq.rhs).xreplace(squares))
        for eq in equations
    ]
    _show_system(
        work,
        f"Both unknowns only appear squared, so write {first} = {unknowns[0]}^2 and "
        f"{second} = {unknowns[1]}^2: that is a linear system",
        rewritten,
    )
    matrix, right = sp.linear_eq_to_matrix([eq.lhs - eq.rhs for eq in rewritten], [first, second])
    rows = [list(matrix.row(i)) + [right[i]] for i in range(matrix.rows)]
    assignments, free = _elimination(rows, [first, second], work)
    if not assignments or free:
        return [] if not assignments else _by_computer(equations, unknowns, work)

    values = assignments[0]
    roots = []
    for square, name in ((first, unknowns[0]), (second, unknowns[1])):
        value = values[square]
        if value.is_negative:
            work.note(
                f"{name}^2 = {show(value)} is impossible, because a square is never negative, "
                "so there is no real solution"
            )
            return []
        root = sp.sqrt(value)
        roots.append([root] if root == 0 else [-root, root])
    work.show(
        "Take square roots (each can be positive or negative)",
        f"{unknowns[0]} = +/-{show(roots[0][-1])}, {unknowns[1]} = +/-{show(roots[1][-1])}",
        rf"{latex_of(unknowns[0])} = \pm {latex_of(roots[0][-1])},\quad "
        rf"{latex_of(unknowns[1])} = \pm {latex_of(roots[1][-1])}",
    )
    return [
        {unknowns[0]: a, unknowns[1]: b} for a, b in itertools.product(roots[0], roots[1])
    ]


# ---------------------------------------------------------------- fallback and check


def _by_computer(equations, unknowns, work):
    work.note(
        "mathlint has no by-hand method for this system yet, so SymPy solves it"
    )
    try:
        found = sp.solve([sp.Eq(eq.lhs, eq.rhs) for eq in equations], unknowns, dict=True)
    except Exception:
        work.note("SymPy could not solve it either")
        return []
    pairs = []
    for candidate in found:
        if set(candidate) != set(unknowns):
            continue
        if all(value.is_real is not False for value in candidate.values()):
            pairs.append({unknown: candidate[unknown] for unknown in unknowns})
    return pairs


def _check_all(equations, unknowns, candidates, work):
    kept = []
    seen = []
    for candidate in candidates:
        if any(all(sp.simplify(candidate[u] - other[u]) == 0 for u in unknowns) for other in seen):
            continue
        seen.append(candidate)
        label = "Check " + ", ".join(f"{u} = {show(candidate[u])}" for u in unknowns)
        reason = _problem(equations, candidate)
        if reason is None:
            work.note(f"{label}: both equations hold")
            kept.append(candidate)
        else:
            work.note(f"{label}: {reason}, so it is not a solution")
    try:
        return sorted(kept, key=lambda pair: tuple(float(pair[u]) for u in unknowns))
    except TypeError:
        return kept


def _problem(equations, candidate) -> str | None:
    for index, equation in enumerate(equations, start=1):
        left = sp.simplify(equation.lhs.subs(candidate))
        right = sp.simplify(equation.rhs.subs(candidate))
        if left.has(sp.zoo, sp.nan) or right.has(sp.zoo, sp.nan):
            return f"equation {index} would divide by zero"
        if sp.simplify(left - right) == 0:
            continue
        difference = sp.N(left - right, 30)
        if difference.is_number and abs(difference) < _TOLERANCE:
            continue
        return f"equation {index} gives {show(left)} on the left but {show(right)} on the right"
    return None

