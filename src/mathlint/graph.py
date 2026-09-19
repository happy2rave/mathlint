"""What to draw under an answer, and the points to draw it with.

``graph_for`` looks at what was solved and describes a graph: the curves (as
text the plain parser reads back, so the page can ask for more points later),
the points to mark, the stretches of the x-axis to shade, and a first view that
shows all of it. ``sample`` evaluates the curves across any range of x.
"""

from __future__ import annotations

import math
import re

import sympy as sp

from .parse.plain import latex_of, parse_expression, read_as

SAMPLES = 400
MAX_CURVES = 6
DEFAULT_VIEW = (-10.0, 10.0)


def graph_for(text: str, result) -> dict | None:
    """A graph for a solved problem, or None when there is nothing sensible to draw."""
    try:
        return _graph_for(text, result)
    except Exception:  # a graph is a bonus: never let it break the answer
        return None


def _graph_for(text: str, result) -> dict | None:
    from .calc.computation import Computation
    from .solve import EquationSolution, InequalitySolution, SystemSolution

    if isinstance(result, EquationSolution):
        return _equation(text, result)
    if isinstance(result, InequalitySolution):
        return _inequality(text, result)
    if isinstance(result, SystemSolution):
        return _system(text, result)
    if isinstance(result, Computation) and result.kind in ("expression", "analysis"):
        return _expression(result)
    return None


# --- what each kind of answer draws --------------------------------------------------------


def _equation(text: str, solution) -> dict | None:
    from .solve import parse_equation
    from .solve.api import _FOR_SUFFIX

    if len(solution.letters) != 1 or solution.everything or solution.solution_set is not None:
        return None
    equation = parse_equation(_FOR_SUFFIX.sub("", text))
    x = solution.variable
    sides = [equation.lhs] if equation.rhs == 0 else [equation.lhs, equation.rhs]
    marks = []
    for value in solution.answers:
        point = _point(value, equation.lhs, x)
        if point is not None:
            marks.append({**point, "closed": True})
    return _spec(x, sides, marks=marks)


def _inequality(text: str, solution) -> dict | None:
    from .solve.inequality import parse_inequality
    from .solve.intervals import pieces

    if len(solution.letters) != 1:
        return None
    inequalities = parse_inequality(text)
    x = solution.variable
    first = inequalities[0]
    sides = [first.lhs] if first.rhs == 0 and len(inequalities) == 1 else [first.lhs, first.rhs]
    if len(inequalities) == 2:
        sides.append(inequalities[1].rhs)
    shade, marks = [], []
    for part in pieces(solution.answer):
        if isinstance(part, sp.FiniteSet):
            (value,) = part
            point = _point(value, sides[0], x)
            if point is not None:
                marks.append({**point, "closed": True})
            shade.append({"from": float(value), "to": float(value)})
            continue
        shade.append(
            {
                "from": None if part.start == -sp.oo else float(part.start),
                "to": None if part.end == sp.oo else float(part.end),
            }
        )
        for end, is_open in ((part.start, part.left_open), (part.end, part.right_open)):
            if end.is_infinite:
                continue
            point = _point(end, sides[0], x)
            if point is not None:
                marks.append({**point, "closed": not is_open})
    if solution.answer == sp.S.Reals:
        shade = [{"from": None, "to": None}]
    return _spec(x, sides, marks=marks, shade=shade)


def _system(text: str, solution) -> dict | None:
    from .solve import parse_equation
    from .solve.system import split_equations

    if len(solution.unknowns) != 2 or solution.free:
        return None
    x, y = solution.unknowns
    curves, vertical = [], []
    for part in split_equations(text):
        equation = parse_equation(part)
        if not equation.expr.has(y):
            vertical.extend(
                float(value)
                for value in sp.solve(equation.expr, x)
                if value.is_real and value.is_number
            )
            continue
        branches = [branch for branch in sp.solve(equation.expr, y) if not branch.has(y)]
        curves.extend(branch for branch in branches if branch.free_symbols <= {x})
    marks = []
    for assignment in solution.assignments:
        a, b = assignment.get(x), assignment.get(y)
        if a is not None and b is not None and _real(a) and _real(b):
            marks.append(
                {"x": float(a), "y": float(b), "label": _pair(float(a), float(b)), "closed": True}
            )
    return _spec(x, curves, marks=marks, vertical=vertical, y_name=str(y))


def _expression(computation) -> dict | None:
    if len(computation.letters) != 1:
        return None
    x = sp.Symbol(computation.letters[0])
    function = computation.answer
    marks = []
    if computation.marks:
        # an analysis: its intercepts, extrema and inflection points, one label per point
        grouped: dict[tuple[float, float], list[str]] = {}
        for point in computation.marks:
            key = (round(point["x"], 9), round(point["y"], 9))
            if point["what"] not in grouped.setdefault(key, []):
                grouped[key].append(point["what"])
        for (a, b), what in grouped.items():
            label = f"{', '.join(what)} {_pair(a, b)}"
            marks.append({"x": a, "y": b, "label": label, "closed": True})
        return _spec(x, [function], marks=marks)
    if function.is_polynomial(x):
        # where it crosses the x-axis, which also puts the interesting part in view
        for root in sp.real_roots(sp.Poly(function, x)):
            point = _point(root, function, x)
            if point is not None:
                marks.append({**point, "closed": True})
    return _spec(x, [function], marks=marks)


# --- the description and its first view ----------------------------------------------


def _spec(x, curves, marks=(), shade=(), vertical=(), y_name="y") -> dict | None:
    curves = [curve for curve in curves if curve.free_symbols <= {x}][:MAX_CURVES]
    if not curves and not vertical:
        return None
    texts = [_text(curve) for curve in curves]
    x_min, x_max = _x_range(marks, shade, vertical)
    samples = sample(texts, str(x), x_min, x_max, count=200)
    y_min, y_max = _y_range(samples["curves"], marks)
    data = {
        "variable": str(x),
        "curves": [
            {"expr": text, "latex": f"{y_name} = {latex_of(curve)}"}
            for text, curve in zip(texts, curves, strict=True)
        ],
        "vertical": [
            {"x": value, "latex": f"{latex_of(x)} = {_number(value)}"} for value in vertical
        ],
        "marks": list(marks),
        "shade": list(shade),
        "view": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
    }
    data["samples"] = sample(texts, str(x), x_min, x_max)
    return data


def _x_range(marks, shade, vertical) -> tuple[float, float]:
    xs = [mark["x"] for mark in marks]
    xs += [end for part in shade for end in (part["from"], part["to"]) if end is not None]
    xs += list(vertical)
    xs = [value for value in xs if math.isfinite(value)]
    if not xs:
        return DEFAULT_VIEW
    low, high = min(xs), max(xs)
    pad = max(3.0, (high - low) * 0.4)
    return _nice(low - pad), _nice(high + pad)


def _y_range(curves, marks) -> tuple[float, float]:
    ys = sorted(value for curve in curves for value in curve if value is not None)
    if ys:
        # the middle 90%, so an asymptote does not squash everything flat
        low, high = ys[int(len(ys) * 0.05)], ys[int(len(ys) * 0.95) - 1 if len(ys) > 1 else 0]
    else:
        low, high = DEFAULT_VIEW
    for mark in marks:
        low, high = min(low, mark["y"]), max(high, mark["y"])
    low, high = min(low, 0.0), max(high, 0.0)
    span = max(high - low, 2.0)
    return _nice(low - span * 0.15), _nice(high + span * 0.15)


def _nice(value: float) -> float:
    return float(round(value, 2))


# --- evaluating --------------------------------------------------------------------------


def sample(
    curves: list[str], variable: str, x_min: float, x_max: float, count: int = SAMPLES
) -> dict:
    """Each curve's y at ``count`` evenly spaced x values; None where it is not defined."""
    count = max(2, min(int(count), 2000))
    x_min, x_max = float(x_min), float(x_max)
    if not (math.isfinite(x_min) and math.isfinite(x_max)) or x_max <= x_min:
        raise ValueError("the range of x must go from a smaller to a larger number")
    x = sp.Symbol(variable)
    xs = [x_min + (x_max - x_min) * index / (count - 1) for index in range(count)]
    values = []
    for text in curves[:MAX_CURVES]:
        expression = parse_expression(text).expr
        function = sp.lambdify(x, expression, modules=["math"])
        values.append([_evaluate(function, value) for value in xs])
    return {"xs": xs, "curves": values}


def _evaluate(function, value: float) -> float | None:
    try:
        result = function(value)
    except (ArithmeticError, ValueError, TypeError):
        return None
    if isinstance(result, complex):
        return None
    try:
        result = float(result)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _point(value: sp.Expr, curve: sp.Expr, x: sp.Symbol) -> dict | None:
    if not _real(value):
        return None
    height = curve.subs(x, value)
    if not _real(height):
        return None
    a, b = float(value), float(height)
    return {"x": a, "y": b, "label": _pair(a, b)}


def _real(value: sp.Expr) -> bool:
    try:
        number = complex(sp.N(value))
    except (TypeError, ValueError):
        return False
    return abs(number.imag) < 1e-12 and math.isfinite(number.real)


def _pair(a: float, b: float) -> str:
    return f"({_number(a)}, {_number(b)})"


def _number(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _text(curve: sp.Expr) -> str:
    """The curve in the plain notation ``parse_expression`` reads back."""
    text = read_as(curve)
    if curve.has(sp.E):
        text = re.sub(r"\bE\b", "e", text)
    return text
