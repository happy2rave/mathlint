"""A calculation as the student wrote it, and how to print it back.

SymPy evaluates as it builds, so ``6/8`` becomes ``3/4`` and ``12 : 3 * 2``
becomes ``8`` before anyone sees a step. This tree keeps what was written: a
fraction keeps its own numerator and denominator, a decimal stays a decimal,
and a division stays a division until it is worked out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from ..parse.plain import latex_of, read_as

# how tightly each kind of node binds, loosest first
SUM, NEG, PRODUCT, POWER, ATOM = 1, 2, 3, 4, 5


@dataclass
class Num:
    """A number: ``int``, ``frac`` (numerator ``top`` over ``bottom``), ``dec``, or
    ``exact`` for anything irrational such as ``6 sqrt(2)`` or ``pi``.

    ``keep`` marks a fraction that was written over a common denominator on
    purpose, so it is not reduced straight back.
    """

    value: sp.Expr
    style: str = "int"
    top: int = 0
    bottom: int = 1
    keep: bool = False


@dataclass
class Sum:
    terms: list
    signs: list[int]


@dataclass
class Product:
    """Factors multiplied (``*``, or ``""`` when written side by side) or divided (``:``)."""

    factors: list
    ops: list[str]


@dataclass
class Frac:
    top: object
    bottom: object


@dataclass
class Power:
    base: object
    exp: object


@dataclass
class Call:
    """``sqrt``, ``root3`` (a cube root), ``abs``, ``factorial``, ``ln``, ``exp``, ``sin``..."""

    name: str
    arg: object


@dataclass
class Neg:
    node: object


@dataclass
class Percent:
    node: object


@dataclass
class Printed:
    plain: str
    latex: str
    rank: int
    negative: bool = False
    starts_with_letter: bool = False
    notes: list[str] = field(default_factory=list)


def integer(value) -> Num:
    return Num(sp.Integer(value), "int")


def fraction(top: int, bottom: int, keep: bool = False) -> Num:
    if bottom < 0:
        top, bottom = -top, -bottom
    return Num(sp.Rational(top, bottom), "frac", int(top), int(bottom), keep)


def number(value: sp.Expr, decimal: bool = False) -> Num:
    """The tidiest leaf for a value: whole, decimal (if asked for and exact), fraction, or exact."""
    value = sp.nsimplify(value) if isinstance(value, sp.Float) else sp.sympify(value)
    if value.is_Integer:
        return integer(value)
    if value.is_Rational:
        if decimal and decimal_text(value) is not None:
            return Num(value, "dec")
        return fraction(int(value.p), int(value.q))
    return Num(value, "exact")


def decimal_text(value: sp.Rational) -> str | None:
    """``0.375`` for 3/8, or ``None`` when the decimal never ends."""
    top, bottom = int(value.p), int(value.q)
    rest, twos, fives = bottom, 0, 0
    while rest % 2 == 0:
        rest //= 2
        twos += 1
    while rest % 5 == 0:
        rest //= 5
        fives += 1
    if rest != 1:
        return None
    places = max(twos, fives)
    scaled = abs(top) * 10**places // bottom
    digits = str(scaled).rjust(places + 1, "0")
    text = f"{digits[:-places]}.{digits[-places:]}" if places else digits
    return ("-" if top < 0 else "") + text


def children(node) -> list:
    if isinstance(node, Sum):
        return list(node.terms)
    if isinstance(node, Product):
        return list(node.factors)
    if isinstance(node, Frac):
        return [node.top, node.bottom]
    if isinstance(node, Power):
        return [node.base, node.exp]
    if isinstance(node, Call | Neg | Percent):
        return [node.arg if isinstance(node, Call) else node.node]
    return []


def with_children(node, new: list):
    if isinstance(node, Sum):
        return Sum(new, list(node.signs))
    if isinstance(node, Product):
        return Product(new, list(node.ops))
    if isinstance(node, Frac):
        return Frac(*new)
    if isinstance(node, Power):
        return Power(*new)
    if isinstance(node, Call):
        return Call(node.name, new[0])
    if isinstance(node, Neg):
        return Neg(new[0])
    if isinstance(node, Percent):
        return Percent(new[0])
    return node


def bracketed(parent, child) -> bool:
    """Whether ``child`` sits inside brackets (a fraction bar, an exponent and a
    function's argument count), which decides what gets worked out first."""
    if isinstance(parent, Frac | Power | Call | Percent):
        return True
    if isinstance(parent, Neg):
        return isinstance(child, Sum | Product)
    if isinstance(parent, Sum | Product):
        inside_product = isinstance(parent, Product) and isinstance(child, Product)
        return isinstance(child, Sum) or inside_product
    return False


# --- printing -------------------------------------------------------------------------

_LATEX_FUNCTIONS = {
    "sin": r"\sin",
    "cos": r"\cos",
    "tan": r"\tan",
    "cot": r"\cot",
    "sec": r"\sec",
    "csc": r"\csc",
    "asin": r"\arcsin",
    "acos": r"\arccos",
    "atan": r"\arctan",
    "sinh": r"\sinh",
    "cosh": r"\cosh",
    "tanh": r"\tanh",
    "ln": r"\ln",
}


def plain(node) -> str:
    return render(node).plain


def latex(node) -> str:
    return render(node).latex


def render(node) -> Printed:
    if isinstance(node, Num):
        return _render_num(node)
    if isinstance(node, Sum):
        return _render_sum(node)
    if isinstance(node, Product):
        return _render_product(node)
    if isinstance(node, Frac):
        top, bottom = render(node.top), render(node.bottom)
        top_plain = _wrap(top.plain) if top.rank <= PRODUCT or top.negative else top.plain
        bottom_plain = (
            bottom.plain if bottom.rank > PRODUCT and not bottom.negative else _wrap(bottom.plain)
        )
        return Printed(
            f"{top_plain}/{bottom_plain}",
            rf"\frac{{{top.latex}}}{{{bottom.latex}}}",
            PRODUCT,
        )
    if isinstance(node, Power):
        base, exp = render(node.base), render(node.exp)
        simple_base = base.rank == ATOM and not base.negative and "/" not in base.plain
        base_plain = base.plain if simple_base else _wrap(base.plain)
        base_latex = base.latex if simple_base else _wrap_latex(base.latex)
        exp_plain = exp.plain if exp.rank == ATOM and not exp.negative else _wrap(exp.plain)
        return Printed(f"{base_plain}^{exp_plain}", f"{base_latex}^{{{exp.latex}}}", POWER)
    if isinstance(node, Call):
        return _render_call(node)
    if isinstance(node, Neg):
        inner = render(node.node)
        wrap = inner.rank <= PRODUCT or inner.negative
        return Printed(
            "-" + (_wrap(inner.plain) if wrap else inner.plain),
            "-" + (_wrap_latex(inner.latex) if wrap else inner.latex),
            NEG,
            negative=True,
        )
    if isinstance(node, Percent):
        inner = render(node.node)
        wrap = inner.rank < ATOM or inner.negative
        return Printed(
            (_wrap(inner.plain) if wrap else inner.plain) + "%",
            (_wrap_latex(inner.latex) if wrap else inner.latex) + r"\%",
            ATOM,
        )
    raise TypeError(f"cannot print {node!r}")


def _render_num(node: Num) -> Printed:
    value = node.value
    if node.style == "int":
        return Printed(str(value), str(value), ATOM, negative=value < 0)
    if node.style == "dec":
        text = decimal_text(value) or str(value)
        return Printed(text, text, ATOM, negative=value < 0)
    if node.style == "frac":
        sign = "-" if node.top < 0 else ""
        return Printed(
            f"{node.top}/{node.bottom}",
            rf"{sign}\frac{{{abs(node.top)}}}{{{node.bottom}}}",
            PRODUCT,
            negative=node.top < 0,
        )
    text = _constants(read_as(value), value)
    rank = ATOM
    if isinstance(value, sp.Add):
        rank = SUM
    elif isinstance(value, sp.Mul):
        rank = PRODUCT
    elif isinstance(value, sp.Pow) and value.exp.is_Rational and value.exp.q != 1:
        rank = ATOM  # a root prints as sqrt(...)
    elif isinstance(value, sp.Pow):
        rank = POWER
    return Printed(
        text,
        latex_of(value),
        rank,
        negative=value.could_extract_minus_sign(),
        starts_with_letter=text[:1].isalpha(),
    )


def _render_sum(node: Sum) -> Printed:
    plain_parts: list[str] = []
    latex_parts: list[str] = []
    for index, (term, sign) in enumerate(zip(node.terms, node.signs, strict=True)):
        printed = render(term)
        wrap = isinstance(term, Sum) or (index > 0 and (printed.negative or printed.rank < PRODUCT))
        body_plain = _wrap(printed.plain) if wrap else printed.plain
        body_latex = _wrap_latex(printed.latex) if wrap else printed.latex
        if index == 0:
            plain_parts.append(("-" if sign < 0 else "") + body_plain)
            latex_parts.append(("-" if sign < 0 else "") + body_latex)
        else:
            operator = " - " if sign < 0 else " + "
            plain_parts.append(operator + body_plain)
            latex_parts.append(operator + body_latex)
    first = render(node.terms[0])
    return Printed(
        "".join(plain_parts),
        "".join(latex_parts),
        SUM,
        negative=node.signs[0] < 0 or first.negative,
    )


def _render_product(node: Product) -> Printed:
    plain_text = ""
    latex_text = ""
    for index, (factor, op) in enumerate(zip(node.factors, node.ops, strict=True)):
        printed = render(factor)
        wrap = isinstance(factor, Sum | Product) or printed.rank < PRODUCT
        if index > 0:
            wrap = wrap or printed.negative or (op == ":" and printed.rank <= PRODUCT)
        body_plain = _wrap(printed.plain) if wrap else printed.plain
        body_latex = _wrap_latex(printed.latex) if wrap else printed.latex
        if index == 0:
            plain_text, latex_text = body_plain, body_latex
            continue
        side_by_side = op == "" and (
            wrap or printed.starts_with_letter or printed.plain.startswith("(")
        )
        if side_by_side:
            plain_text += body_plain
            latex_text += body_latex
        elif op == ":":
            plain_text += f" / {body_plain}"
            latex_text += rf" \div {body_latex}"
        else:
            plain_text += f" * {body_plain}"
            latex_text += rf" \times {body_latex}"
    first = render(node.factors[0])
    return Printed(plain_text, latex_text, PRODUCT, negative=first.negative)


def _render_call(node: Call) -> Printed:
    inner = render(node.arg)
    name = node.name
    if name == "sqrt":
        return Printed(
            f"sqrt({inner.plain})", rf"\sqrt{{{inner.latex}}}", ATOM, starts_with_letter=True
        )
    if name.startswith("root"):
        degree = name[4:]
        return Printed(
            f"root{degree}({inner.plain})",
            rf"\sqrt[{degree}]{{{inner.latex}}}",
            ATOM,
            starts_with_letter=True,
        )
    if name == "abs":
        return Printed(f"|{inner.plain}|", rf"\left|{inner.latex}\right|", ATOM)
    if name == "factorial":
        simple = inner.rank == ATOM and not inner.negative
        body_plain = inner.plain if simple else _wrap(inner.plain)
        body_latex = inner.latex if simple else _wrap_latex(inner.latex)
        return Printed(f"{body_plain}!", f"{body_latex}!", ATOM)
    if name == "exp":
        simple = inner.rank == ATOM and not inner.negative
        return Printed(
            f"e^{inner.plain}" if simple else f"e^({inner.plain})",
            f"e^{{{inner.latex}}}",
            POWER,
            starts_with_letter=True,
        )
    command = _LATEX_FUNCTIONS.get(name, rf"\operatorname{{{name}}}")
    return Printed(
        f"{name}({inner.plain})",
        rf"{command}\left({inner.latex}\right)",
        ATOM,
        starts_with_letter=True,
    )


def _constants(text: str, value: sp.Expr) -> str:
    """``e`` and ``i`` the way they are written by hand, not SymPy's ``E`` and ``I``."""
    if value.has(sp.E):
        text = re.sub(r"\bE\b", "e", text)
    if value.has(sp.I):
        text = re.sub(r"\bI\b", "i", text)
    return text


def _wrap(text: str) -> str:
    return f"({text})"


def _wrap_latex(text: str) -> str:
    return rf"\left({text}\right)"
