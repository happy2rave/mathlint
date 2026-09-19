"""``mathlint.compute``: work out anything that has no ``=`` sign."""

from __future__ import annotations

import sympy as sp

from ..errors import MathlintError, ParseError, UnsupportedError
from ..parse.plain import latex_of, parse_expression, read_as
from ..steps.calculus import differentiate_solution, integrate_solution
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
    if "=" in text:
        raise ParseError("this is an equation — use solve for it")
    try:
        tree = read_arithmetic(text)
    except NotArithmetic:
        return _calculus(text) or compute_expression(text, method)
    if method not in (None, "calculate"):
        raise UnsupportedError(f"the method '{method}' does not apply here — try calculate")
    return calculate(tree)


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
    if isinstance(expression, sp.Derivative) and expression.derivative_count == 1:
        variable = expression.variables[0]
        solution = differentiate_solution(expression.expr, variable)
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
