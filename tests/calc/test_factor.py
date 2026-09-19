import pytest
import sympy as sp

import mathlint

x, y, a, b = sp.symbols("x y a b")

FACTORED = [
    ("6x^2 + 9x", 3 * x * (2 * x + 3)),
    ("x^2 - 9", (x - 3) * (x + 3)),
    ("x^2 + 5x + 6", (x + 2) * (x + 3)),
    ("2x^2 + 5x + 3", (x + 1) * (2 * x + 3)),
    ("6x^2 - x - 2", (2 * x + 1) * (3 * x - 2)),
    ("2x^2 - 5x + 2", (x - 2) * (2 * x - 1)),
    ("x^2 - 6x + 9", (x - 3) ** 2),
    ("4x^2 - 12x + 9", (2 * x - 3) ** 2),
    ("x^4 - 16", (x - 2) * (x + 2) * (x**2 + 4)),
    ("x^3 - 8", (x - 2) * (x**2 + 2 * x + 4)),
    ("x^3 + 27", (x + 3) * (x**2 - 3 * x + 9)),
    ("x^3 + 3x^2 + 2x + 6", (x + 3) * (x**2 + 2)),
    ("x^3 - x^2 - x + 1", (x - 1) ** 2 * (x + 1)),
    ("ax + ay + bx + by", (a + b) * (x + y)),
    ("x^3 - 6x^2 + 11x - 6", (x - 1) * (x - 2) * (x - 3)),
    ("2x^3 - 3x^2 - 11x + 6", (2 * x - 1) * (x - 3) * (x + 2)),
    ("x^4 - 5x^2 + 4", (x - 2) * (x - 1) * (x + 1) * (x + 2)),
    ("x^2 + 5xy + 6y^2", (x + 2 * y) * (x + 3 * y)),
    ("-x^2 + 4", -(x - 2) * (x + 2)),
    ("2x^2 - 8", 2 * (x - 2) * (x + 2)),
    ("x^2/2 - 2", (x - 2) * (x + 2) / 2),
    ("x^6 - 1", (x - 1) * (x + 1) * (x**2 - x + 1) * (x**2 + x + 1)),
    ("3x^3 - 12x", 3 * x * (x - 2) * (x + 2)),
]


@pytest.mark.parametrize(("text", "expected"), FACTORED, ids=[text for text, _ in FACTORED])
def test_factor_bank(text, expected):
    result = mathlint.compute(text, method="factor")
    # the same factors, not only the same value
    assert sp.factor_list(result.answer) == sp.factor_list(expected), result.to_text()
    assert result.answer == expected or sp.expand(result.answer - expected) == 0
    assert all(step.text not in ("Factor", "Factor (computer algebra)") for step in result.steps), (
        result.to_text()
    )


def texts(text):
    return [step.text for step in mathlint.compute(text, method="factor").steps]


def test_an_expanded_polynomial_is_factored_by_default():
    assert mathlint.compute("x^2 - 9").method == "factor"
    assert mathlint.compute("(x+1)^2 - 4").methods == ["expand", "factor", "simplify"]


def test_only_a_whole_number_coming_out_counts_as_factoring():
    assert mathlint.compute("6x + 9").method == "factor"
    assert "factor" not in mathlint.compute("2x + 1/2").methods
    assert "factor" not in mathlint.compute("-x - 1").methods


def test_common_factor_first():
    assert texts("3x^3 - 12x")[1] == "Take out the common factor 3*x"


def test_two_numbers():
    assert texts("x^2 + 5x + 6")[1] == ("Find two numbers that multiply to 6 and add to 5: 2 and 3")


def test_splitting_the_middle_term():
    steps = mathlint.compute("2x^2 + 5x + 3").steps
    assert [step.rendered() for step in steps[1:]] == [
        "2*x^2 + 2*x + 3*x + 3",
        "2*x*(x + 1) + 3*(x + 1)",
        "(x + 1)*(2*x + 3)",
    ]


def test_grouping_with_a_minus_sign():
    steps = mathlint.compute("x^3 - x^2 - x + 1").steps
    assert steps[1].rendered() == "(x^3 - x^2) + (1 - x)"
    assert steps[2].rendered() == "x^2*(x - 1) - (x - 1)"


def test_factors_are_factored_again():
    assert texts("x^4 - 16")[1:] == [
        "Difference of squares: a^2 - b^2 = (a - b)(a + b), with a = x^2 and b = 4",
        "Difference of squares: a^2 - b^2 = (a - b)(a + b), with a = x and b = 2",
    ]


def test_the_factor_theorem():
    assert texts("x^3 - 6x^2 + 11x - 6")[1].startswith("x = 1 makes it 0, so x - 1 is a factor")


def test_brackets_are_multiplied_out_before_factoring():
    steps = mathlint.compute("(x+1)^2 - 4", method="factor").steps
    assert steps[1].text == "Multiply out first"
    assert steps[-1].rendered() == "(x - 1)*(x + 3)"
