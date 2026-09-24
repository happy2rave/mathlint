"""Limits, worked out the way a calculus course teaches them.

First try putting the number in. When that gives 0/0 the expression has to be
rewritten: factor and cancel, multiply by the conjugate of a square root, or,
when nothing else works, L'Hopital's rule. At infinity, divide the top and the
bottom by the highest power of the denominator. A number over 0 means the
function grows without bound, and then each side is looked at on its own. The
answer is always compared with SymPy's before it is shown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp

from ..errors import ParseError
from ..i18n import join, msg
from ..parse.plain import latex_of, parse_expression, read_as
from .solution import Solution, SolutionStep

MAX_REWRITES = 4

_START = re.compile(r"^\s*(?:\\lim|lim(?:it)?)(?![A-Za-z])\s*", re.IGNORECASE)
_ARROW = r"(?:->|→|\\to(?![A-Za-z])|\\rightarrow(?![A-Za-z])|\bto\b)"
_APPROACH = re.compile(rf"^\s*([A-Za-z])\s*{_ARROW}\s*(.+?)\s*$")
_BARE = re.compile(rf"^\s*([A-Za-z])\s*{_ARROW}\s*(\S+)")
_INFINITY = {"oo", "inf", "infty", "infinity", r"\infty", "∞"}


@dataclass
class LimitProblem:
    expression: sp.Expr
    variable: sp.Symbol
    point: sp.Expr
    direction: str  # "+-" from both sides, "+" from the right, "-" from the left


def looks_like_limit(text: str) -> bool:
    return bool(_START.match(text))


def parse_limit(text: str) -> LimitProblem | None:
    """``lim x->2 (x^2 - 4)/(x - 2)`` or ``\\lim_{x\\to 2}\\frac{x^2-4}{x-2}``, or None."""
    start = _START.match(text)
    if start is None:
        return None
    rest = text[start.end() :].lstrip()
    if rest.startswith("_"):
        rest = rest[1:].lstrip()
    if rest[:1] in ("{", "("):
        approach, rest = _group(rest)
    else:
        bare = _BARE.match(rest)
        if bare is None:
            raise ParseError(msg("write the limit like lim x->2 (x^2 - 4)/(x - 2)"))
        approach, rest = bare.group(0), rest[bare.end() :]
    match = _APPROACH.match(approach)
    if match is None:
        raise ParseError(msg("say what the variable approaches, like x->2 or x->oo"))
    variable = sp.Symbol(match.group(1))
    point, direction = _point(match.group(2))
    body = rest.strip()
    if not body:
        raise ParseError(msg("a limit needs something to take the limit of"))
    expression = parse_expression(body).expr
    return LimitProblem(expression, variable, point, direction)


def _group(text: str) -> tuple[str, str]:
    opening = text[0]
    closing = "}" if opening == "{" else ")"
    depth = 0
    for index, char in enumerate(text):
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[1:index], text[index + 1 :]
    raise ParseError(msg("unbalanced bracket in the limit"))


def _point(text: str) -> tuple[sp.Expr, str]:
    body = text.replace(" ", "")
    direction = "+-"
    side = re.search(r"\^?\{?([+-])\}?$", body)
    if side and not re.fullmatch(r"[+-]?(oo|inf|infty|infinity|\\infty|∞)", body):
        direction = side.group(1)
        body = body[: side.start()]
    sign = -1 if body.startswith("-") else 1
    bare = body.lstrip("+-")
    if bare in _INFINITY:
        return (sp.oo if sign > 0 else -sp.oo), "+-"
    point = parse_expression(body).expr
    if point.free_symbols:
        raise ParseError(msg("the point a limit approaches must be a number or infinity"))
    return point, direction


# --- writing it out ----------------------------------------------------------------------


@dataclass
class Quotient:
    """A top over a bottom, shown as written rather than as SymPy would tidy it."""

    top: sp.Expr
    bottom: sp.Expr


def _body(expression) -> tuple[str, str]:
    if isinstance(expression, Quotient):
        top, bottom = expression.top, expression.bottom
        top_plain, bottom_plain = read_as(top), read_as(bottom)
        if isinstance(top, sp.Add):
            top_plain = f"({top_plain})"
        if not (bottom.is_Atom or isinstance(bottom, sp.Function)):
            bottom_plain = f"({bottom_plain})"
        return f"{top_plain}/{bottom_plain}", rf"\frac{{{latex_of(top)}}}{{{latex_of(bottom)}}}"
    plain, latex = read_as(expression), latex_of(expression)
    if isinstance(expression, sp.Add):
        plain, latex = f"({plain})", rf"\left({latex}\right)"
    return plain, latex


def limit_plain(expression, variable: sp.Symbol, point: sp.Expr, direction: str) -> str:
    body, _ = _body(expression)
    return f"lim {variable}->{_point_plain(point)}{_side(direction)} {body}"


def limit_latex(expression, variable: sp.Symbol, point: sp.Expr, direction: str) -> str:
    _, body = _body(expression)
    side = {"+": "^{+}", "-": "^{-}"}.get(direction, "")
    return rf"\lim_{{{latex_of(variable)} \to {latex_of(point)}{side}}} {body}"


def _point_plain(point: sp.Expr) -> str:
    return "inf" if point == sp.oo else "-inf" if point == -sp.oo else read_as(point)


def _side(direction: str) -> str:
    return {"+": "+", "-": "-"}.get(direction, "")


class _Work:
    def __init__(self, solution: Solution, problem: LimitProblem) -> None:
        self.solution = solution
        self.problem = problem

    def limit(self, text: str, expression: sp.Expr) -> None:
        p = self.problem
        self.solution.steps.append(
            SolutionStep(
                text=text,
                display=limit_plain(expression, p.variable, p.point, p.direction),
                display_latex=limit_latex(expression, p.variable, p.point, p.direction),
            )
        )

    def value(self, text: str, value: sp.Expr) -> None:
        self.solution.steps.append(
            SolutionStep(text=text, display=_value_plain(value), display_latex=_value_latex(value))
        )

    def note(self, text: str) -> None:
        self.solution.steps.append(SolutionStep(text=text))


DOES_NOT_EXIST = sp.S.NaN


def _from_side(side: str, value: sp.Expr) -> str:
    if side == "-":
        return msg("from the left it goes to {value}", value=_value_plain(value))
    return msg("from the right it goes to {value}", value=_value_plain(value))


def _value_plain(value: sp.Expr) -> str:
    if value is DOES_NOT_EXIST:
        return msg("does not exist")
    return "inf" if value == sp.oo else "-inf" if value == -sp.oo else read_as(value)


def _value_latex(value: sp.Expr) -> str:
    if value is DOES_NOT_EXIST:
        return r"\text{does not exist}"
    return latex_of(value)


# --- solving -------------------------------------------------------------------------------


def limit_solution(problem: LimitProblem) -> Solution:
    """The worked limit; ``result`` is the value, or NaN when it does not exist."""
    f, x, a, direction = problem.expression, problem.variable, problem.point, problem.direction
    solution = Solution(
        operation="limit", title=msg("Find {limit}", limit=limit_plain(f, x, a, direction))
    )
    work = _Work(solution, problem)
    work.limit(msg("Start from"), f)
    try:
        value = _limit(f, x, a, direction, work, 0)
    except (NotImplementedError, ValueError, TypeError, ZeroDivisionError):
        value = None
    expected = _expected(f, x, a, direction)
    if value is None or not _same(value, expected):
        solution.steps = solution.steps[:1]
        work.value(msg("Limit (computer algebra)"), expected)
        value = expected
    solution.result = value
    solution.summary = f"{limit_plain(f, x, a, direction)} = {_value_plain(value)}"
    return solution


def _expected(f, x, a, direction) -> sp.Expr:
    try:
        value = sp.limit(f, x, a, direction)
    except ValueError:  # the two sides disagree
        return DOES_NOT_EXIST
    if value == sp.zoo:
        # infinite, but with no one sign: look at each side
        left, right = sp.limit(f, x, a, "-"), sp.limit(f, x, a, "+")
        return left if left == right else DOES_NOT_EXIST
    return value


def _same(found: sp.Expr, expected: sp.Expr) -> bool:
    if found is DOES_NOT_EXIST or expected is DOES_NOT_EXIST:
        return found is expected
    if found == expected:
        return True
    if found.is_infinite or expected.is_infinite:
        return False
    return sp.simplify(found - expected) == 0


def _limit(f, x, a, direction, work: _Work, depth: int) -> sp.Expr | None:
    if depth > MAX_REWRITES:
        return None
    if a.is_infinite:
        return _at_infinity(f, x, a, work, depth)

    direct = _substitute(f, x, a)
    if direct is not None:
        work.value(
            msg(
                "Put {x} = {a} straight in: the function is defined and continuous there",
                x=x,
                a=read_as(a),
            ),
            direct,
        )
        return direct

    top, bottom = sp.fraction(sp.together(f))
    top_value, bottom_value = _substitute(top, x, a), _substitute(bottom, x, a)
    if top_value == 0 and bottom_value == 0:
        work.note(
            msg(
                "Putting {x} = {a} in gives 0/0, which says nothing yet: "
                "rewrite the expression first",
                x=x,
                a=read_as(a),
            )
        )
        return _zero_over_zero(top, bottom, x, a, direction, work, depth)
    if bottom_value == 0 and top_value is not None and top_value != 0:
        return _over_zero(f, top_value, x, a, direction, work)
    return None


def _substitute(expression: sp.Expr, x: sp.Symbol, a: sp.Expr) -> sp.Expr | None:
    """The value at ``a`` if it is an ordinary finite number, else None."""
    try:
        value = sp.simplify(expression.subs(x, a))
    except (ZeroDivisionError, TypeError, ValueError):
        return None
    if value.has(sp.nan, sp.zoo, sp.oo, -sp.oo) or value.free_symbols:
        return None
    if not value.is_finite or value.is_real is False:
        return None
    return value


def _zero_over_zero(top, bottom, x, a, direction, work: _Work, depth: int):
    if top.is_polynomial(x) and bottom.is_polynomial(x):
        common = sp.gcd(top, bottom)
        if common.has(x):
            work.limit(msg("Factor the top and the bottom"), _unevaluated_quotient(top, bottom))
            simpler = sp.cancel(top / bottom)
            work.limit(
                msg(
                    "Cancel the common factor {factor}; near {x} = {a} it is not "
                    "0, so this changes nothing about the limit",
                    factor=read_as(sp.factor(common)),
                    x=x,
                    a=read_as(a),
                ),
                simpler,
            )
            return _limit(simpler, x, a, direction, work, depth + 1)

    for side in ("top", "bottom"):
        conjugate = _conjugate(top if side == "top" else bottom)
        if conjugate is None:
            continue
        # (sqrt(u) - c)(sqrt(u) + c) = u - c^2: the root is gone from that side
        if side == "top":
            cleared = sp.expand(top * conjugate)
            shown = Quotient(sp.factor(cleared), sp.Mul(bottom, conjugate))
            common = sp.gcd(cleared, bottom)
            simpler = sp.cancel(cleared / bottom) / conjugate
        else:
            cleared = sp.expand(bottom * conjugate)
            shown = Quotient(sp.Mul(top, conjugate), sp.factor(cleared))
            common = sp.gcd(top, cleared)
            simpler = conjugate * sp.cancel(top / cleared)
        if side == "top":
            text = msg(
                "Multiply the top and the bottom by the conjugate {conjugate}, "
                "so the square root disappears from the top",
                conjugate=read_as(conjugate),
            )
        else:
            text = msg(
                "Multiply the top and the bottom by the conjugate {conjugate}, "
                "so the square root disappears from the bottom",
                conjugate=read_as(conjugate),
            )
        work.limit(
            text,
            shown,
        )
        if common.has(x):
            work.limit(
                msg(
                    "Cancel the common factor {factor}; near {x} = {a} it is not 0",
                    factor=read_as(sp.factor(common)),
                    x=x,
                    a=read_as(a),
                ),
                simpler,
            )
            return _limit(simpler, x, a, direction, work, depth + 1)
        break

    new_top, new_bottom = sp.diff(top, x), sp.diff(bottom, x)
    work.limit(
        msg("L'Hopital's rule: for 0/0, the limit of top/bottom is the limit of top'/bottom'"),
        _unevaluated_quotient(new_top, new_bottom),
    )
    return _limit(sp.simplify(new_top / new_bottom), x, a, direction, work, depth + 1)


def _unevaluated_quotient(top: sp.Expr, bottom: sp.Expr):
    factored_top, factored_bottom = sp.factor(top), sp.factor(bottom)
    if factored_bottom == 1:
        return factored_top
    return Quotient(factored_top, factored_bottom)


def _conjugate(side: sp.Expr) -> sp.Expr | None:
    """For ``sqrt(u) - c`` the conjugate ``sqrt(u) + c``."""
    terms = sp.Add.make_args(sp.expand(side))
    if len(terms) != 2:
        return None
    roots = [term for term in terms if _is_square_root(term)]
    if len(roots) != 1:
        return None
    root = roots[0]
    other = next(term for term in terms if term is not root)
    return root - other


def _is_square_root(term: sp.Expr) -> bool:
    _, rest = term.as_coeff_Mul()
    return isinstance(rest, sp.Pow) and rest.exp == sp.Rational(1, 2)


def _over_zero(f, top_value, x, a, direction, work: _Work):
    work.note(
        msg(
            "Putting {x} = {a} in gives {top_value}/0: the top stays "
            "near {top_value} while the bottom shrinks to 0, so the "
            "function grows without bound. Which way depends on the side",
            x=x,
            a=read_as(a),
            top_value=read_as(top_value),
        )
    )
    sides = {}
    for side in ("-", "+"):
        if direction in (side, "+-"):
            sides[side] = sp.limit(f, x, a, side)
    text = join("; ", [_from_side(side, value) for side, value in sides.items()])
    if direction != "+-":
        (value,) = sides.values()
        if direction == "-":
            one_side = msg("From the left it goes to {value}", value=_value_plain(value))
        else:
            one_side = msg("From the right it goes to {value}", value=_value_plain(value))
        work.value(one_side, value)
        return value
    if sides["-"] == sides["+"]:
        work.value(msg("Both sides agree: {text}", text=text), sides["+"])
        return sides["+"]
    work.value(
        msg("The two sides disagree ({text}), so the limit does not exist", text=text),
        DOES_NOT_EXIST,
    )
    return DOES_NOT_EXIST


def _at_infinity(f, x, a, work: _Work, depth: int):
    where = msg("infinity") if a == sp.oo else msg("minus infinity")
    top, bottom = sp.fraction(sp.together(f))
    if top.is_polynomial(x) and bottom.is_polynomial(x):
        top_degree = sp.degree(top, x) if top.has(x) else 0
        bottom_degree = sp.degree(bottom, x) if bottom.has(x) else 0
        if bottom_degree == 0:
            leading = sp.LT(sp.expand(top), x)
            value = sp.limit(leading, x, a)
            work.limit(
                msg(
                    "A polynomial behaves like its highest-power term as {x} goes to {where}",
                    x=x,
                    where=where,
                ),
                leading / bottom,
            )
            work.value(msg("So it goes to {value}", value=_value_plain(value)), value)
            return value
        if top_degree == 0:
            value = sp.limit(f, x, a)
            work.value(
                msg(
                    "The top stays {top} while the bottom grows without bound, "
                    "so the fraction shrinks to 0",
                    top=read_as(top),
                ),
                value,
            )
            return value
        power = x**bottom_degree
        divided = Quotient(sp.expand(top / power), sp.expand(bottom / power))
        work.limit(
            msg(
                "Divide the top and the bottom by {power}, the highest power in the bottom",
                power=read_as(power),
            ),
            divided,
        )
        value = sp.limit(f, x, a)
        if top_degree < bottom_degree:
            reason = msg(
                "every term with {x} in a denominator goes to 0, and the top goes to 0", x=x
            )
        elif top_degree == bottom_degree:
            reason = msg(
                "every term with {x} in a denominator goes to 0, leaving the "
                "ratio of the leading numbers",
                x=x,
            )
        else:
            reason = msg("the top still grows without bound while the bottom settles to a number")
        work.value(msg("As {x} goes to {where}, {reason}", x=x, where=where, reason=reason), value)
        return value

    top_limit, bottom_limit = sp.limit(top, x, a), sp.limit(bottom, x, a)
    if top_limit.is_infinite and bottom_limit.is_infinite and depth <= MAX_REWRITES:
        new_top, new_bottom = sp.diff(top, x), sp.diff(bottom, x)
        work.limit(
            msg(
                "Both grow without bound (infinity over infinity), so use "
                "L'Hopital's rule: the limit of top/bottom is the limit of "
                "top'/bottom'"
            ),
            _unevaluated_quotient(new_top, new_bottom),
        )
        return _at_infinity(sp.simplify(new_top / new_bottom), x, a, work, depth + 1)
    value = sp.limit(f, x, a)
    work.value(
        msg(
            "As {x} goes to {where}, it approaches {value}",
            x=x,
            where=where,
            value=_value_plain(value),
        ),
        value,
    )
    return value
