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
}


def test_every_example_has_an_expectation():
    assert {example["name"] for example in EXAMPLES} == set(EXPECTED)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda example: example["name"])
def test_solve_example(example):
    # the page sends the lines of the Solve sheet joined by new lines
    solution = mathlint.solve("\n".join(example["lines"]))
    assert solution.to_dict()["answers"] == EXPECTED[example["name"]]
