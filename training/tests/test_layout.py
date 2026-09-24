"""Where the layout puts things, with plain box metrics instead of a font."""

import random

import numpy as np

from mathrec import formulas, layout, render_printed
from mathrec.image import HEIGHT, MAX_WIDTH


class Boxes:
    """Every symbol is 0.5 em wide, 0.7 em above the baseline and 0.2 below."""

    def measure(self, token, size):
        return 0.5 * size * max(1, len(token) if token.isalpha() else 1), 0.7 * size, 0.2 * size


def _place(latex, size=100.0):
    return layout.place(layout.parse(latex), size, Boxes())


def _glyphs(parts, token):
    return [part for part in parts if isinstance(part, layout.Glyph) and part.token == token]


def test_a_fraction_puts_the_top_over_the_bar_over_the_bottom():
    parts = _place(r"\frac{a}{b}")
    (bar,) = [part for part in parts if isinstance(part, layout.Rule)]
    (a,) = _glyphs(parts, "a")
    (b,) = _glyphs(parts, "b")
    assert a.y + a.descent <= bar.y0 <= b.y - b.ascent
    assert bar.x0 <= a.x and a.x + a.width <= bar.x1


def test_a_power_is_raised_and_smaller():
    parts = _place("x^{2}")
    (x,) = _glyphs(parts, "x")
    (two,) = _glyphs(parts, "2")
    assert two.y < x.y
    assert two.size < x.size
    assert two.x >= x.x + x.width


def test_a_subscript_is_lowered():
    parts = _place("x_{1}")
    (x,) = _glyphs(parts, "x")
    (one,) = _glyphs(parts, "1")
    assert one.y > x.y


def test_a_root_covers_what_is_under_it():
    parts = _place(r"\sqrt{\frac{a}{b}}")
    (sign,) = _glyphs(parts, r"\sqrt")
    top = min(part.y0 for part in parts if isinstance(part, layout.Rule))
    (a,) = _glyphs(parts, "a")
    (b,) = _glyphs(parts, "b")
    assert top <= a.y - a.ascent
    _, sign_top, _, sign_height = sign.box
    assert sign_top + sign_height >= b.y  # the sign reaches down past the denominator


def test_brackets_grow_with_a_fraction():
    parts = _place(r"\left(\frac{a}{b}\right)")
    brackets = _glyphs(parts, "(") + _glyphs(parts, ")")
    assert len(brackets) == 2
    assert all(bracket.stretch > 1 for bracket in brackets)


def test_a_limit_puts_its_approach_underneath():
    parts = _place(r"\lim_{x\to 2}x")
    (lim,) = _glyphs(parts, "lim")
    (two,) = _glyphs(parts, "2")
    assert two.y > lim.y


def test_a_matrix_has_its_rows_one_under_another():
    parts = _place(formulas.sample(random.Random(5), "matrix"))
    ys = sorted(
        {
            round(part.y)
            for part in parts
            if isinstance(part, layout.Glyph) and part.token not in "()"
        }
    )
    assert len(ys) >= 2


def test_every_sampled_formula_can_be_laid_out():
    for latex in formulas.corpus(300, seed=9):
        parts = _place(latex)
        left, top, right, bottom = layout.bounds(parts)
        assert right > left and bottom > top


def test_a_printed_formula_is_96_pixels_tall_with_ink_on_it():
    rng = random.Random(2)
    for latex in formulas.corpus(20, seed=4):
        image = render_printed.render(latex, rng)
        assert image.mode == "L" and image.height == HEIGHT and image.width <= MAX_WIDTH
        pixels = np.asarray(image)
        assert (pixels < 128).sum() > 50  # ink
        assert pixels[0].min() > 128 or pixels[-1].min() > 128  # a margin of paper


def test_printing_is_deterministic_for_a_seed():
    a = np.asarray(render_printed.render(r"\frac{1}{2}x+3=7", random.Random(1)))
    b = np.asarray(render_printed.render(r"\frac{1}{2}x+3=7", random.Random(1)))
    assert (a == b).all()
