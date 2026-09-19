"""Differential equations, solved by the methods a first course teaches.

First order: separate the variables when the equation separates, otherwise use
an integrating factor when it is linear. Second order with constant
coefficients: the characteristic equation, and its three cases (two real
roots, a double root, complex roots), plus a particular solution when the
right side is not 0. Initial conditions fix the constants. Every answer is
checked by putting it back into the equation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from ..errors import ParseError, UnsupportedError
from ..parse.plain import latex_of, parse_expression, read_as
from .solution import Solution, SolutionStep

_PRIME_LATEX = [
    (re.compile(r"\^\{\\prime\\prime\}"), "''"),
    (re.compile(r"\^\{\\prime\}"), "'"),
    (re.compile(r"\\prime\\prime"), "''"),
    (re.compile(r"\\prime"), "'"),
    (
        re.compile(
            r"\\frac\s*\{\s*d\s*\^\s*\{?2\}?\s*y\s*\}\s*\{\s*d\s*([a-z])\s*\^\s*\{?2\}?\s*\}"
        ),
        "y''",
    ),
    (re.compile(r"\\frac\s*\{\s*d\s*y\s*\}\s*\{\s*d\s*([a-z])\s*\}"), "y'"),
    (re.compile(r"d\s*\^\s*2\s*y\s*/\s*d\s*([a-z])\s*\^\s*2"), "y''"),
    (re.compile(r"(?<![A-Za-z])dy\s*/\s*d([a-z])"), "y'"),
]
_CONDITION = re.compile(r"^\s*y('*)\s*\(\s*(.+?)\s*\)\s*=\s*(.+?)\s*$")
# names the parser keeps whole (it splits "abc" into a*b*c, but not "Q_1")
_MARKERS = {"''": "Q_2", "'": "Q_1"}


@dataclass
class ODEProblem:
    equation: sp.Eq
    x: sp.Symbol
    order: int
    conditions: list[tuple[int, sp.Expr, sp.Expr]] = field(default_factory=list)


def _normalize(text: str) -> str:
    for pattern, replacement in _PRIME_LATEX:
        text = pattern.sub(replacement, text)
    return text


def looks_like_ode(text: str) -> bool:
    body = _normalize(text)
    return "=" in body and bool(re.search(r"(?<![A-Za-z])y'", body))


def parse_ode(text: str) -> ODEProblem:
    body = _normalize(text)
    parts = [part for part in re.split(r"[;\n]|,(?=\s*y'*\s*\()", body) if part.strip()]
    equations = [part for part in parts if "'" in part and not _CONDITION.match(part)]
    if len(equations) != 1:
        raise ParseError("write one differential equation, like y' = 2y, then any y(0) = 1")
    x = (
        sp.Symbol("t")
        if re.search(r"(?<![A-Za-z])t(?![A-Za-z])", equations[0])
        and not re.search(r"(?<![A-Za-z])x(?![A-Za-z])", equations[0])
        else sp.Symbol("x")
    )
    y = sp.Function("y")(x)
    left, _, right = equations[0].partition("=")
    if "=" in right:
        raise ParseError("a differential equation has one '=' sign")

    def read(side: str) -> sp.Expr:
        if re.search(r"y'{3,}", side):
            raise UnsupportedError("only first- and second-order equations are solved so far")
        marked = re.sub(r"(?<![A-Za-z])y('+)", lambda m: " " + _MARKERS[m.group(1)] + " ", side)
        marked = re.sub(r"(?<![A-Za-z])y(?![A-Za-z'_])", " Q_0 ", marked)
        expression = parse_expression(marked).expr
        return expression.subs(
            {
                sp.Symbol("Q_2"): y.diff(x, 2),
                sp.Symbol("Q_1"): y.diff(x),
                sp.Symbol("Q_0"): y,
            }
        )

    equation = sp.Eq(read(left), read(right))
    order = sp.ode_order(equation, y)
    if order not in (1, 2):
        raise UnsupportedError("only first- and second-order equations are solved so far")
    conditions = []
    for part in parts:
        match = _CONDITION.match(part)
        if match:
            conditions.append(
                (
                    len(match.group(1)),
                    parse_expression(match.group(2)).expr,
                    parse_expression(match.group(3)).expr,
                )
            )
    return ODEProblem(equation, x, order, conditions)


# --- showing -------------------------------------------------------------------------


def _prime(expression: sp.Expr, x: sp.Symbol) -> sp.Expr:
    """y(x), y'(x), y''(x) written as y, y', y''."""
    y = sp.Function("y")(x)
    return expression.subs(
        {y.diff(x, 2): sp.Symbol("y''"), y.diff(x): sp.Symbol("y'"), y: sp.Symbol("y")}
    )


def _step(solution: Solution, text: str, left, right=None, x=None) -> None:
    if right is None:
        solution.steps.append(SolutionStep(text=text))
        return
    if x is not None:
        left, right = _prime(left, x), _prime(right, x)
    solution.steps.append(
        SolutionStep(
            text=text,
            display=f"{read_as(left)} = {read_as(right)}",
            display_latex=f"{latex_of(left)} = {latex_of(right)}",
        )
    )


# --- solving -------------------------------------------------------------------------


def ode_solution(problem: ODEProblem) -> Solution:
    x = problem.x
    y = sp.Function("y")(x)
    shown = _prime(problem.equation.lhs, x), _prime(problem.equation.rhs, x)
    solution = Solution(operation="ode", title=f"Solve {read_as(shown[0])} = {read_as(shown[1])}")
    _step(solution, "Start from", problem.equation.lhs, problem.equation.rhs, x)
    general = None
    try:
        if problem.order == 1:
            general = _first_order(problem.equation, y, x, solution)
        else:
            general = _second_order(problem.equation, y, x, solution)
    except (NotImplementedError, ValueError, TypeError):
        general = None
    if general is None or not _checks(problem.equation, general, y):
        solution.steps = solution.steps[:1]
        try:
            general = sp.dsolve(problem.equation, y)
        except (NotImplementedError, ValueError, TypeError) as error:
            raise UnsupportedError(
                "this differential equation is not one mathlint can solve yet"
            ) from error
        if isinstance(general, list):
            general = general[0]
        _step(solution, "Solve (computer algebra)", sp.Symbol("y"), general.rhs)
    answer = general
    if problem.conditions:
        answer = _conditions(general, problem.conditions, y, x, solution)
    solution.result = answer
    solution.summary = f"y = {read_as(answer.rhs)}"
    return solution


def _checks(equation, general, y) -> bool:
    try:
        ok, _ = sp.checkodesol(equation, general, y)
    except (NotImplementedError, ValueError, TypeError):
        return False
    return bool(ok)


def _first_order(equation, y, x, solution: Solution):
    slope = sp.solve(equation.lhs - equation.rhs, y.diff(x))
    if len(slope) != 1:
        return None
    f = sp.expand(slope[0])
    if equation.lhs != y.diff(x):
        _step(solution, "Get y' on its own", y.diff(x), f, x)

    Y = sp.Symbol("y")
    in_y = f.subs(y, Y)
    parts = sp.separatevars(in_y, symbols=[x, Y], dict=True)
    if parts and parts.get(Y) is not None and not (parts[Y].has(x) or parts[x].has(Y)):
        return _separable(parts[x] * parts["coeff"], parts[Y], y, x, Y, solution)
    p = -sp.expand(in_y).coeff(Y)
    q = sp.expand(in_y + p * Y)
    if not q.has(Y) and not p.has(Y):
        return _linear(p, q, y, x, solution)
    return None


def _separable(g, h, y, x, Y, solution: Solution):
    C = sp.Symbol("C")
    solution.steps.append(
        SolutionStep(
            text="The right side is a function of x times a function of y, so separate the "
            "variables: everything with y (and dy) on the left, everything with x (and dx) "
            "on the right",
            display=f"{_times(1 / h)}dy = {_times(g)}dx",
            display_latex=rf"{_times_latex(1 / h)}\,dy = {_times_latex(g)}\,dx",
        )
    )
    left = sp.integrate(1 / h, Y)
    right = sp.integrate(g, x)
    # the integral of 1/y is ln|y|, not ln(y)
    shown_left = left.replace(
        lambda node: isinstance(node, sp.log) and node.args[0].has(Y),
        lambda node: sp.log(sp.Abs(node.args[0])),
    )
    _step(solution, "Integrate both sides, with one constant C for both", shown_left, right + C)
    solved = sp.solve(sp.Eq(left, right + C), Y)
    if not solved:
        return sp.Eq(y, sp.Symbol("y"))  # keep it implicit; checkodesol decides
    value = sp.simplify(solved[-1])
    # plus or minus e^C, or C^3/3, is just another constant: write it as C
    value = _renamed_constant(value.subs(sp.exp(C), C), C, x)
    general = sp.Eq(y, value)
    text = "Solve for y"
    if shown_left != left:
        text += " (the plus or minus from |y| and e^C together are just another constant C)"
    _step(solution, text, sp.Symbol("y"), value)
    return general


def _renamed_constant(value: sp.Expr, C: sp.Symbol, x: sp.Symbol) -> sp.Expr:
    """``C^3 e^(3x)/3 - 2`` -> ``C e^(3x) - 2``: any number made from C is a new C."""
    terms = sp.Add.make_args(sp.expand(value))
    with_c = [term for term in terms if term.has(C)]
    if len(with_c) != 1:
        return value
    (term,) = with_c
    constant, rest = term.as_independent(x, as_Add=False)
    if not constant.has(C) or rest.has(C):
        return value
    return sp.Add(*[t for t in terms if t is not term]) + C * rest


def _times(factor: sp.Expr) -> str:
    """``2`` -> ``2 ``, ``x + 1`` -> ``(x + 1) ``, ``1`` -> nothing."""
    if factor == 1:
        return ""
    text = read_as(factor)
    return f"({text}) " if isinstance(factor, sp.Add) else f"{text} "


def _times_latex(factor: sp.Expr) -> str:
    if factor == 1:
        return ""
    text = latex_of(factor)
    return rf"\left({text}\right)" if isinstance(factor, sp.Add) else text


def _linear(p, q, y, x, solution: Solution):
    C = sp.Symbol("C")
    term = p * sp.Symbol("y")
    sign = " - " if term.could_extract_minus_sign() else " + "
    body = read_as(-term if sign == " - " else term)
    body_latex = latex_of(-term if sign == " - " else term)
    solution.steps.append(
        SolutionStep(
            text=f"This is linear: y' + P(x) y = Q(x), with P = {read_as(p)} and Q = {read_as(q)}",
            display=f"y'{sign}{body} = {read_as(q)}",
            display_latex=f"y'{sign}{body_latex} = {latex_of(q)}",
        )
    )
    factor = sp.simplify(sp.exp(sp.integrate(p, x)))
    solution.steps.append(
        SolutionStep(
            text="The integrating factor is e^(integral of P)",
            display=f"mu = {read_as(factor)}",
            display_latex=rf"\mu = e^{{\int {latex_of(p)}\,dx}} = {latex_of(factor)}",
        )
    )
    _step(
        solution,
        "Multiply both sides by mu: the left side becomes the derivative of mu*y",
        sp.Derivative(factor * sp.Symbol("y"), x),
        sp.simplify(factor * q),
    )
    integral = sp.integrate(sp.simplify(factor * q), x)
    _step(solution, "Integrate both sides", factor * sp.Symbol("y"), integral + C)
    value = sp.simplify((integral + C) / factor)
    _step(solution, "Divide by mu", sp.Symbol("y"), value)
    return sp.Eq(y, value)


def _second_order(equation, y, x, solution: Solution):
    expression = sp.expand(equation.lhs - equation.rhs)
    a = expression.coeff(y.diff(x, 2))
    rest = sp.expand(expression - a * y.diff(x, 2))
    b = rest.coeff(y.diff(x))
    rest = sp.expand(rest - b * y.diff(x))
    c = rest.coeff(y)
    forcing = -sp.expand(rest - c * y)
    if any(value.has(x) or value.has(y) for value in (a, b, c)) or forcing.has(y):
        return None

    r = sp.Symbol("r")
    characteristic = a * r**2 + b * r + c
    _step(
        solution,
        "Constant coefficients: try y = e^(rx), which turns the equation into the "
        "characteristic equation",
        characteristic,
        sp.Integer(0),
    )
    roots = sp.roots(sp.Poly(characteristic, r))
    C1, C2 = sp.symbols("C1 C2")
    if len(roots) == 2 and all(root.is_real for root in roots):
        r1, r2 = sorted(roots, key=float)
        homogeneous = C1 * sp.exp(r1 * x) + C2 * sp.exp(r2 * x)
        text = f"Two real roots, r = {read_as(r1)} and r = {read_as(r2)}, give two exponentials"
    elif len(roots) == 1:
        (r1,) = roots
        homogeneous = (C1 + C2 * x) * sp.exp(r1 * x)
        text = f"A double root r = {read_as(r1)}: the second solution gets an extra factor x"
    else:
        root = next(iter(roots))
        alpha, beta = sp.re(root), abs(sp.im(root))
        homogeneous = sp.exp(alpha * x) * (C1 * sp.cos(beta * x) + C2 * sp.sin(beta * x))
        text = (
            f"Complex roots r = {read_as(alpha)} ± {read_as(beta)}i give an exponential "
            "times a cosine and a sine"
        )
    _step(solution, text, sp.Symbol("y_h") if forcing != 0 else sp.Symbol("y"), homogeneous)
    if forcing == 0:
        return sp.Eq(y, homogeneous)

    full = sp.dsolve(equation, y)
    constants = sorted(full.rhs.free_symbols - {x}, key=str)
    particular = sp.simplify(full.rhs.subs({constant: 0 for constant in constants}))
    _step(
        solution,
        "The right side is not 0, so add a particular solution: guess a form like the "
        "right side and find its numbers (undetermined coefficients)",
        sp.Symbol("y_p"),
        particular,
    )
    value = homogeneous + particular
    _step(solution, "The general solution is y_h + y_p", sp.Symbol("y"), value)
    return sp.Eq(y, value)


def _conditions(general, conditions, y, x, solution: Solution):
    value = general.rhs
    constants = sorted(value.free_symbols - {x}, key=str)
    equations = []
    for order, at, wanted in conditions:
        derivative = sp.diff(value, x, order)
        equation = sp.Eq(derivative.subs(x, at), wanted)
        equations.append(equation)
        name = "y" + "'" * order
        solution.steps.append(
            SolutionStep(
                text=f"Use {name}({read_as(at)}) = {read_as(wanted)}",
                display=f"{read_as(equation.lhs)} = {read_as(equation.rhs)}",
                display_latex=f"{latex_of(equation.lhs)} = {latex_of(equation.rhs)}",
            )
        )
    found = sp.solve(equations, constants, dict=True)
    if not found:
        raise ParseError("these initial conditions cannot all hold")
    found = found[0]
    solution.steps.append(
        SolutionStep(
            text="Solve for the constants",
            display=", ".join(f"{name} = {read_as(found[name])}" for name in found),
            display_latex=r",\ ".join(
                f"{latex_of(name)} = {latex_of(found[name])}" for name in found
            ),
        )
    )
    particular = sp.expand(value.subs(found))
    _step(solution, "Put them back", sp.Symbol("y"), particular)
    return sp.Eq(y, particular)
