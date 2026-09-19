"""The Solve tab's examples, written the way its math editor writes them."""

import json
from pathlib import Path

import pytest

import mathlint

EXAMPLES = json.loads(
    (Path(__file__).resolve().parent.parent / "web" / "solve-examples.json").read_text(
        encoding="utf-8"
    )
)
EXPECTED = {
    "Quadratic": ["2", "3"],
    "Brackets": ["8"],
    "Fractions": ["1"],
    "Cubic": ["1", "2", "3"],
    "Unknown in a denominator": ["3"],
    "Square root": ["5"],
    "Absolute value": ["-3", "5"],
    "Exponential": ["1"],
    "Logarithms": ["3"],
    "System of two equations": [{"x": "2", "y": "5"}],
    "System of three equations": [{"x": "1", "y": "2", "z": "3"}],
    "Formula (solve for a letter)": None,
    "Arithmetic with fractions": ["10"],
    "Expand brackets": ["6*x^2 + 5*x - 4"],
    "Factor": ["(x + 1)*(2*x + 3)"],
    "Simplify a fraction": ["(x - 2)/(x - 1)"],
    "Derivative": ["x*(x*cos(x) + 2*sin(x))"],
}


def test_every_example_has_an_expectation():
    assert {example["name"] for example in EXAMPLES} == set(EXPECTED)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda example: example["name"])
def test_solve_example(example):
    # the page sends the lines of the Solve sheet joined by new lines
    text = "\n".join(example["lines"])
    expected = EXPECTED[example["name"]]
    if expected is None:
        # no x: the page asks which letter, and every letter must then solve
        for letter in "atuv":
            assert mathlint.solve(text, variable=letter).answers
        return
    assert mathlint.solve(text).to_dict()["answers"] == expected
