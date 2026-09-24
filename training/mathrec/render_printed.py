"""Formulas typeset in open fonts, the way a textbook or a worksheet prints them."""

from __future__ import annotations

import random
from functools import cache

from PIL import Image, ImageDraw, ImageFont

from . import layout
from .fonts import MATH_FONTS, TEXT_FONTS, Font
from .image import finish

# what each token looks like in a font (letters are handled below)
SYMBOLS = {
    "-": "−",
    r"\cdot": "⋅",
    r"\times": "×",
    r"\div": "÷",
    r"\pm": "±",
    r"\le": "≤",
    r"\ge": "≥",
    r"\ne": "≠",
    r"\to": "→",
    r"\infty": "∞",
    r"\pi": "\U0001d70b",
    r"\theta": "\U0001d703",
    r"\alpha": "\U0001d6fc",
    r"\beta": "\U0001d6fd",
    r"\lambda": "\U0001d706",
    r"\mu": "\U0001d707",
    r"\varphi": "\U0001d711",
    r"\Delta": "Δ",
    r"\int": "∫",
    r"\prime": "′",
    "'": "′",
    r"\sim": "∼",
    r"\Rightarrow": "⇒",
    r"\sqrt": "√",
}
# plain-font stand-ins, for a worksheet typed without math italics
PLAIN = {
    r"\pi": "π",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\varphi": "φ",
}
# symbols a text font draws well; everything else comes from the math font
TEXT_SAFE = set("0123456789+=<>()[],;.!|") | {"-", r"\times", r"\div", r"\pm", r"\cdot"}


def _italic(letter: str) -> str:
    """The Unicode mathematical italic form of a Latin letter."""
    if letter == "h":
        return "ℎ"  # the one italic letter outside the block
    base = 0x1D434 if letter.isupper() else 0x1D44E
    offset = ord(letter) - (ord("A") if letter.isupper() else ord("a"))
    return chr(base + offset)


@cache
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


class PrintedMetrics:
    """Measures and draws tokens with a math font and, maybe, a text font."""

    def __init__(self, math: Font, text: Font | None, italic: bool) -> None:
        self.math = str(math.path())
        self.text = str(text.path()) if text else None
        self.italic = italic

    def choose(self, token: str, size: float) -> tuple[ImageFont.FreeTypeFont, str]:
        size = max(4, round(size))
        if len(token) == 1 and token.isalpha() and token.isascii():
            if self.italic and self.text is None:
                return _font(self.math, size), _italic(token)
            return _font(self.text or self.math, size), token
        if len(token) > 1 and token.isalpha():  # sin, ln, lim, or: always upright
            return _font(self.text or self.math, size), token
        if self.text and token in TEXT_SAFE:
            return _font(self.text, size), SYMBOLS.get(token, token)
        if self.text and token in PLAIN:
            return _font(self.math, size), PLAIN[token]
        return _font(self.math, size), SYMBOLS.get(token, token)

    def measure(self, token: str, size: float) -> tuple[float, float, float]:
        font, text = self.choose(token, size)
        x0, y0, x1, y1 = font.getbbox(text, anchor="ls")
        advance = max(font.getlength(text), x1)
        return advance, max(-y0, 1.0), max(y1, 0.0)

    def draw(self, canvas: Image.Image, glyph: layout.Glyph, ink: int) -> None:
        font, text = self.choose(glyph.token, glyph.size)
        if glyph.stretch <= 1.01:
            ImageDraw.Draw(canvas).text((glyph.x, glyph.y), text, font=font, fill=ink, anchor="ls")
            return
        # a grown bracket or root: draw it at its size, then stretch it tall
        x0, y0, x1, y1 = font.getbbox(text, anchor="ls")
        piece = Image.new("L", (max(1, x1 - x0 + 2), max(1, y1 - y0 + 2)), 255)
        ImageDraw.Draw(piece).text((1 - x0, 1 - y0), text, font=font, fill=ink, anchor="ls")
        tall = piece.resize((piece.width, max(1, round(piece.height * glyph.stretch))))
        top = glyph.y + y0 * glyph.stretch
        canvas.paste(tall, (round(glyph.x + x0), round(top)), mask=_mask(tall))


def _mask(piece: Image.Image) -> Image.Image:
    return piece.point(lambda value: 255 - value)


def draw(parts: list, metrics: PrintedMetrics, rng: random.Random, ink: int = 0) -> Image.Image:
    left, top, right, bottom = layout.bounds(parts)
    margin = 8
    canvas = Image.new("L", (int(right - left) + 2 * margin, int(bottom - top) + 2 * margin), 255)
    shift_x, shift_y = margin - left, margin - top
    pen = ImageDraw.Draw(canvas)
    for part in parts:
        if isinstance(part, layout.Glyph):
            moved = layout.Glyph(
                part.token,
                part.x + shift_x,
                part.y + shift_y,
                part.size,
                part.width,
                part.ascent,
                part.descent,
                part.stretch,
            )
            metrics.draw(canvas, moved, ink)
        else:
            half = max(1.0, part.thickness) / 2
            pen.rectangle(
                (
                    part.x0 + shift_x,
                    part.y0 + shift_y - half,
                    part.x1 + shift_x,
                    part.y1 + shift_y + half,
                ),
                fill=ink,
            )
    return canvas


def render(latex: str, rng: random.Random) -> Image.Image:
    """``latex`` typeset in a random open font, as the recognizer sees it."""
    math = rng.choice(MATH_FONTS)
    text = rng.choice(TEXT_FONTS) if rng.random() < 0.3 else None
    metrics = PrintedMetrics(math, text, italic=rng.random() < 0.85)
    style = layout.Style(
        script=rng.uniform(0.62, 0.78),
        fraction=rng.uniform(0.75, 1.0),
        gap=rng.uniform(0.7, 1.4),
        rule=rng.uniform(0.04, 0.08),
    )
    parts = layout.place(layout.parse(latex), rng.uniform(40, 64), metrics, style)
    return finish(draw(parts, metrics, rng, ink=rng.randint(0, 60)), rng)
