"""Expressions with letters: simplify, expand or factor them, with steps.

Each method is a function that writes its steps into a :class:`Steps` and
returns the result. The result is always checked against the input, so a
step-writer can never hand back something that is not equal to what was typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import sympy as sp
from sympy.core.parameters import distribute

from ..equivalence import Verdict, compare
from ..errors import UnsupportedError
from ..parse.plain import latex_of, parse_as_written, parse_expression, read_as
from ..steps.solution import SolutionStep
from .computation import METHOD_LABELS, Computation


class Steps:
    """Writes the steps of working on an expression into a :class:`Computation`."""

    def __init__(self, computation: Computation) -> None:
        self.computation = computation

    def show(self, text: str, expression: sp.Expr) -> None:
        self.computation.steps.append(
            SolutionStep(text=text, display=read_as(expression), display_latex=latex_of(expression))
        )

    def show_text(self, text: str, plain: str, latex: str) -> None:
        self.computation.steps.append(SolutionStep(text=text, display=plain, display_latex=latex))

    def note(self, text: str) -> None:
        self.computation.steps.append(SolutionStep(text=text))

    def condition(self, text: str) -> None:
        self.computation.conditions.append(text)


@dataclass
class Method:
    applies: Callable[[sp.Expr], bool]
    run: Callable[[sp.Expr, Steps], sp.Expr]


#: filled in by the modules that write the steps, in the order they are offered
METHODS: dict[str, Method] = {}


def method(name: str, applies: Callable[[sp.Expr], bool]):
    def decorator(run: Callable[[sp.Expr, Steps], sp.Expr]):
        METHODS[name] = Method(applies, run)
        return run

    return decorator


def compute_expression(text: str, method_name: str | None = None) -> Computation:
    with distribute(False):
        expression = parse_expression(text).expr
    letters = sorted(symbol.name for symbol in expression.free_symbols)
    available = [name for name, entry in METHODS.items() if entry.applies(expression)]
    if not available:
        raise UnsupportedError("there is nothing to simplify, expand or factor here")
    choice = method_name or default_method(expression, available)
    if choice not in available:
        options = ", ".join(available)
        raise UnsupportedError(f"the method '{choice}' does not apply here — try {options}")
    ordered = [choice, *[name for name in available if name != choice]]

    computation = Computation(
        operation=choice,
        title=f"{METHOD_LABELS[choice]} {read_as(expression)}",
        kind="expression",
        method=choice,
        methods=ordered,
        letters=letters,
    )
    steps = Steps(computation)
    start = _start(text, expression, steps)
    with distribute(False):
        result = METHODS[choice].run(start, steps)
    if not same_value(result, expression):
        # never show steps that do not add up
        computation.steps = computation.steps[:1]
        result = _fallback(choice, expression)
        steps.show(METHOD_LABELS[choice], result)
    if len(computation.steps) == 1:
        steps.note("This is already as simple as it gets")
    computation.finish(result)
    return computation


def default_method(expression: sp.Expr, available: list[str]) -> str:
    """Expand brackets, factor an expanded polynomial, simplify anything else."""
    polynomial = expression.is_polynomial(*expression.free_symbols)
    if polynomial and "expand" in available:
        return "expand"
    if polynomial and "factor" in available:
        return "factor"
    return "simplify" if "simplify" in available else available[0]


def same_value(result: sp.Expr, expression: sp.Expr) -> bool:
    """Equal wherever both are defined (ln(xy) and ln(x) + ln(y) count as equal)."""
    difference = sp.expand(sp.together(result - expression))
    if difference == 0 or sp.simplify(difference) == 0:
        return True
    return compare(result, expression).verdict is Verdict.OK


def _fallback(choice: str, expression: sp.Expr) -> sp.Expr:
    if choice == "expand":
        return sp.expand(expression)
    if choice == "factor":
        return sp.factor(expression)
    return sp.simplify(expression)


# --- what SymPy does silently while reading --------------------------------------------


def _start(text: str, expression: sp.Expr, steps: Steps) -> sp.Expr:
    """Show the expression as written, and name the rules SymPy used to tidy it."""
    try:
        written = parse_as_written(text)
    except Exception:  # the evaluated reading worked; this is only for show
        written = expression
    rules = tidy_rules(written)
    if rules and read_as(written) != read_as(expression):
        steps.show("Start from", written)
        steps.show(_join(rules), expression)
    else:
        steps.show("Start from", expression)
    return expression


def tidy_rules(written: sp.Basic) -> list[str]:
    """What turns ``written`` into its tidy form: like terms, exponent rules, numbers."""
    rules: list[str] = []

    def add(rule: str) -> None:
        if rule not in rules:
            rules.append(rule)

    for node in sp.preorder_traversal(written):
        if isinstance(node, sp.Pow) and isinstance(node.base, sp.Pow) and node.exp != -1:
            if node.base.exp != -1:
                add("A power of a power: multiply the exponents")
        elif isinstance(node, sp.Mul):
            bases: dict[sp.Expr, list[sp.Expr]] = {}
            numbers = 0
            for factor in node.args:
                if factor.is_Number:
                    numbers += 1
                    continue
                base, exponent = factor.as_base_exp()
                if isinstance(base, sp.Pow) and exponent == -1:
                    base, exponent = base.base, -base.exp
                bases.setdefault(base, []).append(exponent)
            if numbers > 1:
                add("Multiply the numbers")
            for exponents in bases.values():
                if len(exponents) > 1:
                    if any(exponent.could_extract_minus_sign() for exponent in exponents):
                        add("Divide powers with the same base: subtract the exponents")
                    else:
                        add("Multiply powers with the same base: add the exponents")
        elif isinstance(node, sp.Add):
            seen: set[sp.Expr] = set()
            for term in node.args:
                _, rest = term.as_coeff_Mul()
                if rest in seen and rest != 1:
                    add("Collect like terms")
                seen.add(rest)
            if sum(1 for term in node.args if term.is_Number) > 1:
                add("Add the numbers")
    return rules


def _join(rules: list[str]) -> str:
    if len(rules) == 1:
        return rules[0]
    return "; ".join([rules[0], *[rule[0].lower() + rule[1:] for rule in rules[1:]]])


def terms_of(expression: sp.Expr) -> list[sp.Expr]:
    return list(sp.Add.make_args(expression))


def sum_of(terms: list[sp.Expr]) -> sp.Expr:
    """The terms side by side, like terms not yet collected."""
    if not terms:
        return sp.Integer(0)
    if len(terms) == 1:
        return terms[0]
    return sp.Add(*terms, evaluate=False)


def show(expression: sp.Expr) -> str:
    return read_as(expression)
