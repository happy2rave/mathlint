"""Work out a calculation one operation at a time, in the order of operations.

Each round finds the operations that are ready (everything they work on is
already a number) and does the one that comes first: the innermost brackets,
then powers, roots and functions, then multiplying and dividing, then adding
and subtracting, left to right. Whole-number arithmetic of the same rank is
done together, so ``2*3 + 4*5`` takes one step to ``6 + 20``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import sympy as sp

from ..errors import ParseError, UnsupportedError
from ..i18n import msg
from .reader import negate, settle_fraction
from .tree import (
    Call,
    Frac,
    Neg,
    Num,
    Percent,
    Power,
    Product,
    Sum,
    bracketed,
    children,
    decimal_text,
    fraction,
    integer,
    number,
    plain,
    with_children,
)

MAX_STEPS = 200
MAX_POWER_DIGITS = 1000

_SYMPY_FUNCTIONS = {
    "ln": sp.log,
    "exp": sp.exp,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "cot": sp.cot,
    "sec": sp.sec,
    "csc": sp.csc,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
}

#: what a step says when it did several operations of the same sort at once
_TOGETHER = {
    "add": msg("Add and subtract"),
    "multiply": msg("Multiply"),
    "divide": msg("Divide"),
    "power": msg("Work out the powers"),
    "root": msg("Work out the roots"),
    "percent": msg("Write the percentages as decimals"),
    "reduce": msg("Reduce the fractions"),
    "function": msg("Use the exact values"),
}


@dataclass
class Change:
    node: object
    text: str = ""  # nothing to say: a silent tidy-up, not a step
    batch: str = ""


@dataclass
class Round:
    text: str
    tree: object


def work_out(tree) -> tuple[list[Round], Num]:
    """The steps from ``tree`` to a single number, and that number."""
    rounds: list[Round] = []
    tree = settle(tree)
    for _ in range(MAX_STEPS):
        ready = list(_ready(tree))
        if not ready:
            break
        best = max(ready, key=lambda item: (item.depth, -item.level, -item.order))
        change = operate(best.node)
        changes = [(best.path, change)]
        if change.batch:
            for other in ready:
                if other is best or (other.depth, other.level) != (best.depth, best.level):
                    continue
                other_change = operate(other.node)
                if other_change.batch == change.batch:
                    changes.append((other.path, other_change))
        for path, done in changes:
            tree = _replace(tree, path, done.node)
        tree = settle(tree)
        if change.text:
            texts = {done.text for _, done in changes}
            text = change.text if len(texts) == 1 else _TOGETHER.get(change.batch, change.text)
            rounds.append(Round(text, tree))
    if not isinstance(tree, Num):
        raise UnsupportedError(msg("this calculation has too many steps to show"))
    return rounds, tree


def value_of(node) -> sp.Expr:
    """The value of a tree, straight from SymPy — the check on every step."""
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Sum):
        pairs = zip(node.terms, node.signs, strict=True)
        return sp.Add(*[sign * value_of(term) for term, sign in pairs])
    if isinstance(node, Product):
        total = sp.Integer(1)
        for factor, op in zip(node.factors, node.ops, strict=True):
            value = value_of(factor)
            if op == ":":
                if value == 0:
                    raise ParseError(msg("this divides by zero, so it has no value"))
                total /= value
            else:
                total *= value
        return total
    if isinstance(node, Frac):
        bottom = value_of(node.bottom)
        if bottom == 0:
            raise ParseError(msg("this divides by zero, so it has no value"))
        return value_of(node.top) / bottom
    if isinstance(node, Power):
        return _power(value_of(node.base), value_of(node.exp))
    if isinstance(node, Neg):
        return -value_of(node.node)
    if isinstance(node, Percent):
        return value_of(node.node) / 100
    if isinstance(node, Call):
        return _call(node.name, value_of(node.arg))
    raise TypeError(node)


# --- which operations are ready ----------------------------------------------------------


@dataclass
class _Ready:
    path: tuple[int, ...]
    node: object
    depth: int
    level: int
    order: int


def _level(node) -> int:
    if isinstance(node, Num):
        return 0
    if isinstance(node, Power | Call | Percent | Neg):
        return 1
    if isinstance(node, Product | Frac):
        return 2
    return 3


def _ready(tree):
    counter = [0]

    def visit(node, path, depth):
        counter[0] += 1
        order = counter[0]
        kids = children(node)
        if isinstance(node, Num):
            if _reducible(node):
                yield _Ready(path, node, depth, 0, order)
            return
        if all(isinstance(kid, Num) and not _reducible(kid) for kid in kids):
            yield _Ready(path, node, depth, _level(node), order)
            return
        for index, kid in enumerate(kids):
            yield from visit(kid, (*path, index), depth + (1 if bracketed(node, kid) else 0))

    yield from visit(tree, (), 0)


def _reducible(node: Num) -> bool:
    if node.style != "frac" or node.keep:
        return False
    return node.bottom == 1 or math.gcd(node.top, node.bottom) > 1


def _replace(tree, path: tuple[int, ...], new):
    if not path:
        return new
    kids = children(tree)
    kids[path[0]] = _replace(kids[path[0]], path[1:], new)
    return with_children(tree, kids)


def settle(node):
    """The tidy-ups nobody writes as a step: ``-(5)`` is ``-5``, ``3/4`` is a fraction."""
    kids = children(node)
    if kids:
        node = with_children(node, [settle(kid) for kid in kids])
    if isinstance(node, Neg) and isinstance(node.node, Num):
        return negate(node.node)
    if isinstance(node, Frac):
        return settle_fraction(node)
    if isinstance(node, Sum) and len(node.terms) == 1:
        term = node.terms[0]
        return term if node.signs[0] > 0 else settle(Neg(term))
    if isinstance(node, Product) and len(node.factors) == 1:
        return node.factors[0]
    if isinstance(node, Num) and node.style == "exact" and node.value.is_Rational:
        return number(node.value)
    return node


# --- the operations ------------------------------------------------------------------


def operate(node) -> Change:
    if isinstance(node, Num):
        return _reduce(node)
    if isinstance(node, Sum):
        return _sum(node)
    if isinstance(node, Product):
        return _product(node)
    if isinstance(node, Frac):
        return _fraction(node)
    if isinstance(node, Power):
        return _power_step(node)
    if isinstance(node, Call):
        return _call_step(node)
    if isinstance(node, Percent):
        value = node.node.value / 100
        return Change(
            number(value, decimal=True),
            msg(
                "A percentage is a number out of 100: {node} = {number}",
                node=plain(node),
                number=plain(number(value, True)),
            ),
            "percent",
        )
    if isinstance(node, Neg):
        return Change(negate(node.node))
    raise TypeError(node)


def _reduce(node: Num) -> Change:
    result = number(sp.Rational(node.top, node.bottom))
    if node.bottom == 1:
        return Change(
            result,
            msg(
                "A fraction over 1 is a whole number: {node} = {result}",
                node=plain(node),
                result=plain(result),
            ),
        )
    if result.style == "int":
        return Change(
            result,
            msg("Divide: {node} = {result}", node=plain(node), result=plain(result)),
            "reduce",
        )
    factor = math.gcd(node.top, node.bottom)
    return Change(
        result,
        msg(
            "Reduce the fraction: divide the numerator and the denominator by {factor}",
            factor=factor,
        ),
        "reduce",
    )


def _styles(nums) -> set[str]:
    return {num.style for num in nums}


def _sum(node: Sum) -> Change:
    terms: list[Num] = node.terms
    styles = _styles(terms)
    values = [sign * term.value for term, sign in zip(terms, node.signs, strict=True)]
    if "exact" in styles:
        return _exact(node, sp.Add(*values), msg("Add the like terms"))
    total = sp.Add(*values)
    if styles <= {"int", "dec"}:
        return Change(number(total, decimal="dec" in styles), _sum_text(node), "add")
    if "dec" in styles:
        return Change(
            Sum([_as_fraction(term) for term in terms], list(node.signs)),
            msg("Write the decimals as fractions"),
        )
    bottoms = [term.bottom if term.style == "frac" else 1 for term in terms]
    if len(set(bottoms)) == 1:
        tops = Sum([integer(term.top) for term in terms], list(node.signs))
        if all(sign < 0 for sign in node.signs[1:]):
            text = msg("The denominators are the same, so subtract the numerators")
        elif len(terms) > 2 and any(sign < 0 for sign in node.signs):
            text = msg("The denominators are the same, so add and subtract the numerators")
        else:
            text = msg("The denominators are the same, so add the numerators")
        return Change(Frac(tops, integer(bottoms[0])), text)
    common = math.lcm(*bottoms)
    rewritten = [
        fraction(
            (term.top if term.style == "frac" else int(term.value)) * (common // bottom),
            common,
            keep=True,
        )
        for term, bottom in zip(terms, bottoms, strict=True)
    ]
    text = msg("Write the fractions over the common denominator {common}", common=common)
    if "int" in styles:
        text = msg(
            "Write everything as a fraction over the common denominator {common}", common=common
        )
    return Change(Sum(rewritten, list(node.signs)), text)


def _sum_text(node: Sum) -> str:
    signs = node.signs[1:]
    if len(node.terms) == 2:
        second = node.terms[1].value
        if second < 0:
            if signs[0] < 0:
                return msg("Subtracting a negative number is the same as adding")
            return msg("Adding a negative number is the same as subtracting")
        return msg("Subtract") if signs[0] < 0 else msg("Add")
    has_negative = any(term.value < 0 for term in node.terms)
    if all(sign > 0 for sign in signs) and not has_negative:
        return msg("Add")
    if all(sign < 0 for sign in signs) and not has_negative and len(signs) == 1:
        return msg("Subtract")
    return msg("Add and subtract from left to right")


def _product(node: Product) -> Change:
    factors: list[Num] = node.factors
    styles = _styles(factors)
    if ":" not in node.ops and styles <= {"int", "dec"}:
        total = sp.Mul(*[factor.value for factor in factors])
        return Change(number(total, decimal="dec" in styles), msg("Multiply"), "multiply")
    first, second, op = factors[0], factors[1], node.ops[1]
    change = _pair(first, op, second)
    if len(factors) == 2:
        return change
    rest = Product([change.node, *factors[2:]], ["*", *node.ops[2:]])
    return Change(rest, change.text, "")


def _pair(first: Num, op: str, second: Num) -> Change:
    divide = op == ":"
    if divide and second.value == 0:
        raise ParseError(msg("this divides by zero, so it has no value"))
    styles = _styles([first, second])
    if "exact" in styles:
        value = first.value / second.value if divide else first.value * second.value
        pair = Product([first, second], ["*", op])
        return _exact(pair, value, msg("Divide") if divide else msg("Multiply"))
    if "dec" in styles and "frac" in styles:
        return Change(
            Product([_as_fraction(first), _as_fraction(second)], ["*", op]),
            msg("Write the decimal as a fraction"),
        )
    if styles <= {"int", "dec"}:
        if not divide:
            value = first.value * second.value
            return Change(number(value, decimal="dec" in styles), msg("Multiply"), "multiply")
        value = first.value / second.value
        if value.is_Integer or ("dec" in styles and decimal_text(value) is not None):
            return Change(number(value, decimal=True), msg("Divide"), "divide")
        if styles == {"int"}:
            return Change(
                fraction(int(first.value), int(second.value)),
                msg("Write the division as a fraction"),
            )
        return Change(
            Product([_as_fraction(first), _as_fraction(second)], ["*", op]),
            msg("Write the decimals as fractions"),
        )
    # whole numbers and fractions
    if divide:
        if second.style == "frac" and first.value == 1:
            return Change(
                _reciprocal(second), msg("1 divided by a fraction is the fraction flipped over")
            )
        if second.style == "frac":
            return Change(
                Product([first, _reciprocal(second)], ["*", "*"]),
                msg("Dividing by a fraction is multiplying by its reciprocal (flip it over)"),
            )
        return Change(
            Frac(integer(first.top), Product([integer(first.bottom), second], ["*", "*"])),
            msg(
                "Dividing by {second} multiplies the denominator by {second}", second=plain(second)
            ),
        )
    if first.style == "frac" and second.style == "frac":
        return Change(
            Frac(
                Product([integer(first.top), integer(second.top)], ["*", "*"]),
                Product([integer(first.bottom), integer(second.bottom)], ["*", "*"]),
            ),
            msg("Multiply the numerators, and multiply the denominators"),
        )
    whole, part = (first, second) if first.style == "int" else (second, first)
    if whole.value == 1:
        return Change(part, msg("Multiplying by 1 changes nothing"))
    top = (
        Product([whole, integer(part.top)], ["*", "*"])
        if whole is first
        else Product([integer(part.top), whole], ["*", "*"])
    )
    return Change(
        Frac(top, integer(part.bottom)), msg("Multiply the whole number by the numerator")
    )


def _fraction(node: Frac) -> Change:
    top, bottom = node.top, node.bottom
    if bottom.value == 0:
        raise ParseError(msg("this divides by zero, so it has no value"))
    styles = _styles([top, bottom])
    if "exact" in styles:
        value = top.value / bottom.value
        if _has_root(bottom.value) and not _has_root(sp.fraction(sp.together(value))[1]):
            return Change(
                number(value),
                msg(
                    "Rationalise the denominator: multiply the numerator and the "
                    "denominator by {factor}",
                    factor=plain(Num(_root_part(bottom.value), "exact")),
                ),
            )
        return _exact(node, value, msg("Simplify the fraction"))
    if "dec" in styles:
        value = top.value / bottom.value
        if value.is_Integer or decimal_text(value) is not None:
            return Change(number(value, decimal=True), msg("Divide"), "divide")
        return Change(
            Frac(_as_fraction(top), _as_fraction(bottom)), msg("Write the decimals as fractions")
        )
    if bottom.style == "frac" and top.value == 1:
        return Change(_reciprocal(bottom), msg("1 over a fraction is the fraction flipped over"))
    if bottom.style == "frac":
        return Change(
            Product([top, _reciprocal(bottom)], ["*", "*"]),
            msg("Dividing by a fraction is multiplying by its reciprocal (flip it over)"),
        )
    return Change(
        Frac(integer(top.top), Product([integer(top.bottom), bottom], ["*", "*"])),
        msg("Dividing by {bottom} multiplies the denominator by {bottom}", bottom=plain(bottom)),
    )


def _power_step(node: Power) -> Change:
    base, exp = node.base, node.exp
    styles = _styles([base, exp])
    if exp.value.is_negative:
        if base.value == 0:
            raise ParseError(msg("0 to a negative power divides by zero, so it has no value"))
        positive = negate(exp)
        if base.style == "frac":
            flipped = _reciprocal(base)
            new = flipped if positive.value == 1 else Power(flipped, positive)
            return Change(new, msg("A negative exponent flips the fraction over"))
        inner = base if positive.value == 1 else Power(base, positive)
        return Change(Frac(integer(1), inner), msg("A negative exponent means one over the power"))
    if "exact" in styles:
        return _exact(node, _power(base.value, exp.value), msg("Work out the power"))
    if exp.style == "dec":
        return Change(Power(base, _as_fraction(exp)), msg("Write the exponent as a fraction"))
    if exp.style == "frac":
        root = Call(f"root{exp.bottom}" if exp.bottom != 2 else "sqrt", base)
        name = _root_name(exp.bottom)
        if exp.top == 1:
            return Change(root, msg("A power of {exp} is the {root}", exp=plain(exp), root=name))
        return Change(
            Power(root, integer(exp.top)),
            msg(
                "A power of {exp} is the {root}, then the power {top}",
                exp=plain(exp),
                root=name,
                top=exp.top,
            ),
        )
    power = int(exp.value)
    if power == 0:
        if base.value == 0:
            raise ParseError(msg("0^0 has no agreed value"))
        return Change(integer(1), msg("Any number except 0 to the power 0 is 1"), "power")
    if power == 1:
        return Change(base, msg("A power of 1 leaves the number as it is"), "power")
    if base.style == "frac":
        return Change(
            Frac(Power(integer(base.top), exp), Power(integer(base.bottom), exp)),
            msg("Raise the numerator and the denominator to the power"),
        )
    value = _power(base.value, exp.value)
    result = number(value, decimal=base.style == "dec")
    text = msg("Work out the power: {node} = {result}", node=plain(node), result=plain(result))
    shown = plain(base) if not base.value.is_negative else f"({plain(base)})"
    if power <= 5 and len(shown) <= 6:
        text = msg(
            "Work out the power: {node} = {product}",
            node=plain(node),
            product=" * ".join([shown] * power),
        )
    return Change(result, text, "power")


def _call_step(node: Call) -> Change:
    arg: Num = node.arg
    name = node.name
    if name == "sqrt" or name.startswith("root"):
        return _root(node, 2 if name == "sqrt" else int(name[4:]))
    if name == "abs":
        result = number(abs(arg.value), decimal=arg.style == "dec")
        if arg.style == "frac":
            result = fraction(abs(arg.top), arg.bottom, arg.keep)
        return Change(
            result,
            msg(
                "The absolute value is the distance from 0: {node} = {result}",
                node=plain(node),
                result=plain(result),
            ),
        )
    if name == "factorial":
        if not arg.value.is_Integer or arg.value < 0:
            raise UnsupportedError(msg("the factorial is only for whole numbers 0, 1, 2, ..."))
        whole = int(arg.value)
        if whole > 1000:
            raise ParseError(msg("that number is too big to compute"))
        result = integer(math.factorial(whole))
        if 2 <= whole <= 8:
            product = " * ".join(str(n) for n in range(whole, 0, -1))
            return Change(result, f"{whole}! = {product}")
        return Change(result, msg("Work out {whole}!", whole=whole))
    value = _call(name, arg.value)
    function = _SYMPY_FUNCTIONS[name]
    if value.has(function) or (name == "exp" and isinstance(value, sp.exp)):
        return Change(Num(value, "exact"))
    return Change(
        number(value),
        msg(
            "Use the exact value: {node} = {number}", node=plain(node), number=plain(number(value))
        ),
    )


def _root(node: Call, degree: int) -> Change:
    arg: Num = node.arg
    name = _root_name(degree)
    if arg.style == "exact":
        return _exact(node, _call(node.name, arg.value), msg("Simplify the root"))
    if arg.style == "frac":
        return Change(
            Frac(Call(node.name, integer(arg.top)), Call(node.name, integer(arg.bottom))),
            msg(
                "The {root} of a fraction is the root of the numerator "
                "over the root of the denominator",
                root=name,
            ),
        )
    value = _call(node.name, arg.value)
    if arg.style == "dec":
        if value.is_Rational and decimal_text(value) is not None:
            result = number(value, decimal=True)
            return Change(
                result,
                msg("Work out the root: {node} = {result}", node=plain(node), result=plain(result)),
                "root",
            )
        return Change(Call(node.name, _as_fraction(arg)), msg("Write the decimal as a fraction"))
    whole = int(arg.value)
    if whole < 0:
        if degree % 2:
            return Change(
                Neg(Call(node.name, integer(-whole))),
                msg("The {root} of a negative number is negative", root=name),
            )
        return Change(
            Num(value, "exact"),
            msg(
                "The {root} of a negative number is not a real number: "
                "it is {value}, where i^2 = -1",
                root=name,
                value=plain(Num(value, "exact")),
            ),
        )
    if value.is_Integer:
        return Change(
            integer(value),
            msg(
                "{node} = {value}, because {value}^{degree} = {whole}",
                node=plain(node),
                value=value,
                degree=degree,
                whole=whole,
            ),
            "root",
        )
    coefficient, rest = value.as_coeff_Mul()
    if coefficient.is_Integer and coefficient > 1:
        taken = int(coefficient) ** degree
        return Change(
            Num(value, "exact"),
            msg(
                "Take out the factor {taken} = {coefficient}^{degree}: "
                "{node} = {first} * {second} = {value}",
                taken=taken,
                coefficient=coefficient,
                degree=degree,
                node=plain(node),
                first=plain(Call(node.name, integer(taken))),
                second=plain(Call(node.name, integer(whole // taken))),
                value=plain(Num(value, "exact")),
            ),
            "",
        )
    return Change(Num(value, "exact"))


# --- helpers -------------------------------------------------------------------------


def _exact(node, value: sp.Expr, text: str) -> Change:
    """An operation on roots, pi and friends: a step only when something combined."""
    written = _unevaluated(node)
    if sp.count_ops(value) < sp.count_ops(written):
        return Change(number(value), text)
    return Change(number(value))


def _unevaluated(node) -> sp.Expr:
    """The operation as written, for counting what the answer saved."""
    values = [kid.value for kid in children(node)]
    if isinstance(node, Sum):
        return sp.Add(
            *[
                value if sign > 0 else sp.Mul(-1, value, evaluate=False)
                for value, sign in zip(values, node.signs, strict=True)
            ],
            evaluate=False,
        )
    if isinstance(node, Product):
        return sp.Mul(
            *[
                sp.Pow(value, -1, evaluate=False) if op == ":" else value
                for value, op in zip(values, node.ops, strict=True)
            ],
            evaluate=False,
        )
    if isinstance(node, Frac):
        return sp.Mul(values[0], sp.Pow(values[1], -1, evaluate=False), evaluate=False)
    if isinstance(node, Power):
        return sp.Pow(values[0], values[1], evaluate=False)
    if isinstance(node, Call):
        with sp.evaluate(False):
            return _call(node.name, values[0])
    return node.value


def _as_fraction(num: Num) -> Num:
    if num.style == "dec":
        return number(num.value)
    return num


def _reciprocal(num: Num) -> Num:
    if num.style == "frac":
        return fraction(num.bottom, num.top)
    return fraction(1, int(num.value))


def _root_name(degree: int) -> str:
    return {2: msg("square root"), 3: msg("cube root")}.get(degree) or msg(
        "{step}th root", step=degree
    )


def _power(base: sp.Expr, exponent: sp.Expr) -> sp.Expr:
    if base.is_number and exponent.is_number and base.is_real and exponent.is_real:
        size = abs(float(exponent)) * math.log10(abs(float(base))) if base != 0 else 0
        if size > MAX_POWER_DIGITS:
            raise ParseError(msg("that number is too big to compute"))
    if exponent.is_Rational and not exponent.is_Integer and exponent.q % 2 and base.is_negative:
        return sp.real_root(base, exponent.q) ** exponent.p
    return base**exponent


def _call(name: str, value: sp.Expr) -> sp.Expr:
    if name == "sqrt":
        return sp.sqrt(value)
    if name.startswith("root"):
        degree = int(name[4:])
        if degree % 2 and value.is_negative:
            return sp.real_root(value, degree)
        return sp.root(value, degree)
    if name == "abs":
        return sp.Abs(value)
    if name == "factorial":
        return sp.factorial(value)
    return _SYMPY_FUNCTIONS[name](value)


def _has_root(value: sp.Expr) -> bool:
    return any(
        isinstance(node, sp.Pow) and node.exp.is_Rational and not node.exp.is_Integer
        for node in sp.preorder_traversal(value)
    )


def _root_part(value: sp.Expr) -> sp.Expr:
    for node in sp.preorder_traversal(value):
        if isinstance(node, sp.Pow) and node.exp.is_Rational and not node.exp.is_Integer:
            return node
    return value
