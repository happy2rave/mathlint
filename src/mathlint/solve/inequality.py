"""Inequalities: solved like equations, except that the sign has a direction.

Multiplying or dividing both sides by a negative number turns the sign around,
and that is the one step students most often get wrong, so it is always said
out loud. Every answer is compared with SymPy's before it is shown.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.core.parameters import distribute

from ..errors import ParseError, UnsupportedError
from ..i18n import join, msg
from ..parse.latex import latex_to_plain
from ..parse.plain import latex_of, parse_expression, read_as
from ..parse.unicode_math import normalize_unicode
from ..steps.solution import Solution, SolutionStep
from .intervals import as_inequality, as_intervals, number_line, pieces, same_set

_SOLVE_PREFIX = re.compile(r"^solve\s+", re.IGNORECASE)
_RELATION = re.compile(r"(<=|>=|<|>)")
_LATEX_RELATIONS = [
    (re.compile(r"\\leq?(?![A-Za-z])"), "<="),
    (re.compile(r"\\geq?(?![A-Za-z])"), ">="),
    (re.compile(r"\\leqslant(?![A-Za-z])"), "<="),
    (re.compile(r"\\geqslant(?![A-Za-z])"), ">="),
    (re.compile(r"\\lt(?![A-Za-z])"), "<"),
    (re.compile(r"\\gt(?![A-Za-z])"), ">"),
]

LATEX = {"<": "<", "<=": r"\le", ">": ">", ">=": r"\ge"}
FLIPPED = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
RELATIONS = {
    "<": sp.StrictLessThan,
    "<=": sp.LessThan,
    ">": sp.StrictGreaterThan,
    ">=": sp.GreaterThan,
}

KIND_LABELS = {
    "linear": msg("Linear inequality"),
    "polynomial": msg("Polynomial inequality"),
    "rational": msg("Rational inequality"),
    "absolute": msg("Absolute-value inequality"),
    "compound": msg("Double inequality"),
    "other": msg("Inequality"),
}

METHOD_LABELS = {
    "balance": msg("Balance both sides", context="method"),
    "sign-chart": msg("Sign chart", context="method"),
    "cases": msg("Split into cases", context="method"),
    "sympy": msg("Computer algebra", context="method"),
}


@dataclass
class Inequality:
    """``lhs op rhs`` with ``op`` one of ``<``, ``<=``, ``>``, ``>=``."""

    lhs: sp.Expr
    op: str
    rhs: sp.Expr

    def plain(self) -> str:
        return f"{read_as(self.lhs)} {self.op} {read_as(self.rhs)}"

    def latex(self) -> str:
        return f"{latex_of(self.lhs)} {LATEX[self.op]} {latex_of(self.rhs)}"

    def relational(self) -> sp.Basic:
        return RELATIONS[self.op](self.lhs, self.rhs)

    def holds(self, variable: sp.Symbol, value: sp.Expr) -> bool:
        left = self.lhs.subs(variable, value)
        right = self.rhs.subs(variable, value)
        return bool(RELATIONS[self.op](left, right))

    def turned_around(self) -> Inequality:
        """``a < b`` read from the other side: ``b > a``."""
        return Inequality(self.rhs, FLIPPED[self.op], self.lhs)


def looks_like_inequality(text: str) -> bool:
    try:
        return bool(_RELATION.search(_normalize(text)))
    except ParseError:
        return False


def _normalize(text: str) -> str:
    body = _SOLVE_PREFIX.sub("", normalize_unicode(text).strip())
    for pattern, replacement in _LATEX_RELATIONS:
        body = pattern.sub(f" {replacement} ", body)
    if "\\" in body:
        body = latex_to_plain(body)
    return body.replace("≤", "<=").replace("≥", ">=").replace("⩽", "<=").replace("⩾", ">=")


def parse_inequality(text: str) -> list[Inequality]:
    """One inequality, or two for ``a < x < b``."""
    body = _normalize(text)
    parts = _RELATION.split(body)
    if len(parts) not in (3, 5):
        raise ParseError(msg("write one inequality, or two joined like 1 < 2x + 3 < 7"))
    with distribute(False):
        sides = [parse_expression(part).expr for part in parts[0::2]]
    ops = parts[1::2]
    return [Inequality(sides[i], ops[i], sides[i + 1]) for i in range(len(ops))]


@dataclass
class InequalitySolution(Solution):
    kind: str = "other"
    method: str = "balance"
    methods: list[str] = field(default_factory=list)
    variable: sp.Symbol | None = None
    letters: list[str] = field(default_factory=list)
    answer: sp.Set = field(default_factory=lambda: sp.S.EmptySet)
    answer_latex: str = ""
    interval_text: str = ""
    interval_latex: str = ""

    def finish(self, answer: sp.Set) -> None:
        assert self.variable is not None
        self.answer = answer
        self.result = answer
        self.summary, self.answer_latex = as_inequality(self.variable, answer)
        self.interval_text, self.interval_latex = as_intervals(answer)
        if answer not in (sp.S.Reals, sp.S.EmptySet):
            self.summary += msg(", that is {interval_text}", interval_text=self.interval_text)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "kind": f"{self.kind}-inequality",
                "kind_label": KIND_LABELS.get(self.kind, "Inequality"),
                "method": self.method,
                "methods": [
                    {"id": method, "label": METHOD_LABELS.get(method, method)}
                    for method in self.methods
                ],
                "variable": str(self.variable),
                "letters": list(self.letters),
                "answers": [],
                "answer_text": self.summary,
                "answer_latex": self.answer_latex,
                "interval_text": self.interval_text,
                "interval_latex": self.interval_latex,
                "number_line": number_line(self.answer),
                "everything": self.answer == sp.S.Reals,
            }
        )
        return data


class Steps:
    def __init__(self, solution: InequalitySolution) -> None:
        self.solution = solution

    def show(self, text: str, inequality: Inequality, operation: str = "") -> None:
        self.solution.steps.append(
            SolutionStep(
                text=text,
                operation=operation,
                display=inequality.plain(),
                display_latex=inequality.latex(),
            )
        )

    def text(self, text: str, plain: str = "", latex: str = "") -> None:
        self.solution.steps.append(SolutionStep(text=text, display=plain, display_latex=latex))


def solve_inequality(
    text: str, method: str | None = None, variable: str | None = None
) -> InequalitySolution:
    """Solve an inequality in one unknown, showing every step."""
    inequalities = parse_inequality(text)
    letters = sorted(
        set().union(*[item.lhs.free_symbols | item.rhs.free_symbols for item in inequalities]),
        key=lambda symbol: symbol.name,
    )
    unknown = _unknown(letters, variable)
    shown = inequalities[0].plain()
    if len(inequalities) == 2:
        shown += f" {inequalities[1].op} {read_as(inequalities[1].rhs)}"
    solution = InequalitySolution(
        operation="solve",
        title=f"Solve {shown}",
        variable=unknown,
        letters=[letter.name for letter in letters],
    )
    steps = Steps(solution)

    if len(inequalities) == 2:
        solution.kind = "compound"
        solution.methods = ["balance"]
        answer = _compound(inequalities, unknown, steps)
    else:
        inequality = inequalities[0]
        solution.kind = classify(inequality, unknown)
        solution.methods = methods_for(solution.kind)
        if method is not None and method not in solution.methods:
            options = ", ".join(solution.methods)
            raise UnsupportedError(
                msg(
                    "the method '{method}' does not apply here — try {options}",
                    method=method,
                    options=options,
                )
            )
        solution.method = method or solution.methods[0]
        steps.show(msg("Start from"), inequality)
        answer = SOLVERS[solution.method](inequality, unknown, steps)

    expected = _expected(inequalities, unknown)
    if expected is not None and not same_set(answer, expected):
        # never show steps that do not add up
        solution.steps = solution.steps[:1]
        steps.text(msg("Solve (computer algebra)"))
        answer = expected
    solution.finish(answer)
    return solution


def _unknown(letters: list[sp.Symbol], variable: str | None) -> sp.Symbol:
    if not letters:
        raise ParseError(msg("there is nothing to solve for — this inequality has no unknown"))
    if variable:
        chosen = next((letter for letter in letters if letter.name == variable), None)
        if chosen is None:
            raise ParseError(
                msg("{variable} does not appear in this inequality", variable=variable)
            )
        return chosen
    if len(letters) == 1:
        return letters[0]
    raise UnsupportedError(msg("inequalities with more than one letter are not solved yet"))


def classify(inequality: Inequality, variable: sp.Symbol) -> str:
    difference = inequality.lhs - inequality.rhs
    if difference.has(sp.Abs):
        return "absolute"
    together = sp.together(sp.expand(difference))
    numerator, denominator = sp.fraction(together)
    if denominator.has(variable):
        return "rational"
    if together.is_polynomial(variable):
        degree = sp.degree(together, variable)
        return "linear" if degree <= 1 else "polynomial"
    return "other"


def methods_for(kind: str) -> list[str]:
    return {
        "linear": ["balance", "sign-chart"],
        "polynomial": ["sign-chart"],
        "rational": ["sign-chart"],
        "absolute": ["cases"],
    }.get(kind, ["sympy"])


# --- linear: the balance method --------------------------------------------------------------


def _balance(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    lhs, op, rhs = inequality.lhs, inequality.op, inequality.rhs

    expanded = (sp.expand(lhs), sp.expand(rhs))
    if expanded != (lhs, rhs):
        lhs, rhs = expanded
        steps.show(msg("Expand the brackets"), Inequality(lhs, op, rhs))

    denominator = _common_denominator(lhs, rhs, variable)
    if denominator != 1:
        lhs, rhs = sp.expand(lhs * denominator), sp.expand(rhs * denominator)
        steps.show(
            msg(
                "Multiply both sides by {denominator} to clear the "
                "fractions; {denominator} is positive, so the sign stays",
                denominator=denominator,
            ),
            Inequality(lhs, op, rhs),
            operation=f"* {denominator}",
        )

    left_x, left_c = _split(lhs, variable)
    right_x, right_c = _split(rhs, variable)

    # keep the unknown's coefficient positive, so no division by a negative is needed
    if right_x != 0 and (left_x == 0 or right_x > left_x):
        lhs, rhs = rhs, lhs
        op = FLIPPED[op]
        left_x, left_c, right_x, right_c = right_x, right_c, left_x, left_c
        steps.show(
            msg(
                "Swap the sides, so the side with more {variable} is on the "
                "left; the sign turns around with them",
                variable=variable,
            ),
            Inequality(lhs, op, rhs),
        )

    if right_x != 0:
        term = right_x * variable
        lhs, rhs = sp.expand(lhs - term), sp.expand(rhs - term)
        steps.show(_move_text(term), Inequality(lhs, op, rhs), operation=_operation(-term))
        left_x -= right_x

    if left_x == 0:
        true = bool(RELATIONS[op](lhs, rhs))
        verdict = msg("always true") if true else msg("never true")
        steps.text(
            msg(
                "There is no {variable} left, and {lhs} {op} {rhs} is {verdict}",
                variable=variable,
                lhs=read_as(lhs),
                op=op,
                rhs=read_as(rhs),
                verdict=verdict,
            )
        )
        return sp.S.Reals if true else sp.S.EmptySet

    if left_c != 0:
        lhs, rhs = sp.expand(lhs - left_c), sp.expand(rhs - left_c)
        steps.show(_move_text(left_c), Inequality(lhs, op, rhs), operation=_operation(-left_c))

    coefficient = left_x
    value = sp.expand(right_c - left_c)

    answer = value / coefficient
    if coefficient != 1:
        if coefficient < 0:
            op = FLIPPED[op]
            steps.show(
                msg(
                    "Divide both sides by {coefficient}. Dividing by a negative "
                    "number turns the inequality sign around",
                    coefficient=read_as(coefficient),
                ),
                Inequality(variable, op, answer),
                operation=f"/ ({read_as(coefficient)})",
            )
        else:
            steps.show(
                msg(
                    "Divide both sides by {coefficient}; it is positive, so the sign stays",
                    coefficient=read_as(coefficient),
                ),
                Inequality(variable, op, answer),
                operation=f"/ {read_as(coefficient)}",
            )
    result = _ray(op, answer)
    _check_points(inequality, variable, result, steps)
    return result


def _ray(op: str, value: sp.Expr) -> sp.Set:
    """``x < 3`` as a set."""
    if op == "<":
        return sp.Interval.open(-sp.oo, value)
    if op == "<=":
        return sp.Interval(-sp.oo, value)
    if op == ">":
        return sp.Interval.open(value, sp.oo)
    return sp.Interval(value, sp.oo)


def _split(side: sp.Expr, variable: sp.Symbol) -> tuple[sp.Expr, sp.Expr]:
    polynomial = sp.Poly(side, variable)
    return polynomial.coeff_monomial(variable), polynomial.coeff_monomial(1)


def _common_denominator(lhs: sp.Expr, rhs: sp.Expr, variable: sp.Symbol) -> int:
    denominators = [
        int(coefficient.q)
        for side in (lhs, rhs)
        for coefficient in sp.Poly(side, variable).coeffs()
        if coefficient.is_Rational
    ]
    return math.lcm(*denominators) if denominators else 1


def _move_text(term: sp.Expr) -> str:
    if term.could_extract_minus_sign():
        return msg("Add {term} to both sides", term=read_as(-term))
    return msg("Subtract {term} from both sides", term=read_as(term))


def _operation(change: sp.Expr) -> str:
    return (
        f"+ {read_as(change)}" if not change.could_extract_minus_sign() else f"- {read_as(-change)}"
    )


def _check_points(
    inequality: Inequality, variable: sp.Symbol, answer: sp.Set, steps: Steps
) -> None:
    """Try a whole number on each side of the boundary: one must work, one must not."""
    boundary = answer.inf if answer.inf != -sp.oo else answer.sup
    inside = sp.floor(boundary) - 1 if answer.inf == -sp.oo else sp.ceiling(boundary) + 1
    outside = sp.ceiling(boundary) + 1 if answer.inf == -sp.oo else sp.floor(boundary) - 1
    parts = []
    for value, expected in ((inside, True), (outside, False)):
        holds = inequality.holds(variable, value)
        if holds != expected:
            return  # the check disagrees: leave it to the final comparison
        left = inequality.lhs.subs(variable, value)
        right = inequality.rhs.subs(variable, value)
        truth = msg("true") if holds else msg("false")
        parts.append(
            msg(
                "{variable} = {value} gives {left} {op} {right}, {truth}",
                variable=variable,
                value=read_as(value),
                left=read_as(left),
                op=inequality.op,
                right=read_as(right),
                truth=truth,
            )
        )
    steps.text(msg("Check a number on each side: {checks}", checks=join("; ", parts)))


# --- two at once -----------------------------------------------------------------------------


def _compound(inequalities: list[Inequality], variable: sp.Symbol, steps: Steps) -> sp.Set:
    first, second = inequalities
    steps.text(
        msg("A double inequality is two inequalities that must both hold"),
        f"{first.plain()} and {second.plain()}",
        rf"{first.latex()} \quad\text{{and}}\quad {second.latex()}",
    )
    answers = []
    for part in (first, second):
        steps.show(msg("Solve"), part)
        kind = classify(part, variable)
        answers.append(SOLVERS[methods_for(kind)[0]](part, variable, steps))
    both = sp.Intersection(*answers)
    plain, latex = as_inequality(variable, both)
    steps.text(msg("Both must hold, so the answer is where they overlap"), plain, latex)
    return both


# --- anything else -------------------------------------------------------------------------


def _computer(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    answer = _solve_set(inequality, variable)
    plain, latex = as_inequality(variable, answer)
    steps.text(msg("Solve (computer algebra)"), plain, latex)
    return answer


def _solve_set(inequality: Inequality, variable: sp.Symbol) -> sp.Set:
    return sp.solve_univariate_inequality(
        inequality.relational(), variable, relational=False, domain=sp.S.Reals
    )


def _expected(inequalities: list[Inequality], variable: sp.Symbol) -> sp.Set | None:
    try:
        return sp.Intersection(*[_solve_set(item, variable) for item in inequalities])
    except (NotImplementedError, ValueError, TypeError):
        return None


def _sign_chart(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    from .signchart import sign_chart

    return sign_chart(inequality, variable, steps)


def _cases(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    from .signchart import absolute_cases

    return absolute_cases(inequality, variable, steps)


SOLVERS = {
    "balance": _balance,
    "sign-chart": _sign_chart,
    "cases": _cases,
    "sympy": _computer,
}

__all__ = [
    msg("Inequality"),
    "InequalitySolution",
    "looks_like_inequality",
    "parse_inequality",
    "pieces",
    "solve_inequality",
]
