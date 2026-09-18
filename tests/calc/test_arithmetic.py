import pytest
import sympy as sp

import mathlint
from mathlint.errors import ParseError, UnsupportedError

from .bank import ARITHMETIC


@pytest.mark.parametrize(("text", "answer"), ARITHMETIC, ids=[text for text, _ in ARITHMETIC])
def test_bank(text, answer):
    result = mathlint.compute(text)
    assert result.kind == "arithmetic"
    assert sp.simplify(result.answer - sp.sympify(answer)) == 0, result.to_text()
    # the steps are worked out, not a single "Calculate" that stands in for them
    assert all(step.text != "Calculate" for step in result.steps), result.to_text()


def steps(text):
    return [(step.text, step.rendered()) for step in mathlint.compute(text).steps]


def test_order_of_operations():
    assert steps("2 + 3*4") == [("Start from", "2 + 3 * 4"), ("Multiply", "2 + 12"), ("Add", "14")]
    assert steps("12 : 3 * 2")[1:] == [("Divide", "4 * 2"), ("Multiply", "8")]


def test_brackets_come_first():
    assert steps("(3 + 5) * 2")[1] == ("Add", "8 * 2")


def test_the_same_kind_of_operation_is_done_together():
    assert steps("2*3 + 4*5")[1] == ("Multiply", "6 + 20")


def test_adding_fractions():
    assert steps("1/2 + 1/3")[1:] == [
        ("Write the fractions over the common denominator 6", "3/6 + 2/6"),
        ("The denominators are the same, so add the numerators", "(3 + 2)/6"),
        ("Add", "5/6"),
    ]


def test_multiplying_and_dividing_fractions():
    assert steps("2/3 * 3/4")[1][0] == "Multiply the numerators, and multiply the denominators"
    assert steps("2/3 * 3/4")[-1] == (
        "Reduce the fraction: divide the numerator and the denominator by 6",
        "1/2",
    )
    assert "reciprocal" in steps("3/4 : 2/5")[1][0]


def test_decimals_become_fractions_only_when_mixed_with_fractions():
    assert steps("0.5 + 1/4")[1] == ("Write the decimals as fractions", "1/2 + 1/4")
    assert steps("2.5 * 1.2")[1] == ("Multiply", "3")


def test_percentages():
    assert steps("20% of 150")[1] == ("A percentage is a number out of 100: 20% = 0.2", "0.2 * 150")


def test_powers_and_roots():
    assert steps("-3^2")[1] == ("Work out the power: 3^2 = 3 * 3", "-9")
    assert steps("2^-3")[1] == ("A negative exponent means one over the power", "1/2^3")
    assert steps("sqrt(72)")[1][0].startswith("Take out the factor 36 = 6^2")
    assert steps("sqrt(16)")[1][0] == "sqrt(16) = 4, because 4^2 = 16"


def test_answers_are_exact_with_a_decimal():
    result = mathlint.compute("1/2 + 1/3")
    assert result.answer_plain == "5/6"
    assert result.decimal == "0.8333333333"
    assert mathlint.compute("2 + 3").decimal is None


def test_the_answer_is_verified():
    result = mathlint.compute("sqrt(8) + sqrt(2)")
    assert result.answer == 3 * sp.sqrt(2)
    assert result.answer_latex == r"3 \sqrt{2}"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("1/0", "divides by zero"),
        ("4 : 0", "divides by zero"),
        ("0^0", "no agreed value"),
        ("3,5", "point"),
        ("2^100000", "too big"),
        ("2 + 3 -", "stops too early"),
        ("", "nothing to calculate"),
    ],
)
def test_mistakes_in_the_input_are_explained(text, message):
    with pytest.raises(ParseError, match=message):
        mathlint.compute(text)


def test_an_equation_is_not_a_calculation():
    with pytest.raises(ParseError, match="equation"):
        mathlint.compute("2 + 3 = 5")


def test_letters_are_not_arithmetic_yet():
    with pytest.raises(UnsupportedError):
        mathlint.compute("2x + 1")


def test_to_dict_matches_the_solve_tab():
    data = mathlint.compute("1/2 + 1/3").to_dict()
    assert data["kind_label"] == "Arithmetic"
    assert data["answer_latex"] == r"\frac{5}{6}"
    assert data["decimal"] == "0.8333333333"
    assert data["methods"] == [{"id": "calculate", "label": "Calculate"}]
    assert data["steps"][1]["math_latex"] == r"\frac{3}{6} + \frac{2}{6}"
