"""Where every symbol of a formula goes.

``parse`` turns a formula (in the recognizer's spelling) into a tree —
fractions, powers and subscripts, roots, brackets that grow with what they hold,
matrices, integrals and limits — and ``place`` lays the tree out, TeX-style, as
a flat list of things to draw: glyphs at a position and size, and rules (the
bar of a fraction, the top of a root).

The layout does not know what the symbols look like. It asks a ``Metrics``
object how wide and how tall each symbol is, so the same geometry serves the
printed renderer (a font's own measurements) and the handwritten one (the
proportions of a handwritten sample).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .vocab import tokenize

# -- the tree ----------------------------------------------------------------------------


@dataclass
class Sym:
    token: str


@dataclass
class Word:
    """Letters drawn upright, as one unit: sin, ln, lim, or."""

    text: str


@dataclass
class Space:
    em: float


@dataclass
class Row:
    items: list = field(default_factory=list)


@dataclass
class Frac:
    top: Row
    bottom: Row


@dataclass
class Root:
    body: Row
    index: Row | None = None


@dataclass
class Scripts:
    base: object
    sup: Row | None = None
    sub: Row | None = None


@dataclass
class Fenced:
    left: str
    body: Row
    right: str


@dataclass
class Matrix:
    rows: list[list[Row]]


@dataclass
class Limit:
    under: Row | None = None


WORDS = {
    r"\sin": "sin",
    r"\cos": "cos",
    r"\tan": "tan",
    r"\cot": "cot",
    r"\sec": "sec",
    r"\csc": "csc",
    r"\ln": "ln",
    r"\log": "log",
    r"\exp": "exp",
    r"\arcsin": "arcsin",
    r"\arccos": "arccos",
    r"\arctan": "arctan",
    r"\sinh": "sinh",
    r"\cosh": "cosh",
    r"\tanh": "tanh",
    r"\text{ or }": "or",
}
FENCES = {r"\left(": ("(", r"\right)"), r"\left|": ("|", r"\right|"), r"\left[": ("[", r"\right]")}
RELATIONS = {"=", "<", ">", r"\le", r"\ge", r"\ne", r"\to", r"\Rightarrow", r"\sim"}
BINARY = {"+", "-", r"\cdot", r"\times", r"\div", r"\pm"}


def parse(latex: str) -> Row:
    tokens = tokenize(latex)
    row, at = _row(tokens, 0, stop=set())
    if at != len(tokens):
        raise ValueError(f"unexpected {tokens[at]!r} in {latex!r}")
    return row


def _group(tokens: list[str], at: int) -> tuple[Row, int]:
    if at < len(tokens) and tokens[at] == "{":
        row, at = _row(tokens, at + 1, stop={"}"})
        return row, at + 1
    # a single token without braces
    row, _ = _row(tokens[at : at + 1], 0, stop=set())
    return row, at + 1


def _row(tokens: list[str], at: int, stop: set[str]) -> tuple[Row, int]:
    row = Row()
    while at < len(tokens) and tokens[at] not in stop:
        token = tokens[at]
        if token in ("^", "_"):
            base = row.items.pop() if row.items else Sym(" ")
            script, at = _group(tokens, at + 1)
            if isinstance(base, Limit) and token == "_":
                base.under = script
                row.items.append(base)
                continue
            if not isinstance(base, Scripts):
                base = Scripts(base)
            if token == "^":
                base.sup = script
            else:
                base.sub = script
            row.items.append(base)
            continue
        at += 1
        if token == "{":
            inner, at = _row(tokens, at, stop={"}"})
            row.items.append(inner)
            at += 1
        elif token == r"\frac":
            top, at = _group(tokens, at)
            bottom, at = _group(tokens, at)
            row.items.append(Frac(top, bottom))
        elif token == r"\sqrt":
            index = None
            if at < len(tokens) and tokens[at] == "[":
                index, at = _row(tokens, at + 1, stop={"]"})
                at += 1
            body, at = _group(tokens, at)
            row.items.append(Root(body, index))
        elif token in FENCES:
            left, closing = FENCES[token]
            body, at = _row(tokens, at, stop={closing})
            right = {"(": ")", "|": "|", "[": "]"}[left]
            row.items.append(Fenced(left, body, right))
            at += 1
        elif token == r"\begin{pmatrix}":
            rows: list[list[Row]] = [[]]
            while at < len(tokens) and tokens[at] != r"\end{pmatrix}":
                cell, at = _row(tokens, at, stop={"&", r"\\", r"\end{pmatrix}"})
                rows[-1].append(cell)
                if at < len(tokens) and tokens[at] == r"\\":
                    rows.append([])
                if at < len(tokens) and tokens[at] in ("&", r"\\"):
                    at += 1
            row.items.append(Matrix([r for r in rows if r]))
            at += 1
        elif token == r"\lim":
            row.items.append(Limit())
        elif token in WORDS:
            row.items.append(Word(WORDS[token]))
        elif token == r"\,":
            row.items.append(Space(0.17))
        else:
            row.items.append(Sym(token))
    return row, at


# -- what gets drawn ---------------------------------------------------------------------


@dataclass
class Glyph:
    """``token`` (or a word) drawn with its baseline-left at (x, y)."""

    token: str
    x: float
    y: float
    size: float
    width: float
    ascent: float
    descent: float
    stretch: float = 1.0  # a bracket or a root drawn taller than it is

    @property
    def box(self) -> tuple[float, float, float, float]:
        top = self.y - self.ascent * self.stretch
        return (self.x, top, self.width, (self.ascent + self.descent) * self.stretch)


@dataclass
class Rule:
    x0: float
    y0: float
    x1: float
    y1: float
    thickness: float


class Metrics(Protocol):
    def measure(self, token: str, size: float) -> tuple[float, float, float]:
        """(advance width, ascent above the baseline, descent below it)."""


@dataclass
class Box:
    width: float
    ascent: float
    descent: float
    parts: list = field(default_factory=list)  # (dx, dy, Glyph | Rule | Box)

    def flatten(self, x: float = 0.0, y: float = 0.0) -> list:
        out = []
        for dx, dy, part in self.parts:
            if isinstance(part, Box):
                out += part.flatten(x + dx, y + dy)
            elif isinstance(part, Glyph):
                out.append(
                    Glyph(
                        part.token,
                        part.x + x + dx,
                        part.y + y + dy,
                        part.size,
                        part.width,
                        part.ascent,
                        part.descent,
                        part.stretch,
                    )
                )
            else:
                out.append(
                    Rule(
                        part.x0 + x + dx,
                        part.y0 + y + dy,
                        part.x1 + x + dx,
                        part.y1 + y + dy,
                        part.thickness,
                    )
                )
        return out


@dataclass
class Style:
    """How loose or tight a layout is; the renderers vary it for variety."""

    script: float = 0.7
    fraction: float = 0.85
    gap: float = 1.0  # multiplies every space
    rule: float = 0.06  # thickness, in em


def place(row: Row, size: float, metrics: Metrics, style: Style | None = None) -> list:
    """The formula laid out at font ``size``: glyphs and rules, baseline at y = 0."""
    box = _layout_row(row, size, metrics, style or Style())
    return box.flatten()


def _glyph(token: str, size: float, metrics: Metrics) -> Box:
    width, ascent, descent = metrics.measure(token, size)
    glyph = Glyph(token, 0.0, 0.0, size, width, ascent, descent)
    return Box(width, ascent, descent, [(0.0, 0.0, glyph)])


def _layout_row(row: Row, size: float, metrics: Metrics, style: Style) -> Box:
    box = Box(0.0, size * 0.5, size * 0.1)
    x = 0.0
    items = row.items
    for index, item in enumerate(items):
        token = item.token if isinstance(item, Sym) else None
        space = 0.0
        if isinstance(item, Word) and item.text == "or":
            space = 0.4  # "x = 2  or  x = 3"
        elif token in RELATIONS:
            space = 0.28
        elif token in BINARY and index > 0 and not _is_operator(items[index - 1]):
            space = 0.22
        pad = space * size * style.gap
        x += pad
        part = _layout(item, size, metrics, style)
        box.parts.append((x, 0.0, part))
        x += part.width + pad
        if token == ",":
            x += 0.17 * size * style.gap
        if isinstance(item, Word) and index + 1 < len(items):
            x += 0.17 * size * style.gap  # sin x, not sinx
        box.ascent = max(box.ascent, part.ascent)
        box.descent = max(box.descent, part.descent)
    box.width = x
    return box


def _is_operator(item) -> bool:
    return isinstance(item, Sym) and (
        item.token in BINARY or item.token in RELATIONS or item.token in "(,["
    )


def _layout(item, size: float, metrics: Metrics, style: Style) -> Box:
    if isinstance(item, Row):
        return _layout_row(item, size, metrics, style)
    if isinstance(item, Sym) and item.token == r"\int":
        return _integral_sign(size, metrics)
    if isinstance(item, Sym):
        return _glyph(item.token, size, metrics)
    if isinstance(item, Word):
        return _glyph(item.text, size, metrics)
    if isinstance(item, Space):
        return Box(item.em * size * style.gap, 0.0, 0.0)
    if isinstance(item, Frac):
        return _frac(item, size, metrics, style)
    if isinstance(item, Root):
        return _root(item, size, metrics, style)
    if isinstance(item, Scripts):
        return _scripts(item, size, metrics, style)
    if isinstance(item, Fenced):
        return _fenced(item, size, metrics, style)
    if isinstance(item, Matrix):
        return _matrix(item, size, metrics, style)
    if isinstance(item, Limit):
        return _limit(item, size, metrics, style)
    raise TypeError(item)


def _integral_sign(size: float, metrics: Metrics) -> Box:
    """An integral sign taller than the letters, centred on the axis."""
    width, ascent, descent = metrics.measure(r"\int", size)
    stretch = max(1.0, size * 1.4 / max(ascent + descent, 1e-6))
    centre = -_axis(size)
    baseline = centre + (ascent - descent) * stretch / 2
    glyph = Glyph(r"\int", 0.0, baseline, size, width, ascent, descent, stretch)
    top, bottom = baseline - ascent * stretch, baseline + descent * stretch
    return Box(width + size * 0.08, -top, bottom, [(0.0, 0.0, glyph)])


def _axis(size: float) -> float:
    """Height of the fraction bar and of the middle of + above the baseline."""
    return size * 0.25


def _frac(item: Frac, size: float, metrics: Metrics, style: Style) -> Box:
    inner = size * style.fraction
    top = _layout_row(item.top, inner, metrics, style)
    bottom = _layout_row(item.bottom, inner, metrics, style)
    width = max(top.width, bottom.width) + size * 0.2
    thickness = size * style.rule
    gap = size * 0.12
    axis = _axis(size)
    top_baseline = -axis - gap - top.descent
    bottom_baseline = -axis + gap + bottom.ascent
    box = Box(width, axis + gap + top.descent + top.ascent, bottom_baseline + bottom.descent)
    box.parts.append(((width - top.width) / 2, top_baseline, top))
    box.parts.append(((width - bottom.width) / 2, bottom_baseline, bottom))
    box.parts.append((0.0, 0.0, Rule(0.0, -axis, width, -axis, thickness)))
    return box


def _root(item: Root, size: float, metrics: Metrics, style: Style) -> Box:
    body = _layout_row(item.body, size, metrics, style)
    height = body.ascent + body.descent + size * 0.15
    sign_w, sign_a, sign_d = metrics.measure(r"\sqrt", size)
    stretch = max(1.0, height / max(sign_a + sign_d, 1e-6))
    sign = Glyph(r"\sqrt", 0.0, body.descent, size, sign_w, sign_a, sign_d, stretch)
    top = -body.ascent - size * 0.15
    index_width = 0.0
    box = Box(0.0, -top + size * style.rule, body.descent)
    if item.index is not None:
        index = _layout_row(item.index, size * style.script * 0.8, metrics, style)
        index_width = max(0.0, index.width - sign_w * 0.4)
        box.parts.append((0.0, top + size * 0.35, index))
    sign.y = body.descent
    box.parts.append((index_width, 0.0, Box(sign_w, sign_a * stretch, 0.0, [(0.0, 0.0, sign)])))
    x0 = index_width + sign_w
    box.parts.append((x0 + size * 0.05, 0.0, body))
    end = x0 + body.width + size * 0.12
    box.parts.append((0.0, 0.0, Rule(x0 - size * 0.02, top, end, top, size * style.rule)))
    box.width = end
    return box


def _scripts(item: Scripts, size: float, metrics: Metrics, style: Style) -> Box:
    base = _layout(item.base, size, metrics, style)
    small = size * style.script
    box = Box(base.width, base.ascent, base.descent, [(0.0, 0.0, base)])
    is_integral = isinstance(item.base, Sym) and item.base.token == r"\int"
    x = base.width + (size * 0.05 if not is_integral else -size * 0.1)
    width = 0.0
    if item.sup is not None:
        sup = _layout_row(item.sup, small, metrics, style)
        raise_by = max(base.ascent - sup.ascent * 0.4, size * 0.45)
        box.parts.append((x, -raise_by, sup))
        box.ascent = max(box.ascent, raise_by + sup.ascent)
        width = max(width, sup.width)
    if item.sub is not None:
        sub = _layout_row(item.sub, small, metrics, style)
        drop = max(base.descent + sub.ascent * 0.3, size * 0.2)
        sub_x = x - (size * 0.15 if is_integral else 0.0)
        box.parts.append((sub_x, drop, sub))
        box.descent = max(box.descent, drop + sub.descent)
        width = max(width, sub.width + (sub_x - x))
    box.width = x + width + size * 0.05
    return box


def _fenced(item: Fenced, size: float, metrics: Metrics, style: Style) -> Box:
    body = _layout_row(item.body, size, metrics, style)
    out = Box(0.0, body.ascent + size * 0.05, body.descent + size * 0.05)
    x = 0.0
    for part in (item.left, None, item.right):
        if part is None:
            out.parts.append((x, 0.0, body))
            x += body.width
            continue
        width, ascent, descent = metrics.measure(part, size)
        need = out.ascent + out.descent
        stretch = max(1.0, need / max(ascent + descent, 1e-6))
        # grown brackets stay centred on the formula's axis
        centre = (-out.ascent + out.descent) / 2
        baseline = centre + (ascent - descent) * stretch / 2
        glyph = Glyph(part, 0.0, baseline, size, width, ascent, descent, stretch)
        out.parts.append((x, 0.0, Box(width, 0.0, 0.0, [(0.0, 0.0, glyph)])))
        x += width
    out.width = x
    return out


def _matrix(item: Matrix, size: float, metrics: Metrics, style: Style) -> Box:
    inner = size * 0.9
    cells = [[_layout_row(cell, inner, metrics, style) for cell in row] for row in item.rows]
    columns = max(len(row) for row in cells)
    widths = [
        max((row[c].width for row in cells if c < len(row)), default=0.0) for c in range(columns)
    ]
    heights = [max(cell.ascent for cell in row) for row in cells]
    depths = [max(cell.descent for cell in row) for row in cells]
    gap_x, gap_y = size * 0.6 * style.gap, size * 0.35
    total = sum(heights) + sum(depths) + gap_y * (len(cells) - 1)
    grid = Box(sum(widths) + gap_x * (columns - 1), 0.0, 0.0)
    y = -total / 2 - _axis(size)
    for r, row in enumerate(cells):
        y += heights[r]
        x = 0.0
        for c, cell in enumerate(row):
            grid.parts.append((x + (widths[c] - cell.width) / 2, y, cell))
            x += widths[c] + gap_x
        y += depths[r] + gap_y
    grid.ascent = total / 2 + _axis(size)
    grid.descent = total / 2 - _axis(size)
    out = Box(0.0, grid.ascent + size * 0.1, grid.descent + size * 0.1)
    return _fenced_around(out, grid, size, metrics)


def _fenced_around(out: Box, middle: Box, size: float, metrics: Metrics) -> Box:
    x = 0.0
    for part in ("(", None, ")"):
        if part is None:
            out.parts.append((x + size * 0.1, 0.0, middle))
            x += middle.width + size * 0.2
            continue
        width, ascent, descent = metrics.measure(part, size)
        stretch = max(1.0, (out.ascent + out.descent) / max(ascent + descent, 1e-6))
        centre = (-out.ascent + out.descent) / 2
        baseline = centre + (ascent - descent) * stretch / 2
        glyph = Glyph(part, 0.0, baseline, size, width, ascent, descent, stretch)
        out.parts.append((x, 0.0, Box(width, 0.0, 0.0, [(0.0, 0.0, glyph)])))
        x += width
    out.width = x
    return out


def _limit(item: Limit, size: float, metrics: Metrics, style: Style) -> Box:
    word = _glyph("lim", size, metrics)
    if item.under is None:
        return word
    under = _layout_row(item.under, size * style.script, metrics, style)
    width = max(word.width, under.width)
    box = Box(width + size * 0.17, word.ascent, word.descent)
    box.parts.append(((width - word.width) / 2, 0.0, word))
    drop = word.descent + under.ascent + size * 0.08
    box.parts.append(((width - under.width) / 2, drop, under))
    box.descent = drop + under.descent
    return box


def bounds(parts: list) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of everything drawn."""
    xs0, ys0, xs1, ys1 = [], [], [], []
    for part in parts:
        if isinstance(part, Glyph):
            x, y, w, h = part.box
            xs0.append(x), ys0.append(y), xs1.append(x + w), ys1.append(y + h)
        else:
            half = part.thickness / 2
            xs0.append(min(part.x0, part.x1)), xs1.append(max(part.x0, part.x1))
            ys0.append(min(part.y0, part.y1) - half), ys1.append(max(part.y0, part.y1) + half)
    return min(xs0), min(ys0), max(xs1), max(ys1)
