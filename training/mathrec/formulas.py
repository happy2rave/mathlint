"""Formulas to learn from: the math students bring to mathlint.

Every formula is one line of the notebook, in the recognizer's spelling (see
vocab.py). The kinds follow what mathlint solves and checks — equations of every
sort, systems one equation at a time, inequalities, arithmetic, expressions to
expand and factor, derivatives, integrals, limits, differential equations, a
line of someone's working ("= 2x + 1"), answers ("x=2\\text{ or }x=3") and
matrices — with weights that favour what is most common.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from .vocab import normalize

LETTERS = "xxxxxxyyyztabnkm"


class Maker:
    """Random pieces of math, all in the recognizer's spelling."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    # -- numbers ---------------------------------------------------------------------
    def natural(self, top: int = 9) -> str:
        return str(self.rng.randint(1, top))

    def integer(self, top: int = 9) -> str:
        value = self.rng.randint(-top, top)
        return str(value)

    def number(self) -> str:
        roll = self.rng.random()
        if roll < 0.7:
            return self.natural(self.rng.choice([9, 12, 20, 50, 100]))
        if roll < 0.85:
            return f"{self.rng.randint(0, 20)}.{self.rng.randint(1, 99)}"
        return self.frac(self.natural(), self.natural())

    def coefficient(self) -> str:
        """In front of a letter: often nothing, often a small number."""
        roll = self.rng.random()
        if roll < 0.3:
            return ""
        if roll < 0.9:
            return str(self.rng.randint(2, 12))
        return self.frac(self.natural(), self.natural())

    # -- structures ------------------------------------------------------------------
    @staticmethod
    def frac(top: str, bottom: str) -> str:
        return rf"\frac{{{top}}}{{{bottom}}}"

    @staticmethod
    def power(base: str, exponent: str) -> str:
        return f"{base}^{{{exponent}}}"

    @staticmethod
    def brackets(inside: str) -> str:
        return rf"\left({inside}\right)"

    def signed(self, parts: list[str]) -> str:
        """Terms joined by + and -, the first one maybe negative."""
        out = ""
        for index, part in enumerate(parts):
            negative = part.startswith("-")
            part = part.removeprefix("-")
            if index == 0:
                out = ("-" if negative or self.rng.random() < 0.15 else "") + part
            else:
                sign = self.rng.choice("++-")
                if negative:  # a term that is already negative flips the sign in front
                    sign = "-" if sign == "+" else "+"
                out += sign + part
        return out

    # -- expressions -----------------------------------------------------------------
    def monomial(self, x: str, degree: int) -> str:
        if degree == 0:
            return self.natural(12)
        body = x if degree == 1 else self.power(x, str(degree))
        return self.coefficient() + body

    def polynomial(self, x: str, degree: int | None = None) -> str:
        degree = degree if degree is not None else self.rng.choice([1, 1, 2, 2, 2, 3])
        extra = self.rng.sample(range(degree + 1), k=self.rng.randint(1, degree + 1))
        degrees = sorted({degree, *extra}, reverse=True)
        return self.signed([self.monomial(x, d) for d in degrees])

    def linear(self, x: str) -> str:
        return self.signed([self.coefficient() + x, self.natural(20)])

    def factor(self, x: str) -> str:
        return self.brackets(self.linear(x))

    def function(self, x: str) -> str:
        name = self.rng.choice([r"\sin", r"\cos", r"\tan", r"\ln", r"\ln", r"\log", r"\sqrt"])
        inside = self.rng.choice([x, x, self.linear(x), self.power(x, "2")])
        if name == r"\sqrt":
            return rf"\sqrt{{{inside}}}"
        if len(inside) == 1 and self.rng.random() < 0.6:
            return f"{name} {inside}"
        return name + self.brackets(inside)

    def expression(self, x: str, depth: int = 0) -> str:
        roll = self.rng.random()
        if depth > 1 or roll < 0.4:
            return self.polynomial(x)
        if roll < 0.55:
            return self.factor(x) + self.factor(x)
        if roll < 0.7:
            return self.frac(self.expression(x, depth + 1), self.expression(x, depth + 1))
        if roll < 0.85:
            return self.signed([self.coefficient() + self.function(x), self.polynomial(x, 1)])
        return self.power(self.factor(x), str(self.rng.randint(2, 3)))


def _equation(m: Maker, x: str) -> str:
    kind = m.rng.random()
    if kind < 0.25:
        return f"{m.linear(x)}={m.linear(x) if m.rng.random() < 0.5 else m.natural(30)}"
    if kind < 0.35:
        return f"{m.natural()}{m.factor(x)}={m.linear(x)}"
    if kind < 0.55:
        return f"{m.polynomial(x, 2)}=0"
    if kind < 0.62:
        return f"{m.polynomial(x, 3)}=0"
    if kind < 0.72:
        return f"{m.frac(m.natural(), m.linear(x))}={m.frac(m.natural(), m.linear(x))}"
    if kind < 0.78:
        return rf"\sqrt{{{m.linear(x)}}}+{m.natural()}={x}"
    if kind < 0.84:
        return rf"\left|{m.linear(x)}\right|={m.natural(12)}"
    if kind < 0.9:
        base = m.rng.choice("2359")
        return f"{m.power(base, m.linear(x))}={m.natural(81)}"
    if kind < 0.95:
        return rf"\ln{m.brackets(x)}+\ln{m.brackets(m.linear(x))}=\ln{m.brackets(m.natural())}"
    return f"{m.polynomial(x, 1)}={m.frac(m.natural(), m.natural())}"


def _system_line(m: Maker, x: str) -> str:
    y = m.rng.choice("yz")
    return f"{m.coefficient()}{x}{m.rng.choice('+-')}{m.coefficient()}{y}={m.integer(30)}"


def _inequality(m: Maker, x: str) -> str:
    op = m.rng.choice(["<", ">", r"\le", r"\ge"])
    kind = m.rng.random()
    if kind < 0.4:
        return f"{m.linear(x)}{op}{m.integer(20)}"
    if kind < 0.7:
        return f"{m.polynomial(x, 2)}{op}0"
    if kind < 0.85:
        return rf"\left|{m.linear(x)}\right|{op}{m.natural()}"
    return f"{m.integer()}<{m.linear(x)}<{m.natural(20)}"


def _arithmetic(m: Maker, _: str) -> str:
    parts = [m.number() for _ in range(m.rng.randint(2, 4))]
    out = parts[0]
    for part in parts[1:]:
        out += m.rng.choice(["+", "-", r"\cdot", r"\times", r"\div"]) + part
    if m.rng.random() < 0.3:
        out = m.power(m.natural(), m.natural(4)) + m.rng.choice("+-") + out
    if m.rng.random() < 0.15:
        out = rf"\sqrt{{{m.natural(144)}}}" + m.rng.choice("+-") + out
    return out


def _expression(m: Maker, x: str) -> str:
    return m.expression(x)


def _derivative(m: Maker, x: str) -> str:
    order = r"\frac{d}{dx}" if m.rng.random() < 0.85 else r"\frac{d^{2}}{dx^{2}}"
    return order + m.brackets(m.signed([m.expression("x"), m.function("x")][: m.rng.randint(1, 2)]))


def _integral(m: Maker, _: str) -> str:
    body = m.rng.choice(
        [
            m.polynomial("x"),
            m.function("x"),
            m.frac(m.natural(), m.linear("x")),
            "x" + m.power("e", "x"),
            m.expression("x"),
        ]
    )
    if m.rng.random() < 0.3:
        return rf"\int_{{{m.integer(3)}}}^{{{m.natural(5)}}}{body}\,dx"
    return rf"\int {body}\,dx"


def _limit(m: Maker, _: str) -> str:
    to = m.rng.choice([m.integer(5), m.integer(5), r"\infty", "0"])
    return rf"\lim_{{x\to{to}}}" + m.expression("x")


def _ode(m: Maker, _: str) -> str:
    y1, y2 = r"y^{\prime}", r"y^{\prime\prime}"
    kind = m.rng.random()
    if kind < 0.4:
        return f"{y1}={m.coefficient()}y"
    if kind < 0.8:
        first, second = m.rng.choice("+-"), m.rng.choice("+-")
        return f"{y2}{first}{m.coefficient()}{y1}{second}{m.coefficient()}y=0"
    return f"{y1}+{m.coefficient()}y={m.power('e', 'x')}"


def _working(m: Maker, x: str) -> str:
    """A later line of someone's working: it starts with "="."""
    return "=" + m.expression(x)


def _answer(m: Maker, x: str) -> str:
    kind = m.rng.random()
    if kind < 0.5:
        return f"{x}={m.integer(20)}"
    if kind < 0.8:
        return rf"{x}={m.integer()}\text{{ or }}{x}={m.integer()}"
    return f"{x}={m.frac(m.integer(), m.natural())}"


def _matrix(m: Maker, _: str) -> str:
    size = m.rng.choice([2, 2, 3])

    def entry() -> str:
        return m.integer(9) if m.rng.random() < 0.9 else m.frac(m.natural(), m.natural())

    rows = ["&".join(entry() for _ in range(size)) for _ in range(size)]
    prefix = m.rng.choice(["", "", r"\sim"])
    return prefix + r"\begin{pmatrix}" + r"\\".join(rows) + r"\end{pmatrix}"


KINDS: dict[str, tuple[float, Callable[[Maker, str], str]]] = {
    "equation": (0.26, _equation),
    "system": (0.05, _system_line),
    "inequality": (0.09, _inequality),
    "arithmetic": (0.10, _arithmetic),
    "expression": (0.10, _expression),
    "derivative": (0.07, _derivative),
    "integral": (0.07, _integral),
    "limit": (0.05, _limit),
    "ode": (0.03, _ode),
    "working": (0.08, _working),
    "answer": (0.07, _answer),
    "matrix": (0.03, _matrix),
}


def sample(rng: random.Random, kind: str | None = None) -> str:
    """One formula, in the recognizer's spelling."""
    if kind is None:
        names = list(KINDS)
        kind = rng.choices(names, weights=[KINDS[name][0] for name in names])[0]
    maker = Maker(rng)
    lettered = ("equation", "inequality", "expression", "working", "answer")
    x = rng.choice(LETTERS) if kind in lettered else "x"
    return normalize(KINDS[kind][1](maker, x))


def corpus(n: int, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    return [sample(rng) for _ in range(n)]
