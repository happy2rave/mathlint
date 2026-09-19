"""``mathlint.compute``: work out anything that has no ``=`` sign."""

from __future__ import annotations

import sympy as sp

from ..errors import MathlintError, ParseError, UnsupportedError
from ..parse.plain import latex_of, parse_expression, read_as
from ..steps.calculus import differentiate_solution, integrate_solution
from ..steps.derivatives import (
    higher_derivative_solution,
    implicit_solution,
    looks_like_implicit,
    looks_like_tangent,
    tangent_solution,
)
from ..steps.limits import DOES_NOT_EXIST, limit_solution, looks_like_limit, parse_limit
from ..steps.solution import SolutionStep
from .arithmetic import value_of, work_out
from .computation import Computation
from .expression import compute_expression
from .reader import NotArithmetic, read_arithmetic
from .tree import Num, latex, plain


def compute(text: str, method: str | None = None) -> Computation:
    """Work out a calculation or an expression, showing every step.

    A calculation (numbers only) is worked out in the order of operations, with
    fractions, decimals, percentages, powers and roots done the way they are
    taught. The answer is exact, with a decimal alongside when they differ.

    An expression with letters is simplified, expanded or factored; ``method``
    picks one of the result's ``methods``, and by default brackets are
    multiplied out, a polynomial without brackets is factored, and anything
    else is simplified.
    """
    if looks_like_limit(text):
        return _limit(text)
    if looks_like_tangent(text):
        return _tangent(text)
    if looks_like_implicit(text):
        return _implicit(text)
    if "=" in text:
        raise ParseError("this is an equation — use solve for it")
    try:
        tree = read_arithmetic(text)
    except NotArithmetic:
        return _calculus(text) or compute_expression(text, method)
    if method not in (None, "calculate"):
        raise UnsupportedError(f"the method '{method}' does not apply here — try calculate")
    return calculate(tree)


def analyze_function(text: str) -> Computation:
    """Domain, intercepts, asymptotes, rising and falling, extrema, bending and
    inflection points of a function of one letter, each with its reason."""
    return compute(text, method="analyze")


def calculate(tree) -> Computation:
    computation = Computation(
        operation="calculate",
        title=f"Calculate {plain(tree)}",
        kind="arithmetic",
        method="calculate",
        methods=["calculate"],
    )
    expected = sp.nsimplify(value_of(tree)) if value_of(tree).has(sp.Float) else value_of(tree)
    computation.steps.append(_step("Start from", tree))
    try:
        rounds, final = work_out(tree)
    except UnsupportedError:
        rounds, final = [], None
    if not isinstance(final, Num) or not _same(final.value, expected):
        # never show steps that do not add up: the checked answer alone instead
        answer = sp.simplify(expected)
        computation.steps.append(_step_value("Calculate", answer))
        computation.finish(answer)
        return computation
    computation.steps.extend(_step(one.text, one.tree) for one in rounds)
    computation.finish(final.value, plain(final), latex(final))
    return computation


def _calculus(text: str) -> Computation | None:
    """``d/dx [...]`` and ``int ... dx`` go to the derivative and integral steps."""
    try:
        expression = parse_expression(text).expr
    except MathlintError:
        return None
    lower = upper = None
    if isinstance(expression, sp.Derivative) and len(expression.variable_count) == 1:
        variable, order = expression.variable_count[0]
        if order == 1:
            solution = differentiate_solution(expression.expr, variable)
        else:
            solution = higher_derivative_solution(expression.expr, variable, int(order))
        kind = "derivative"
    elif isinstance(expression, sp.Integral) and len(expression.limits) == 1:
        variable, *bounds = expression.limits[0]
        if bounds:
            lower, upper = bounds
        solution = integrate_solution(expression.function, variable, lower=lower, upper=upper)
        kind = "integral"
    else:
        return None
    computation = Computation(
        operation=solution.operation,
        title=solution.title,
        kind=kind,
        method=kind,
        methods=[kind],
        letters=sorted(symbol.name for symbol in expression.free_symbols | {variable}),
    )
    computation.steps = list(solution.steps)
    result = solution.result
    if kind == "integral" and lower is None:
        computation.finish(result, f"{read_as(result)} + C", f"{latex_of(result)} + C")
    else:
        computation.finish(result)
    return computation


def _limit(text: str) -> Computation:
    problem = parse_limit(text)
    assert problem is not None
    solution = limit_solution(problem)
    computation = Computation(
        operation="limit",
        title=solution.title,
        kind="limit",
        method="limit",
        methods=["limit"],
        letters=sorted(symbol.name for symbol in problem.expression.free_symbols),
    )
    computation.steps = list(solution.steps)
    value = solution.result
    if value is DOES_NOT_EXIST:
        computation.finish(value, "does not exist", r"\text{does not exist}")
    elif value.is_infinite:
        computation.finish(value, "inf" if value == sp.oo else "-inf", latex_of(value))
    else:
        computation.finish(value)
    return computation


def _tangent(text: str) -> Computation:
    solution, curve, line, (a, b) = tangent_solution(text)
    kind = "normal" if solution.title.startswith("The normal") else "tangent"
    computation = Computation(
        operation=kind,
        title=solution.title,
        kind=kind,
        method=kind,
        methods=[kind],
        letters=sorted(symbol.name for symbol in curve.free_symbols),
    )
    computation.steps = list(solution.steps)
    computation.plot = [curve] if line is None else [curve, line]
    computation.marks.append({"x": float(a), "y": float(b), "what": "touches at"})
    left, right = solution.result.args
    # the equation of a line has no decimal to give
    computation.finish(
        solution.result,
        f"{read_as(left)} = {read_as(right)}",
        f"{latex_of(left)} = {latex_of(right)}",
    )
    return computation


def _implicit(text: str) -> Computation:
    solution = implicit_solution(text)
    computation = Computation(
        operation="implicit",
        title=solution.title,
        kind="implicit",
        method="implicit",
        methods=["implicit"],
        letters=["x", "y"],
    )
    computation.steps = list(solution.steps)
    computation.finish(
        solution.result,
        f"dy/dx = {read_as(solution.result)}",
        rf"\frac{{dy}}{{dx}} = {latex_of(solution.result)}",
    )
    return computation


def _step(text: str, tree) -> SolutionStep:
    return SolutionStep(text=text, display=plain(tree), display_latex=latex(tree))


def _step_value(text: str, value: sp.Expr) -> SolutionStep:
    return SolutionStep(text=text, expression=value)


def _same(found: sp.Expr, expected: sp.Expr) -> bool:
    difference = sp.simplify(found - expected)
    if difference == 0:
        return True
    try:
        return abs(complex(sp.N(difference))) < 1e-9 * max(1.0, abs(complex(sp.N(expected))))
    except (TypeError, ValueError):
        return False
