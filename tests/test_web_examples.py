"""The examples on the web page are written the way its math editor writes them.

If mathlint ever stops reading that notation, the page breaks quietly — so the
examples are checked here, with the verdict each one is meant to produce.
"""

import json
from pathlib import Path

import pytest

import mathlint

EXAMPLES = json.loads(
    (Path(__file__).resolve().parent.parent / "web" / "examples.json").read_text(encoding="utf-8")
)
EXPECTED = {
    "Derivative with a sign slip": 4,
    "Integration by parts": None,
    "Quadratic equation": None,
    "Squaring invents a root": 3,
    "Dividing loses a root": 2,
    "Row reduction": None,
    "System, with a slip": 3,
}


def test_every_example_has_an_expectation():
    assert {example["name"] for example in EXAMPLES} == set(EXPECTED)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda example: example["name"])
def test_web_example(example):
    report = mathlint.check("\n".join(example["lines"]))
    expected_line = EXPECTED[example["name"]]
    if expected_line is None:
        assert report.ok, report.to_text()
    else:
        assert report.first_error is not None, report.to_text()
        assert report.first_error.line == expected_line
