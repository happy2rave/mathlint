"""Sign charts: how polynomial and rational inequalities are solved by hand.

Everything goes to one side, the side is factored, and the numbers where a
factor is zero cut the number line into intervals. One test number per
interval gives the sign of every factor there, and so the sign of the whole
side. A denominator is never multiplied across — its sign is not known — and
the numbers that make it zero are never part of the answer.
"""

from __future__ import annotations

import sympy as sp

from ..i18n import msg
from ..parse.plain import latex_of, read_as
from .inequality import FLIPPED, LATEX, RELATIONS, Inequality, Steps
from .intervals import as_inequality

SIGN_PLAIN = {1: "+", -1: "-", 0: "0"}


def sign_chart(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    op = inequality.op
    with sp.evaluate(True):
        side = sp.together(sp.expand(inequality.lhs - inequality.rhs))
    top, bottom = sp.fraction(side)
    top, bottom = sp.expand(top), sp.expand(bottom)
    rational = bottom.has(variable)

    shown = inequality.lhs  # what the last step showed on the left
    if inequality.rhs != 0:
        text = (
            msg(
                "Move everything to the left side and write it as one "
                "fraction. Do not multiply by the denominator: its sign is "
                "not known"
            )
            if rational
            else msg("Move everything to the left side")
        )
        shown = _quotient(top, bottom)
        steps.show(text, Inequality(shown, op, 0))

    # a positive leading number is easier to read: -x^2 + 4 > 0 is x^2 - 4 < 0
    constant = _leading_sign(top, variable) * _leading_sign(bottom, variable)
    if constant < 0:
        top = sp.expand(-top)
        op = FLIPPED[op]
        shown = _quotient(top, bottom)
        steps.show(
            msg(
                "Multiply both sides by -1; multiplying by a negative number turns the sign around"
            ),
            Inequality(shown, op, 0),
            operation="* (-1)",
        )
    if _leading_sign(bottom, variable) < 0:
        top, bottom = sp.expand(-top), sp.expand(-bottom)

    top_number, top_factors = sp.factor_list(top, variable)
    bottom_number, bottom_factors = sp.factor_list(bottom, variable)
    number = top_number / bottom_number
    factored = _quotient(
        number * sp.Mul(*[factor**power for factor, power in top_factors]),
        sp.Mul(*[factor**power for factor, power in bottom_factors]),
    )
    if read_as(factored) != read_as(shown):
        steps.show(msg("Factor"), Inequality(factored, op, 0))

    zeros = _zeros(top_factors, variable)
    poles = _zeros(bottom_factors, variable)
    if poles:
        excluded = ", ".join(f"{variable} = {read_as(point)}" for point in poles)
        steps.text(
            msg(
                "The denominator is zero at {excluded}, so that is never part of the answer",
                excluded=excluded,
            )
        )
    cuts = sorted(set(zeros) | set(poles), key=float)
    rows = [(factor, power, False) for factor, power in top_factors] + [
        (factor, power, True) for factor, power in bottom_factors
    ]
    # left to right by where each factor is zero; factors that never are, last
    rows.sort(key=lambda row: min(map(float, _zeros([row[:2]], variable)), default=float("inf")))

    if not cuts:
        test = sp.Integer(0)
        holds = bool(RELATIONS[op](factored.subs(variable, test), 0))
        value = read_as(factored.subs(variable, test))
        if holds:
            text = msg(
                "The left side is never zero, so it has the same sign everywhere. At "
                "{variable} = 0 it is {value}, so the inequality is always true",
                variable=variable,
                value=value,
            )
        else:
            text = msg(
                "The left side is never zero, so it has the same sign everywhere. At "
                "{variable} = 0 it is {value}, so the inequality is never true",
                variable=variable,
                value=value,
            )
        steps.text(text)
        return sp.S.Reals if holds else sp.S.EmptySet

    where = ", ".join(f"{variable} = {read_as(point)}" for point in cuts)
    steps.text(
        msg("The left side can only change sign where a factor is zero: {where}", where=where)
    )

    intervals = _intervals(cuts)
    tests = [_test_point(interval) for interval in intervals]
    signs = [[_sign(factor**power, variable, test) for test in tests] for factor, power, _ in rows]
    totals = [_sign(factored, variable, test) for test in tests]
    steps.text(
        msg("Make a sign chart: one test number in each interval gives the sign of every factor"),
        *_chart(variable, intervals, rows, signs, totals, number),
    )

    wanted = 1 if op in (">", ">=") else -1
    answer = sp.Union(
        *[interval for interval, total in zip(intervals, totals, strict=True) if total == wanted]
    )
    if op in ("<=", ">="):
        answer = sp.Union(answer, sp.FiniteSet(*[point for point in zeros if point not in poles]))
    answer = sp.Complement(answer, sp.FiniteSet(*poles)) if poles else answer
    plain, latex = as_inequality(variable, answer)
    keep = {
        (True, False): msg("Keep the intervals where the left side is positive"),
        (True, True): msg("Keep the intervals where the left side is positive or zero"),
        (False, False): msg("Keep the intervals where the left side is negative"),
        (False, True): msg("Keep the intervals where the left side is negative or zero"),
    }
    steps.text(keep[wanted > 0, op in ("<=", ">=")], plain, latex)
    return answer


def _quotient(top: sp.Expr, bottom: sp.Expr) -> sp.Expr:
    return top if bottom == 1 else top / bottom


def _leading_sign(polynomial: sp.Expr, variable: sp.Symbol) -> int:
    if not polynomial.has(variable):
        return 1 if polynomial >= 0 else -1
    return 1 if sp.Poly(polynomial, variable).LC() > 0 else -1


def _zeros(factors: list[tuple[sp.Expr, int]], variable: sp.Symbol) -> list[sp.Expr]:
    points: list[sp.Expr] = []
    for factor, _ in factors:
        for root in sp.real_roots(sp.Poly(factor, variable)):
            value = root if not isinstance(root, sp.CRootOf) else sp.Float(root.evalf(12), 12)
            if value not in points:
                points.append(value)
    return points


def _intervals(cuts: list[sp.Expr]) -> list[sp.Interval]:
    ends = [-sp.oo, *cuts, sp.oo]
    return [sp.Interval.open(left, right) for left, right in zip(ends, ends[1:], strict=False)]


def _test_point(interval: sp.Interval) -> sp.Expr:
    """A simple number inside: a whole number if there is one, else the middle."""
    start, end = interval.start, interval.end
    if start == -sp.oo:
        return sp.floor(end) - 1
    if end == sp.oo:
        return sp.ceiling(start) + 1
    candidate = sp.floor(start) + 1
    if start < candidate < end:
        return candidate
    return (start + end) / 2


def _sign(expression: sp.Expr, variable: sp.Symbol, value: sp.Expr) -> int:
    number = expression.subs(variable, value)
    return 1 if number > 0 else -1 if number < 0 else 0


def _chart(variable, intervals, rows, signs, totals, number) -> tuple[str, str]:
    """The chart in plain text (a table) and in LaTeX (an array)."""
    headers = [_interval_plain(interval) for interval in intervals]
    names = [_row_name(factor, power, below) for factor, power, below in rows]
    if number != 1:
        names.insert(0, read_as(number))
        signs = [[1 if number > 0 else -1] * len(intervals), *signs]
    names.append(msg("left side"))
    table = [[str(variable), *headers]]
    table += [
        [name, *[SIGN_PLAIN[value] for value in row]]
        for name, row in zip(names, [*signs, totals], strict=True)
    ]
    widths = [max(len(line[column]) for line in table) for column in range(len(table[0]))]
    plain_lines = [
        " | ".join(cell.center(width) for cell, width in zip(line, widths, strict=True))
        for line in table
    ]
    plain_lines.insert(1, "-+-".join("-" * width for width in widths))
    plain = "\n".join(plain_lines)

    latex_names = [latex_of(number)] if number != 1 else []
    latex_names += [_row_latex(factor, power, below) for factor, power, below in rows]
    latex_rows = [
        " & ".join([name, *[_SIGN_LATEX[value] for value in row]])
        for name, row in zip(latex_names, signs, strict=True)
    ]
    header = " & ".join([latex_of(variable), *[_interval_latex(i) for i in intervals]])
    total = " & ".join([r"\text{left side}", *[_SIGN_LATEX[value] for value in totals]])
    columns = "c|" + "c" * len(intervals)
    latex = (
        rf"\begin{{array}}{{{columns}}} {header} \\ \hline "
        + r" \\ ".join(latex_rows)
        + rf" \\ \hline {total} \end{{array}}"
    )
    return plain, latex


_SIGN_LATEX = {1: "+", -1: "-", 0: "0"}


def _row_name(factor: sp.Expr, power: int, below: bool) -> str:
    name = read_as(factor) if power == 1 else f"({read_as(factor)})^{power}"
    if not below:
        return name
    return f"1/{name}" if name.isalnum() else f"1/({name})"


def _row_latex(factor: sp.Expr, power: int, below: bool) -> str:
    body = latex_of(factor) if power == 1 else rf"\left({latex_of(factor)}\right)^{{{power}}}"
    return rf"\frac{{1}}{{{body}}}" if below else body


def _interval_plain(interval: sp.Interval) -> str:
    left = "-inf" if interval.start == -sp.oo else read_as(interval.start)
    right = "inf" if interval.end == sp.oo else read_as(interval.end)
    return f"({left}, {right})"


def _interval_latex(interval: sp.Interval) -> str:
    left = r"-\infty" if interval.start == -sp.oo else latex_of(interval.start)
    right = r"\infty" if interval.end == sp.oo else latex_of(interval.end)
    return rf"({left}, {right})"


# --- absolute values -------------------------------------------------------------------------


def absolute_cases(inequality: Inequality, variable: sp.Symbol, steps: Steps) -> sp.Set:
    """``|A| < b`` is ``-b < A < b``; ``|A| > b`` is ``A < -b`` or ``A > b``."""
    from .inequality import SOLVERS, classify, methods_for

    isolated = _isolate_absolute(inequality)
    if isolated is None:
        return SOLVERS["sympy"](inequality, variable, steps)
    inside, op, bound, changed = isolated
    if changed:
        steps.show(msg("Get the absolute value on its own"), Inequality(sp.Abs(inside), op, bound))

    if bound < 0 or (bound == 0 and op in ("<", ">=")):
        # |A| is never negative
        always = op in (">", ">=")
        inside_text, bound_text = read_as(inside), read_as(bound)
        if always:
            text = msg(
                "An absolute value is never negative, so |{inside}| {op} {bound} is always true",
                inside=inside_text,
                op=op,
                bound=bound_text,
            )
        else:
            text = msg(
                "An absolute value is never negative, so |{inside}| {op} {bound} is never true",
                inside=inside_text,
                op=op,
                bound=bound_text,
            )
        steps.text(text)
        return sp.S.Reals if always else sp.S.EmptySet
    if bound == 0 and op == "<=":
        steps.text(
            msg("An absolute value is never negative, so it can only be 0 here"),
            f"{read_as(inside)} = 0",
            f"{latex_of(inside)} = 0",
        )
        return sp.FiniteSet(*sp.solveset(inside, variable, sp.S.Reals))

    def solve_part(part: Inequality) -> sp.Set:
        steps.show(msg("Solve"), part)
        kind = classify(part, variable)
        return SOLVERS[methods_for(kind)[0]](part, variable, steps)

    if op in ("<", "<="):
        low, high = Inequality(-bound, op, inside), Inequality(inside, op, bound)
        steps.text(
            msg(
                "An absolute value {op} {bound} means the inside is between {bound2} and {bound}",
                op=op,
                bound=read_as(bound),
                bound2=read_as(-bound),
            ),
            f"{read_as(-bound)} {op} {read_as(inside)} {op} {read_as(bound)}",
            rf"{latex_of(-bound)} {LATEX[op]} {latex_of(inside)} {LATEX[op]} {latex_of(bound)}",
        )
        answer = sp.Intersection(solve_part(low), solve_part(high))
        plain, latex = as_inequality(variable, answer)
        steps.text(msg("Both must hold, so the answer is where they overlap"), plain, latex)
        return answer
    flipped = FLIPPED[op]
    below, above = Inequality(inside, flipped, -bound), Inequality(inside, op, bound)
    steps.text(
        msg(
            "An absolute value {op} {bound} means the inside is below {bound2} or above {bound}",
            op=op,
            bound=read_as(bound),
            bound2=read_as(-bound),
        ),
        f"{below.plain()} or {above.plain()}",
        rf"{below.latex()} \quad\text{{or}}\quad {above.latex()}",
    )
    answer = sp.Union(solve_part(below), solve_part(above))
    plain, latex = as_inequality(variable, answer)
    steps.text(msg("Either one is enough, so the answer is both parts together"), plain, latex)
    return answer


def _isolate_absolute(inequality: Inequality):
    """``k|A| + m op c`` -> ``(A, op, bound, changed)``, or None for anything else."""
    side = sp.expand(inequality.lhs - inequality.rhs)
    terms = sp.Add.make_args(side)
    with_abs = [term for term in terms if term.has(sp.Abs)]
    rest = sp.Add(*[term for term in terms if not term.has(sp.Abs)])
    if len(with_abs) != 1 or rest.free_symbols:
        return None
    coefficient, absolute = with_abs[0].as_coeff_Mul()
    if not isinstance(absolute, sp.Abs) or not coefficient.is_number:
        return None
    op = inequality.op if coefficient > 0 else FLIPPED[inequality.op]
    bound = -rest / coefficient
    changed = not (isinstance(inequality.lhs, sp.Abs) and inequality.rhs.is_number)
    return absolute.args[0], op, bound, changed
