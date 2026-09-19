"""More derivatives: higher orders, implicit differentiation, tangent and normal lines."""

from __future__ import annotations

import re

import sympy as sp
from sympy.core.parameters import distribute

from ..errors import ParseError
from ..parse.plain import latex_of, parse_expression, read_as
from .calculus import differentiate_solution
from .solution import Solution, SolutionStep

_ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
MAX_ORDER = 10

# "dy/dx: x^2 + y^2 = 25" or "y' for x y = 1": the separator is what tells it
# apart from a differential equation such as "dy/dx = 2y" or "y' + y = x"
_IMPLICIT = re.compile(
    r"^\s*(?:dy\s*/\s*dx|\\frac\s*\{\s*d\s*y\s*\}\s*\{\s*d\s*x\s*\}|y')\s*"
    r"(?::|,|\b(?:for|of)\b)\s*",
    re.IGNORECASE,
)
_TANGENT = re.compile(
    r"^\s*(?P<kind>tangent|normal)(?:\s+line)?(?:\s+(?:to|of))?(?:\s+the\s+curve)?\s+"
    r"(?:y\s*=\s*)?(?P<curve>.+?)\s+at\s+(?:x\s*=\s*)?(?P<point>.+?)\s*$",
    re.IGNORECASE,
)


def ordinal(n: int) -> str:
    return _ORDINALS.get(n, f"{n}th")


# --- higher orders ------------------------------------------------------------------------


def higher_derivative_solution(expression: sp.Expr, variable: sp.Symbol, order: int) -> Solution:
    """Differentiate ``order`` times, each time with the rules named."""
    if order > MAX_ORDER:
        raise ParseError(f"derivatives are worked out up to the {MAX_ORDER}th")
    solution = Solution(
        operation="diff",
        title=(
            f"The {ordinal(order)} derivative of {read_as(expression)} "
            f"with respect to {variable}"
        ),
    )
    solution.add("Start from", expression=sp.Derivative(expression, (variable, order)))
    current = expression
    for n in range(1, order + 1):
        single = differentiate_solution(current, variable)
        solution.add(
            f"The {ordinal(n)} derivative: differentiate {read_as(current)}",
            expression=sp.Derivative(current, variable),
        )
        solution.steps.extend(single.steps[1:])
        current = single.result
    solution.result = current
    solution.summary = f"d^{order}/d{variable}^{order} [{read_as(expression)}] = {read_as(current)}"
    return solution


# --- implicit differentiation --------------------------------------------------------------


def looks_like_implicit(text: str) -> bool:
    match = _IMPLICIT.match(text)
    # "y' = 2y" is a differential equation; "dy/dx: x^2 + y^2 = 25" asks for dy/dx
    return bool(match) and "=" in text and not text[match.end() :].lstrip().startswith("=")


def implicit_solution(text: str) -> Solution:
    """dy/dx for an equation in x and y, without solving it for y first."""
    from ..solve import parse_equation

    match = _IMPLICIT.match(text)
    if match is None:
        raise ParseError("start with dy/dx, like dy/dx: x^2 + y^2 = 25")
    equation = parse_equation(text[match.end() :])
    x, y = sp.Symbol("x"), sp.Symbol("y")
    letters = equation.lhs.free_symbols | equation.rhs.free_symbols
    if not {x, y} <= letters or letters - {x, y}:
        raise ParseError("implicit differentiation needs an equation in x and y")

    solution = Solution(operation="implicit", title=f"Find dy/dx for {_equation_plain(equation)}")
    solution.steps.append(_equation_step("Start from", equation.lhs, equation.rhs))

    curve = sp.Function("y")(x)
    slope = sp.Symbol("y'")
    sides = []
    for side in (equation.lhs, equation.rhs):
        derivative = sp.expand(side.subs(y, curve).diff(x))
        sides.append(derivative.subs(sp.Derivative(curve, x), slope).subs(curve, y))
    solution.steps.append(
        _equation_step(
            f"Differentiate both sides with respect to {x}. y depends on {x}, so the chain rule "
            "gives every y term a factor y' = dy/dx",
            *sides,
        )
    )
    moved = sp.expand(sides[0] - sides[1])
    coefficient = sp.expand(moved.coeff(slope))
    rest = sp.expand(moved - coefficient * slope)
    if coefficient == 0:
        raise ParseError("y' drops out, so this equation does not fix dy/dx")
    if sp.Poly(coefficient, x, y).LC() < 0:
        # a positive number in front of y' reads more easily
        coefficient, rest = -coefficient, -rest
    solution.steps.append(
        _equation_step(
            "Keep the y' terms on the left and move everything else to the right",
            sp.Mul(*sp.Mul.make_args(coefficient), slope, evaluate=False),
            -rest,
        )
    )
    answer = sp.factor(sp.cancel(-rest / coefficient))
    solution.steps.append(
        _equation_step(f"Divide both sides by {read_as(coefficient)}", slope, answer)
    )
    solution.result = answer
    solution.summary = f"dy/dx = {read_as(answer)}"
    return solution


def _equation_plain(equation) -> str:
    return f"{read_as(equation.lhs)} = {read_as(equation.rhs)}"


def _equation_step(text: str, left: sp.Expr, right: sp.Expr) -> SolutionStep:
    return SolutionStep(
        text=text,
        display=f"{read_as(left)} = {read_as(right)}",
        display_latex=f"{latex_of(left)} = {latex_of(right)}",
    )


# --- tangent and normal lines --------------------------------------------------------------


def looks_like_tangent(text: str) -> bool:
    return bool(_TANGENT.match(text))


def tangent_solution(text: str) -> tuple[Solution, sp.Expr, sp.Expr, tuple[sp.Expr, sp.Expr]]:
    """The tangent (or normal) line; also the curve, the line and the point, for a graph."""
    match = _TANGENT.match(text)
    if match is None:
        raise ParseError("write it like: tangent to y = x^2 at x = 1")
    kind = match.group("kind").lower()
    curve = parse_expression(match.group("curve")).expr
    point = parse_expression(match.group("point")).expr
    letters = curve.free_symbols
    if len(letters) != 1 or point.free_symbols:
        raise ParseError("give a curve y = f(x) in one letter, and a number to touch it at")
    (x,) = letters
    y = sp.Symbol("y")

    solution = Solution(
        operation="tangent",
        title=f"The {kind} line to y = {read_as(curve)} at {x} = {read_as(point)}",
    )
    height = sp.simplify(curve.subs(x, point))
    if not height.is_finite or height.is_real is False:
        raise ParseError(f"the curve is not defined at {x} = {read_as(point)}")
    solution.steps.append(
        SolutionStep(
            text=f"The point on the curve: put {x} = {read_as(point)} into y = {read_as(curve)}",
            display=f"({read_as(point)}, {read_as(height)})",
            display_latex=rf"\left({latex_of(point)},\ {latex_of(height)}\right)",
        )
    )
    derivative = sp.simplify(sp.diff(curve, x))
    slope = sp.simplify(derivative.subs(x, point))
    solution.steps.append(
        SolutionStep(
            text=f"The slope of the tangent is the derivative at {x} = {read_as(point)}",
            display=f"y' = {read_as(derivative)}, so the slope is {read_as(slope)}",
            display_latex=(
                rf"y' = {latex_of(derivative)} \quad\Rightarrow\quad m = {latex_of(slope)}"
            ),
        )
    )
    if kind == "normal":
        if slope == 0:
            solution.steps.append(
                SolutionStep(
                    text="The tangent is flat, so the normal, which is perpendicular to it, "
                    "is the vertical line through the point",
                    display=f"{x} = {read_as(point)}",
                    display_latex=f"{latex_of(x)} = {latex_of(point)}",
                )
            )
            solution.result = sp.Eq(x, point)
            solution.summary = f"{x} = {read_as(point)}"
            return solution, curve, None, (point, height)
        slope = sp.simplify(-1 / slope)
        solution.steps.append(
            SolutionStep(
                text="The normal is perpendicular to the tangent, so its slope is -1 over "
                "the tangent's",
                display=f"m = {read_as(slope)}",
                display_latex=f"m = {latex_of(slope)}",
            )
        )
    point_slope_left = y - height
    with distribute(False):
        point_slope_right = slope * (x - point)
    solution.steps.append(
        SolutionStep(
            text="Point-slope form: y - y1 = m(x - x1)",
            display=f"{read_as(point_slope_left)} = {read_as(point_slope_right)}",
            display_latex=f"{latex_of(point_slope_left)} = {latex_of(point_slope_right)}",
        )
    )
    line = sp.expand(slope * (x - point) + height)
    solution.steps.append(
        SolutionStep(
            text="Solve for y",
            display=f"y = {read_as(line)}",
            display_latex=f"y = {latex_of(line)}",
        )
    )
    solution.result = sp.Eq(y, line)
    solution.summary = f"y = {read_as(line)}"
    return solution, curve, line, (point, height)
