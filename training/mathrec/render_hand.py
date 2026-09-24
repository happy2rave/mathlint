"""Formulas written by hand, from real handwritten symbols.

Each symbol is a sample from ``symbols.bank()``, placed by ``layout.place``
where a person would put it: letters on the baseline, descenders below it,
operators on the axis, brackets and roots grown around what they hold. One
image is one writer, with one pen, one ink, one slant and one way of writing
each symbol, the way a person writes every x in a line alike.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from functools import cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import layout
from .image import finish
from .symbols import Sample, bank
from .vocab import DIGITS, UPPER

AXIS = 0.25  # the middle of + above the baseline, in em, as in the layout


def _on_axis(height: float, narrow: float, wide: float) -> tuple[float, float, float, float]:
    return AXIS + height / 2, AXIS - height / 2, narrow, wide


# where a symbol sits, in em: (top above the baseline, bottom above it, narrowest, widest)
TALL = (0.7, 0.0, 0.12, 0.8)
SMALL = (0.45, 0.0, 0.14, 0.7)
DESCENDING = (0.45, -0.22, 0.2, 0.7)
BRACKET = (0.78, -0.22, 0.12, 0.35)
PLACES = {
    **{char: TALL for char in [*DIGITS, *UPPER, *"bdfhklt!"]},
    **{char: SMALL for char in "acemnorsuvwxz"},
    **{char: DESCENDING for char in "gpqy"},
    "i": (0.66, 0.0, 0.08, 0.35),
    "j": (0.66, -0.22, 0.12, 0.45),
    r"\theta": TALL,
    r"\lambda": TALL,
    r"\Delta": TALL,
    r"\beta": (0.72, -0.22, 0.2, 0.6),
    r"\alpha": SMALL,
    r"\pi": SMALL,
    r"\mu": DESCENDING,
    r"\varphi": (0.5, -0.22, 0.25, 0.7),
    r"\infty": (0.4, 0.05, 0.5, 0.9),
    "+": _on_axis(0.5, 0.3, 0.55),
    "-": _on_axis(0.4, 0.3, 0.55),
    r"\times": _on_axis(0.42, 0.3, 0.5),
    r"\div": _on_axis(0.5, 0.3, 0.55),
    r"\pm": _on_axis(0.55, 0.3, 0.55),
    r"\cdot": _on_axis(0.1, 0.05, 0.12),
    "=": _on_axis(0.4, 0.35, 0.6),
    r"\ne": _on_axis(0.5, 0.35, 0.6),
    "<": _on_axis(0.5, 0.3, 0.5),
    ">": _on_axis(0.5, 0.3, 0.5),
    r"\le": _on_axis(0.6, 0.3, 0.5),
    r"\ge": _on_axis(0.6, 0.3, 0.5),
    r"\to": _on_axis(0.4, 0.5, 0.8),
    r"\Rightarrow": _on_axis(0.45, 0.5, 0.8),
    r"\sim": _on_axis(0.25, 0.35, 0.6),
    ".": (0.1, 0.0, 0.05, 0.12),
    ",": (0.08, -0.16, 0.05, 0.15),
    ";": (0.42, -0.16, 0.06, 0.2),
    "'": (0.8, 0.48, 0.05, 0.2),
    r"\prime": (0.8, 0.48, 0.05, 0.2),
    "(": BRACKET,
    ")": BRACKET,
    "[": BRACKET,
    "]": BRACKET,
    "|": (0.78, -0.22, 0.05, 0.3),
    r"\int": (0.8, -0.2, 0.2, 0.45),
    r"\sqrt": (0.8, -0.2, 0.45, 0.7),
    " ": (0.45, 0.0, 0.3, 0.3),
}
# how often each kind of sample is picked, when a symbol has it
WEIGHTS = {"strokes": 0.45, "bitmap": 0.25, "font": 0.3}
# the widest a sample may be: a root written with its bar would squash into the
# sign's box, and the layout draws the bar itself
WIDEST = {r"\sqrt": 1.3}


@dataclass
class Shape:
    """One way of writing a symbol, ready to draw into any box."""

    aspect: float  # width over height
    strokes: list | None = None  # arrays of (u, v) in the unit square
    bitmap: np.ndarray | None = None  # ink is dark, cropped to the ink


@cache
def _by_kind() -> dict[str, dict[str, list[Sample]]]:
    out: dict[str, dict[str, list[Sample]]] = {}
    for token, samples in bank().items():
        kinds: dict[str, list[Sample]] = defaultdict(list)
        for sample in samples:
            kinds[sample.kind].append(sample)
        out[token] = dict(kinds)
    return out


@cache
def _font_glyph(path: str, char: str) -> np.ndarray | None:
    font = ImageFont.truetype(path, 96)
    canvas = Image.new("L", (240, 240), 255)
    ImageDraw.Draw(canvas).text((60, 170), char, font=font, fill=0, anchor="ls")
    return _cropped(np.asarray(canvas))


def _cropped(pixels: np.ndarray, threshold: int = 160) -> np.ndarray | None:
    ys, xs = np.nonzero(pixels < threshold)
    if len(xs) == 0:
        return None
    return pixels[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def _shape(sample: Sample, rng: random.Random) -> Shape | None:
    """``sample`` turned a little, sheared and squeezed, as this writer would write it."""
    angle = math.radians(rng.gauss(0, 4))
    shear = rng.gauss(0, 0.08)
    squeeze = rng.uniform(0.85, 1.15)
    if sample.kind == "strokes":
        cos, sin = math.cos(angle), math.sin(angle)
        matrix = np.array([[squeeze, shear], [0.0, 1.0]]) @ np.array([[cos, -sin], [sin, cos]])
        strokes = [stroke.astype(np.float32) @ matrix.T for stroke in sample.strokes]
        every = np.concatenate(strokes)
        low, span = every.min(axis=0), np.ptp(every, axis=0)
        height = max(float(span[1]), 1e-3)
        scale = np.where(span > 1e-3, span, 1.0)
        unit = [(stroke - low) / scale for stroke in strokes]
        # a stroke with no width (a | or a -) sits in the middle of its box
        unit = [np.where(span > 1e-3, points, 0.5) for points in unit]
        return Shape(aspect=float(span[0]) / height, strokes=unit)
    if sample.kind == "bitmap":
        pixels = sample.bitmap
    else:
        pixels = _font_glyph(sample.font, sample.char)
        if pixels is None:
            return None
    image = Image.fromarray(pixels)
    image = image.resize((max(1, round(image.width * squeeze)), image.height))
    image = image.rotate(
        math.degrees(angle), expand=True, fillcolor=255, resample=Image.Resampling.BICUBIC
    )
    pixels = _cropped(np.asarray(image))
    if pixels is None:
        return None
    return Shape(aspect=pixels.shape[1] / pixels.shape[0], bitmap=pixels)


def _choose(token: str, rng: random.Random) -> Shape | None:
    kinds = _by_kind().get(token)
    if not kinds:
        return None
    names = sorted(kinds)
    widest = WIDEST.get(token, math.inf)
    shape = None
    for _ in range(20):
        kind = rng.choices(names, weights=[WEIGHTS[name] for name in names])[0]
        shape = _shape(rng.choice(kinds[kind]), rng) or shape
        if shape is not None and shape.aspect <= widest:
            return shape
    return shape


class HandMetrics:
    """Sizes and draws symbols the way one writer writes them."""

    def __init__(self, rng: random.Random, bearing: float) -> None:
        self.rng = rng
        self.bearing = bearing  # space beside each symbol, in em
        self.shapes: dict[str, Shape | None] = {}

    def shape(self, token: str) -> Shape | None:
        if token not in self.shapes:
            self.shapes[token] = _choose(token, self.rng) if token != " " else None
        return self.shapes[token]

    def letter(self, token: str, size: float, bearing: float) -> tuple[float, float, float, float]:
        """(advance, ink width, top, bottom) of one symbol, in pixels above the baseline."""
        top, bottom, narrow, wide = PLACES.get(token, TALL)
        shape = self.shape(token)
        aspect = shape.aspect if shape else 0.0
        ink = min(max(aspect * (top - bottom), narrow), wide) * size
        return ink + bearing * size, ink, top * size, bottom * size

    def measure(self, token: str, size: float) -> tuple[float, float, float]:
        if len(token) > 1 and token.isalpha():  # a word: its letters, close together
            letters = [self.letter(char, size, self.bearing * 0.5) for char in token]
            return (
                sum(letter[0] for letter in letters) + self.bearing * size * 0.5,
                max(letter[2] for letter in letters),
                max(-letter[3] for letter in letters),
            )
        advance, _, top, bottom = self.letter(token, size, self.bearing)
        return advance, top, -bottom


class Pen:
    """Puts shapes and rules on the page, with this writer's pen and ink."""

    def __init__(self, canvas: Image.Image, width: float, ink: int, rng: random.Random) -> None:
        self.canvas = canvas
        self.draw = ImageDraw.Draw(canvas)
        self.width = width
        self.ink = ink
        self.rng = rng

    def shape(self, shape: Shape, box: tuple, size: float, fill: bool) -> None:
        x, y, width, height = box
        if not fill:  # keep the shape's proportions, centred in the box
            drawn_height = min(height, width / shape.aspect) if shape.aspect > 0 else height
            drawn_width = drawn_height * shape.aspect
            x += (width - drawn_width) / 2
            y += (height - drawn_height) / 2
            width, height = drawn_width, drawn_height
        grow = self.rng.uniform(0.92, 1.06)
        x += self.rng.gauss(0, 0.02 * size) + width * (1 - grow) / 2
        y += self.rng.gauss(0, 0.025 * size) + height * (1 - grow) / 2
        width, height = max(width * grow, 1.0), max(height * grow, 1.0)
        pen = max(1, round(min(self.width, size * 0.1)))
        if shape.strokes is not None:
            for stroke in shape.strokes:
                points = [(x + u * width, y + v * height) for u, v in stroke.tolist()]
                if len(points) > 1:
                    self.draw.line(points, fill=self.ink, width=pen, joint="curve")
                for px, py in (points[0], points[-1]):  # round ends
                    r = pen / 2
                    self.draw.ellipse((px - r, py - r, px + r, py + r), fill=self.ink)
            return
        piece = Image.fromarray(shape.bitmap).resize(
            (max(1, round(width)), max(1, round(height))), Image.Resampling.BILINEAR
        )
        mask = piece.point(lambda value: max(0, min(255, (215 - value) * 2)))
        left, top = round(x), round(y)
        self.canvas.paste(self.ink, (left, top, left + piece.width, top + piece.height), mask)

    def rule(self, rule: layout.Rule, size: float) -> None:
        """A bar drawn by hand: a little longer or shorter, a little tilted, not quite straight."""
        x0 = rule.x0 + self.rng.gauss(0, 0.04 * size)
        x1 = rule.x1 + self.rng.gauss(0, 0.04 * size)
        tilt = self.rng.gauss(0, 0.02)
        points = []
        for step in range(7):
            at = step / 6
            wobble = self.rng.gauss(0, 0.01 * size)
            points.append((x0 + (x1 - x0) * at, rule.y0 + (x1 - x0) * (at - 0.5) * tilt + wobble))
        self.draw.line(points, fill=self.ink, width=max(1, round(self.width)), joint="curve")


def _draw_glyph(pen: Pen, metrics: HandMetrics, glyph: layout.Glyph) -> None:
    size = glyph.size
    if len(glyph.token) > 1 and glyph.token.isalpha():
        x = glyph.x
        for char in glyph.token:
            advance, ink, top, bottom = metrics.letter(char, size, metrics.bearing * 0.5)
            shape = metrics.shape(char)
            if shape is not None:
                pen.shape(
                    shape, (x + (advance - ink) / 2, glyph.y - top, ink, top - bottom), size, False
                )
            x += advance
        return
    shape = metrics.shape(glyph.token)
    if shape is None:
        return
    advance, ink, top, bottom = metrics.letter(glyph.token, size, metrics.bearing)
    left = glyph.x + (advance - ink) / 2
    if glyph.stretch > 1.01 or glyph.token == r"\sqrt":  # grown to what it holds: fill it
        _, box_top, _, height = glyph.box
        pen.shape(shape, (left, box_top, ink, height), size, True)
    else:
        pen.shape(shape, (left, glyph.y - top, ink, top - bottom), size, False)


def draw(parts: list, metrics: HandMetrics, rng: random.Random, pen_width: float, ink: int):
    left, top, right, bottom = layout.bounds(parts)
    margin = 16
    canvas = Image.new("L", (int(right - left) + 2 * margin, int(bottom - top) + 2 * margin), 255)
    shift_x, shift_y = margin - left, margin - top
    pen = Pen(canvas, pen_width, ink, rng)
    for part in parts:
        if isinstance(part, layout.Glyph):
            part = layout.Glyph(
                part.token,
                part.x + shift_x,
                part.y + shift_y,
                part.size,
                part.width,
                part.ascent,
                part.descent,
                part.stretch,
            )
            _draw_glyph(pen, metrics, part)
        else:
            moved = layout.Rule(
                part.x0 + shift_x,
                part.y0 + shift_y,
                part.x1 + shift_x,
                part.y1 + shift_y,
                part.thickness,
            )
            pen.rule(moved, parts_size(parts))
    return canvas


def parts_size(parts: list) -> float:
    """The largest symbol size: the formula's own size."""
    return max((part.size for part in parts if isinstance(part, layout.Glyph)), default=48.0)


def _slanted(image: Image.Image, slant: float, tilt: float) -> Image.Image:
    """The whole line leaning like handwriting, and not quite level."""
    pad = int(abs(slant) * image.height) + 2
    width = image.width + 2 * pad
    data = (1, slant, -pad - slant * image.height / 2, 0, 1, 0)
    leaning = image.transform((width, image.height), Image.Transform.AFFINE, data, fillcolor=255)
    return leaning.rotate(tilt, expand=True, fillcolor=255, resample=Image.Resampling.BICUBIC)


def render(latex: str, rng: random.Random) -> Image.Image:
    """``latex`` written by a random hand, as the recognizer sees it."""
    size = rng.uniform(40, 64)
    metrics = HandMetrics(rng, bearing=rng.uniform(0.04, 0.14))
    style = layout.Style(
        script=rng.uniform(0.6, 0.8),
        fraction=rng.uniform(0.75, 1.0),
        gap=rng.uniform(0.6, 1.5),
        rule=0.06,
    )
    parts = layout.place(layout.parse(latex), size, metrics, style)
    pen_width = size * rng.uniform(0.04, 0.085)
    ink = rng.randint(0, 90)
    canvas = draw(parts, metrics, rng, pen_width, ink)
    canvas = _slanted(canvas, rng.gauss(0, 0.12), rng.gauss(0, 1.2))
    return finish(canvas, rng)
