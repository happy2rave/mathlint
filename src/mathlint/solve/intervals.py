"""Sets of real numbers the way a student writes them.

The same answer three ways: ``x < -2 or x >= 3``, ``(-inf, -2) U [3, inf)``, and
the pieces a number line is drawn from.
"""

from __future__ import annotations

import sympy as sp

from ..parse.plain import latex_of, read_as

INFINITY_PLAIN = "inf"


def pieces(solution: sp.Set) -> list[sp.Set]:
    """The intervals and single points of ``solution``, left to right."""
    parts = list(solution.args) if isinstance(solution, sp.Union) else [solution]
    flat: list[sp.Set] = []
    for part in parts:
        if isinstance(part, sp.FiniteSet):
            flat.extend(sp.FiniteSet(point) for point in part)
        elif part is not sp.S.EmptySet:
            flat.append(part)
    return sorted(flat, key=_left)


def _left(part: sp.Set) -> float:
    start = part.inf
    return float("-inf") if start == -sp.oo else float(start)


def _missing_points(solution: sp.Set) -> list[sp.Expr] | None:
    """For every real number except a few points, those points; otherwise None."""
    parts = pieces(solution)
    if not parts or any(not isinstance(part, sp.Interval) for part in parts):
        return None
    if parts[0].start != -sp.oo or parts[-1].end != sp.oo:
        return None
    missing = []
    for left, right in zip(parts, parts[1:], strict=False):
        if left.end != right.start or not (left.right_open and right.left_open):
            return None
        missing.append(left.end)
    return missing or None


def as_inequality(variable: sp.Symbol, solution: sp.Set) -> tuple[str, str]:
    """``x < -2 or x >= 3`` in plain text and in LaTeX."""
    name, name_latex = str(variable), latex_of(variable)
    if solution == sp.S.Reals:
        return "every real number", rf"{name_latex} \in \mathbb{{R}}"
    if solution == sp.S.EmptySet:
        return "no real solution", r"\text{no real solution}"
    missing = _missing_points(solution)
    if missing:
        plain = " and ".join(f"{name} != {read_as(point)}" for point in missing)
        latex = r" \text{ and } ".join(rf"{name_latex} \neq {latex_of(point)}" for point in missing)
        return plain, latex
    plain_parts, latex_parts = [], []
    for part in pieces(solution):
        if isinstance(part, sp.FiniteSet):
            (point,) = part
            plain_parts.append(f"{name} = {read_as(point)}")
            latex_parts.append(f"{name_latex} = {latex_of(point)}")
            continue
        left = None if part.start == -sp.oo else part.start
        right = None if part.end == sp.oo else part.end
        if left is None and right is None:
            plain_parts.append("every real number")
            latex_parts.append(rf"{name_latex} \in \mathbb{{R}}")
        elif left is None:
            op = "<" if part.right_open else "<="
            plain_parts.append(f"{name} {op} {read_as(right)}")
            latex_parts.append(f"{name_latex} {_LATEX[op]} {latex_of(right)}")
        elif right is None:
            op = ">" if part.left_open else ">="
            plain_parts.append(f"{name} {op} {read_as(left)}")
            latex_parts.append(f"{name_latex} {_LATEX[op]} {latex_of(left)}")
        else:
            left_op = "<" if part.left_open else "<="
            right_op = "<" if part.right_open else "<="
            plain_parts.append(f"{read_as(left)} {left_op} {name} {right_op} {read_as(right)}")
            latex_parts.append(
                f"{latex_of(left)} {_LATEX[left_op]} {name_latex} "
                f"{_LATEX[right_op]} {latex_of(right)}"
            )
    return " or ".join(plain_parts), r" \quad\text{or}\quad ".join(latex_parts)


def as_intervals(solution: sp.Set) -> tuple[str, str]:
    """``(-inf, -2) U [3, inf)`` in plain text and in LaTeX."""
    if solution == sp.S.EmptySet:
        return "{}", r"\varnothing"
    plain_parts, latex_parts = [], []
    for part in pieces(solution):
        if isinstance(part, sp.FiniteSet):
            (point,) = part
            plain_parts.append(f"{{{read_as(point)}}}")
            latex_parts.append(rf"\left\{{{latex_of(point)}\right\}}")
            continue
        opening = "(" if part.left_open or part.start == -sp.oo else "["
        closing = ")" if part.right_open or part.end == sp.oo else "]"
        left_plain, left_latex = _end(part.start)
        right_plain, right_latex = _end(part.end)
        plain_parts.append(f"{opening}{left_plain}, {right_plain}{closing}")
        latex_parts.append(rf"\left{opening}{left_latex}, {right_latex}\right{closing}")
    return " U ".join(plain_parts), r" \cup ".join(latex_parts)


def _end(value: sp.Expr) -> tuple[str, str]:
    if value == sp.oo:
        return INFINITY_PLAIN, r"\infty"
    if value == -sp.oo:
        return f"-{INFINITY_PLAIN}", r"-\infty"
    return read_as(value), latex_of(value)


def number_line(solution: sp.Set) -> dict:
    """What the web page needs to draw the answer on a number line."""
    intervals, points = [], []
    for part in pieces(solution):
        if isinstance(part, sp.FiniteSet):
            (point,) = part
            points.append({"at": float(point), "label": latex_of(point)})
            continue
        intervals.append(
            {
                "from": None if part.start == -sp.oo else float(part.start),
                "to": None if part.end == sp.oo else float(part.end),
                "from_closed": part.start != -sp.oo and not part.left_open,
                "to_closed": part.end != sp.oo and not part.right_open,
                "from_label": None if part.start == -sp.oo else latex_of(part.start),
                "to_label": None if part.end == sp.oo else latex_of(part.end),
            }
        )
    return {"intervals": intervals, "points": points}


def same_set(first: sp.Set, second: sp.Set) -> bool:
    """Equal as sets of real numbers, allowing different ways of writing the ends."""
    if first == second:
        return True
    left, right = pieces(first), pieces(second)
    if len(left) != len(right):
        return False
    for a, b in zip(left, right, strict=True):
        if isinstance(a, sp.FiniteSet) != isinstance(b, sp.FiniteSet):
            return False
        if not (_close(a.inf, b.inf) and _close(a.sup, b.sup)):
            return False
        if isinstance(a, sp.Interval) and (
            a.left_open != b.left_open or a.right_open != b.right_open
        ):
            return False
    return True


def _close(a: sp.Expr, b: sp.Expr) -> bool:
    if a == b:
        return True
    if a.is_infinite or b.is_infinite:
        return False
    return abs(float(a) - float(b)) < 1e-9 * max(1.0, abs(float(a)))


_LATEX = {"<": "<", "<=": r"\le", ">": ">", ">=": r"\ge"}
