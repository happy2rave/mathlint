"""Function analysis: everything a curve-sketching question asks for.

The domain (and what restricts it), the intercepts, the asymptotes, where the
function rises and falls and its extrema, where it bends up or down and its
inflection points. Each finding is a step with its reason. A part SymPy cannot
settle exactly is said to be left out, never guessed.
"""

from __future__ import annotations

import sympy as sp
from sympy.calculus.util import continuous_domain

from ..parse.plain import latex_of, read_as
from ..solve.intervals import as_intervals, pieces
from .expression import Steps, method

MAX_POINTS = 12


def can_analyze(expression: sp.Expr) -> bool:
    symbols = expression.free_symbols
    return len(symbols) == 1 and not expression.has(sp.Derivative, sp.Integral)


@method("analyze", applies=can_analyze)
def analyze_steps(expression: sp.Expr, steps: Steps) -> sp.Expr:
    (x,) = expression.free_symbols
    f = expression
    computation = steps.computation
    computation.kind = "analysis"
    name = f"f({x})"
    steps.show_text(
        "The function", f"{name} = {read_as(f)}", f"f\\left({latex_of(x)}\\right) = {latex_of(f)}"
    )

    domain = _domain(f, x, steps)
    _intercepts(f, x, domain, steps)
    _asymptotes(f, x, domain, steps)
    derivative = _rising_and_falling(f, x, domain, steps)
    if derivative is not None:
        _bending(f, derivative, x, domain, steps)
    computation.title = f"Analyze f({x}) = {read_as(f)}"
    return expression


# --- domain ------------------------------------------------------------------------------


def _domain(f: sp.Expr, x: sp.Symbol, steps: Steps) -> sp.Set:
    domain = continuous_domain(f, x, sp.S.Reals)
    reasons = []
    for node in sp.preorder_traversal(f):
        if isinstance(node, sp.Pow) and node.exp.is_negative and node.base.has(x):
            reasons.append(f"the denominator {read_as(node.base)} must not be 0")
        elif isinstance(node, sp.Pow) and node.exp.is_Rational and node.exp.q % 2 == 0:
            reasons.append(f"what is under the root, {read_as(node.base)}, must be at least 0")
        elif isinstance(node, sp.log):
            reasons.append(f"what the logarithm takes, {read_as(node.args[0])}, must be positive")
    plain, latex = as_intervals(domain)
    if domain == sp.S.Reals:
        text = (
            "Domain: every real number, since nothing divides by zero or leaves a root or a "
            "logarithm undefined"
        )
        plain, latex = "all real numbers", r"\mathbb{R}"
    else:
        text = "Domain: " + "; ".join(dict.fromkeys(reasons)) if reasons else "Domain"
    steps.show_text(text, plain, latex)
    return domain


# --- intercepts --------------------------------------------------------------------------


def _intercepts(f: sp.Expr, x: sp.Symbol, domain: sp.Set, steps: Steps) -> None:
    if sp.S.Zero in domain:
        value = sp.simplify(f.subs(x, 0))
        steps.show_text(
            f"The y-intercept: put {x} = 0",
            f"f(0) = {read_as(value)}, the point (0, {read_as(value)})",
            rf"f(0) = {latex_of(value)}",
        )
        _mark(steps, 0, value, "y-intercept")
    else:
        steps.note(f"No y-intercept: {x} = 0 is not in the domain")

    zeros = _solve(f, x, domain)
    if zeros is None:
        _endless(f, x, domain, steps, f"The zeros: f({x}) = 0")
    elif not zeros:
        steps.note(f"No zeros: f({x}) is never 0, so the graph never touches the x-axis")
    else:
        listed = ", ".join(f"{x} = {read_as(value)}" for value in zeros)
        steps.show_text(
            f"The zeros (x-intercepts): solve f({x}) = 0",
            listed,
            r",\ ".join(f"{latex_of(x)} = {latex_of(value)}" for value in zeros),
        )
        for value in zeros:
            _mark(steps, value, 0, "zero")


# --- asymptotes --------------------------------------------------------------------------


def _asymptotes(f: sp.Expr, x: sp.Symbol, domain: sp.Set, steps: Steps) -> None:
    found = False
    for point in _gaps(domain):
        sides = _sides(domain, point)
        limits = {side: sp.limit(f, x, point, "-" if side == "left" else "+") for side in sides}
        values = list(limits.values())
        if any(value.is_infinite for value in values):
            approach = " and ".join(
                f"{_infinity(value)} from the {side}" for side, value in limits.items()
            )
            steps.show_text(
                f"Vertical asymptote: as {x} approaches {read_as(point)}, f({x}) goes to "
                f"{approach}",
                f"{x} = {read_as(point)}",
                f"{latex_of(x)} = {latex_of(point)}",
            )
            found = True
        elif len(values) == 2 and values[0] == values[1] and values[0].is_finite:
            left = values[0]
            steps.show_text(
                f"A hole, not an asymptote: f({x}) approaches {read_as(left)} at "
                f"{x} = {read_as(point)} from both sides, but is not defined there",
                f"({read_as(point)}, {read_as(left)})",
                rf"\left({latex_of(point)},\ {latex_of(left)}\right)",
            )
            found = True

    lines = {}
    for end in (sp.oo, -sp.oo):
        if not _reaches(domain, end):
            continue
        limit = sp.limit(f, x, end)
        if isinstance(limit, sp.AccumBounds):
            continue  # it keeps going up and down, like sin(x): no line to approach
        if limit.is_number and limit.is_finite:
            lines[end] = ("Horizontal", limit)
            continue
        slant = _oblique(f, x, end)
        if slant is not None:
            lines[end] = ("Oblique", slant)
    ends = {sp.oo: f"{x} goes to infinity", -sp.oo: f"{x} goes to minus infinity"}
    if len(lines) == 2 and lines[sp.oo] == lines[-sp.oo]:
        # the same line on both sides is one asymptote
        lines = {"both": lines[sp.oo]}
        ends["both"] = f"{x} goes to infinity in either direction"
    for end, (kind, line) in lines.items():
        steps.show_text(
            f"{kind} asymptote: f({x}) gets closer and closer to it as {ends[end]}",
            f"y = {read_as(line)}",
            f"y = {latex_of(line)}",
        )
        found = True
    if not found:
        steps.note("No asymptotes")


def _oblique(f: sp.Expr, x: sp.Symbol, end: sp.Expr) -> sp.Expr | None:
    slope = sp.limit(f / x, x, end)
    if isinstance(slope, sp.AccumBounds) or not slope.is_finite or slope == 0:
        return None
    offset = sp.limit(f - slope * x, x, end)
    if isinstance(offset, sp.AccumBounds) or not offset.is_finite:
        return None
    return slope * x + offset


def _gaps(domain: sp.Set) -> list[sp.Expr]:
    """Finite ends of the domain that are not in it: where something can go wrong."""
    ends = []
    for part in pieces(domain):
        for end in (part.inf, part.sup):
            if end.is_finite and end not in ends and domain.contains(end) is not sp.true:
                ends.append(end)
    return ends[:MAX_POINTS]


def _sides(domain: sp.Set, point: sp.Expr) -> list[str]:
    """The sides of ``point`` on which the function is defined."""
    sides = []
    if any(part.sup == point for part in pieces(domain)):
        sides.append("left")
    if any(part.inf == point for part in pieces(domain)):
        sides.append("right")
    return sides


def _reaches(domain: sp.Set, end: sp.Expr) -> bool:
    parts = pieces(domain)
    return bool(parts) and (parts[-1].sup == sp.oo if end == sp.oo else parts[0].inf == -sp.oo)


def _infinity(value: sp.Expr) -> str:
    if value == sp.oo:
        return "+infinity"
    if value == -sp.oo:
        return "-infinity"
    return read_as(value)


# --- rising and falling ------------------------------------------------------------------


def _rising_and_falling(f, x, domain, steps: Steps) -> sp.Expr | None:
    derivative = sp.factor(sp.simplify(sp.diff(f, x)))
    steps.show_text(
        f"The derivative tells where f({x}) rises and falls",
        f"f'({x}) = {read_as(derivative)}",
        rf"f'\left({latex_of(x)}\right) = {latex_of(derivative)}",
    )
    if derivative == 0:
        steps.note(f"f'({x}) = 0 everywhere: f is constant, it neither rises nor falls")
        return None
    critical = _solve(derivative, x, domain)
    if critical is None:
        _endless(derivative, x, domain, steps, f"Critical points: f'({x}) = 0")
        return derivative
    if not critical:
        steps.note(f"f'({x}) is never 0, so there are no critical points")
    else:
        steps.show_text(
            f"Critical points: f'({x}) = 0",
            ", ".join(f"{x} = {read_as(value)}" for value in critical),
            r",\ ".join(f"{latex_of(x)} = {latex_of(value)}" for value in critical),
        )
    signs = _signs(derivative, x, domain, critical)
    rising = [interval for interval, sign in signs if sign > 0]
    falling = [interval for interval, sign in signs if sign < 0]
    if rising:
        steps.show_text("Increasing where f'(x) > 0", *_listed(rising))
    if falling:
        steps.show_text("Decreasing where f'(x) < 0", *_listed(falling))

    for point in critical:
        before, after = _around(signs, point)
        value = sp.simplify(f.subs(x, point))
        if before is None or after is None or before == after:
            continue
        kind = "maximum" if before > 0 > after else "minimum"
        change = "rises then falls" if kind == "maximum" else "falls then rises"
        steps.show_text(
            f"Local {kind}: f({x}) {change} at {x} = {read_as(point)}",
            f"({read_as(point)}, {read_as(value)})",
            rf"\left({latex_of(point)},\ {latex_of(value)}\right)",
        )
        _mark(steps, point, value, f"local {kind}")
    return derivative


def _bending(f, derivative, x, domain, steps: Steps) -> None:
    second = sp.factor(sp.simplify(sp.diff(derivative, x)))
    steps.show_text(
        "The second derivative tells which way it bends",
        f"f''({x}) = {read_as(second)}",
        rf"f''\left({latex_of(x)}\right) = {latex_of(second)}",
    )
    if second == 0:
        steps.note(
            f"f''({x}) = 0 everywhere: the graph is made of straight lines and does not bend"
        )
        return
    flat = _solve(second, x, domain)
    if flat is None:
        _endless(second, x, domain, steps, f"Where f''({x}) = 0")
        return
    if not flat:
        steps.note(f"f''({x}) is never 0, so there is no inflection point")
    signs = _signs(second, x, domain, flat)
    up = [interval for interval, sign in signs if sign > 0]
    down = [interval for interval, sign in signs if sign < 0]
    if up:
        steps.show_text("Concave up (bends upward) where f''(x) > 0", *_listed(up))
    if down:
        steps.show_text("Concave down (bends downward) where f''(x) < 0", *_listed(down))
    for point in flat:
        before, after = _around(signs, point)
        if before is None or after is None or before == after:
            continue
        value = sp.simplify(f.subs(x, point))
        steps.show_text(
            f"Inflection point: the bending changes direction at {x} = {read_as(point)}",
            f"({read_as(point)}, {read_as(value)})",
            rf"\left({latex_of(point)},\ {latex_of(value)}\right)",
        )
        _mark(steps, point, value, "inflection point")


# --- helpers -------------------------------------------------------------------------------


def _solve(expression: sp.Expr, x: sp.Symbol, domain: sp.Set) -> list[sp.Expr] | None:
    """The real solutions of expression = 0 in the domain, or None if not a short list."""
    try:
        found = sp.solveset(expression, x, domain)
    except (NotImplementedError, ValueError, TypeError):
        return None
    if found == sp.S.EmptySet:
        return []
    if not isinstance(found, sp.FiniteSet) or len(found) > MAX_POINTS:
        return None
    values = [value for value in found if value.is_real]
    return sorted(values, key=lambda value: float(value))


def _endless(expression, x, domain, steps: Steps, what: str) -> None:
    """Infinitely many solutions (sin, cos...) are shown as a set; others are left out."""
    try:
        found = sp.solveset(expression, x, domain)
    except (NotImplementedError, ValueError, TypeError):
        found = None
    families = _families(found)
    if families:
        n = sp.Symbol("n", integer=True)
        plain = " or ".join(f"{x} = {read_as(family)}" for family in families)
        latex = r" \quad\text{or}\quad ".join(
            f"{latex_of(x)} = {latex_of(family)}" for family in families
        )
        steps.show_text(
            f"{what} has infinitely many solutions, repeating along the axis",
            f"{plain}, for any whole number {n}",
            latex + rf", \quad {latex_of(n)} \in \mathbb{{Z}}",
        )
        return
    steps.note(f"{what} could not be solved exactly, so this part is left out; see the graph")


def _families(found) -> list[sp.Expr]:
    """``{2 n pi | n in Z} U {2 n pi + pi | n in Z}`` as ``[2*n*pi, 2*n*pi + pi]``."""
    parts = found.args if isinstance(found, sp.Union) else (found,)
    n = sp.Symbol("n", integer=True)
    families = []
    for part in parts:
        if not isinstance(part, sp.ImageSet) or part.base_sets != (sp.S.Integers,):
            return []
        (variable,) = part.lamda.variables
        families.append(part.lamda.expr.subs(variable, n))
    return families


def _signs(expression, x, domain, cuts) -> list[tuple[sp.Interval, int]]:
    """The sign of ``expression`` on each open interval of the domain between the cuts."""
    result = []
    for part in pieces(domain):
        if isinstance(part, sp.FiniteSet):
            continue
        inside = [cut for cut in cuts if part.inf < cut < part.sup]
        ends = [part.inf, *inside, part.sup]
        for left, right in zip(ends, ends[1:], strict=False):
            test = _inside(left, right)
            value = expression.subs(x, test)
            number = complex(sp.N(value))
            if abs(number.imag) > 1e-12:
                continue
            sign = 1 if number.real > 0 else -1 if number.real < 0 else 0
            result.append((sp.Interval.open(left, right), sign))
    return result


def _inside(left: sp.Expr, right: sp.Expr) -> sp.Expr:
    if left == -sp.oo:
        return sp.floor(right) - 1
    if right == sp.oo:
        return sp.ceiling(left) + 1
    return (left + right) / 2


def _around(signs, point) -> tuple[int | None, int | None]:
    before = next((sign for interval, sign in signs if interval.sup == point), None)
    after = next((sign for interval, sign in signs if interval.inf == point), None)
    return before, after


def _listed(intervals: list[sp.Interval]) -> tuple[str, str]:
    plain, latex = as_intervals(sp.Union(*intervals))
    # touching intervals were merged by the union; keep them apart as a student would
    if len(pieces(sp.Union(*intervals))) != len(intervals):
        parts = [as_intervals(interval) for interval in intervals]
        plain = " and ".join(text for text, _ in parts)
        latex = r" \text{ and } ".join(text for _, text in parts)
    return plain, latex


def _mark(steps: Steps, a: sp.Expr, b: sp.Expr, what: str) -> None:
    try:
        point = {"x": float(a), "y": float(b), "what": what}
    except (TypeError, ValueError):
        return
    steps.computation.marks.append(point)
