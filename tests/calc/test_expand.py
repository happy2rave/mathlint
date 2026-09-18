import pytest
import sympy as sp

import mathlint

x, y, a, b, c = sp.symbols("x y a b c")

EXPANDED = [
    ("(x+2)^2", x**2 + 4 * x + 4),
    ("(x-3)^2", x**2 - 6 * x + 9),
    ("(x+3)(x-3)", x**2 - 9),
    ("3(x-1) + 2x", 5 * x - 3),
    ("(x+1)(x+2)", x**2 + 3 * x + 2),
    ("2x(x-5)", 2 * x**2 - 10 * x),
    ("-(x-3)", 3 - x),
    ("(x+1)^3", x**3 + 3 * x**2 + 3 * x + 1),
    ("(2x-1)(3x+4)", 6 * x**2 + 5 * x - 4),
    ("(x+1)^4", sp.expand((x + 1) ** 4)),
    ("(a+b+c)^2", sp.expand((a + b + c) ** 2)),
    ("(x+1)(x+2)(x+3)", x**3 + 6 * x**2 + 11 * x + 6),
    ("2(x+3)^2 - 4x", 2 * x**2 + 8 * x + 18),
    ("x(x+1) - x^2", x),
    ("(x+y)(x-y)", x**2 - y**2),
    (r"\left(x+2\right)^{2}", x**2 + 4 * x + 4),
    ("(x+1)/2", x / 2 + sp.Rational(1, 2)),
]


@pytest.mark.parametrize(("text", "expected"), EXPANDED, ids=[text for text, _ in EXPANDED])
def test_expand_bank(text, expected):
    result = mathlint.compute(text, method="expand")
    assert result.kind == "expression"
    assert sp.expand(result.answer - expected) == 0, result.to_text()
    assert all(step.text != "Expand" for step in result.steps), result.to_text()


def texts(text):
    return [step.text for step in mathlint.compute(text, method="expand").steps]


def test_brackets_are_expanded_by_default():
    assert mathlint.compute("(x+2)^2").method == "expand"


def test_special_products_are_named():
    assert texts("(x+2)^2")[1] == "Use (a + b)^2 = a^2 + 2ab + b^2"
    assert texts("(x-3)^2")[1] == "Use (a - b)^2 = a^2 - 2ab + b^2"
    assert texts("(x+3)(x-3)")[1] == "Use (a + b)(a - b) = a^2 - b^2"


def test_two_brackets_then_like_terms():
    steps = mathlint.compute("(x+1)(x+2)").steps
    assert steps[1].text == "Multiply every term in the first bracket by every term in the second"
    assert steps[1].rendered() == "x^2 + x + 2*x + 2"
    assert steps[2].text == "Collect like terms"


def test_a_number_in_front_waits_until_the_bracket_is_worked_out():
    steps = mathlint.compute("2(x+1)(x+2)").steps
    assert [step.rendered() for step in steps[1:]] == [
        "2*(x^2 + x + 2*x + 2)",
        "2*(x^2 + 3*x + 2)",
        "2*x^2 + 6*x + 4",
    ]


def test_a_minus_sign_in_front():
    assert texts("-(x-3)")[1].startswith("A minus sign in front of a bracket")


def test_the_rules_used_while_reading_are_named():
    steps = mathlint.compute("x^3 x^5 + 2x + 3x(x+1)").steps
    assert steps[0].rendered() == "x^3*x^5 + 3*x*(x + 1) + 2*x"
    assert steps[1].text == "Multiply powers with the same base: add the exponents"


def test_to_dict():
    data = mathlint.compute("(x+2)^2").to_dict()
    assert data["kind_label"] == "Expression"
    assert data["answer_latex"] == "x^{2} + 4 x + 4"
    assert data["letters"] == ["x"]
    assert data["decimal"] is None
    assert {"id": "expand", "label": "Expand"} in data["methods"]
