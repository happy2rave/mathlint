"""Handwritten symbols and formulas written with them.

These need the downloaded datasets (``training/data``); without them they skip.
"""

import random

import numpy as np
import pytest

from mathrec import formulas, render_hand, symbols
from mathrec.download import DOWNLOADS
from mathrec.image import HEIGHT, MAX_WIDTH

pytestmark = pytest.mark.skipif(
    not (symbols.CACHE / "detexify.pkl").exists() and not (DOWNLOADS / "detexify.sql").exists(),
    reason="the handwriting datasets are not downloaded",
)


def test_every_symbol_has_at_least_20_handwritten_samples():
    bank = symbols.bank()
    few = {token: len(bank.get(token, [])) for token in symbols.symbol_tokens()}
    assert {token: count for token, count in few.items() if count < 20} == {}


def test_most_symbols_have_samples_written_by_people_not_only_fonts():
    bank = symbols.bank()
    only_fonts = [
        token
        for token in symbols.symbol_tokens()
        if all(sample.kind == "font" for sample in bank.get(token, []))
    ]
    # the punctuation neither dataset has (= ( ) , ; . ! '), and HASYv2 has no t
    assert set(only_fonts) <= set("=(),;.!'t")


def test_a_writer_puts_descenders_below_the_line_and_operators_on_the_axis():
    metrics = render_hand.HandMetrics(random.Random(1), bearing=0.1)
    _, ascent, descent = metrics.measure("p", 100)
    assert descent > 10
    _, ascent, descent = metrics.measure("+", 100)
    assert ascent > 40 and descent <= 0  # sits on the axis, not below the line
    _, _, descent = metrics.measure("x", 100)
    assert descent == 0


def test_a_writer_writes_a_symbol_the_same_way_every_time():
    metrics = render_hand.HandMetrics(random.Random(1), bearing=0.1)
    assert metrics.measure("x", 50) == metrics.measure("x", 50)
    assert metrics.shape("x") is metrics.shape("x")


def test_a_handwritten_formula_is_96_pixels_tall_with_ink_on_it():
    rng = random.Random(2)
    for latex in formulas.corpus(40, seed=4):
        image = render_hand.render(latex, rng)
        assert image.mode == "L" and image.height == HEIGHT and image.width <= MAX_WIDTH
        assert (np.asarray(image) < 128).sum() > 50


def test_handwriting_is_deterministic_for_a_seed():
    a = np.asarray(render_hand.render(r"\sqrt{2x+1}=\frac{3}{4}", random.Random(1)))
    b = np.asarray(render_hand.render(r"\sqrt{2x+1}=\frac{3}{4}", random.Random(1)))
    assert (a == b).all()
