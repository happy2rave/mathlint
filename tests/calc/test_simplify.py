import pytest
import sympy as sp

import mathlint

x, y = sp.symbols("x y")

SIMPLIFIED = [
    ("(x^2-4)/(x-2)", x + 2),
    ("(x^2-4)/(x^2+x-2)", (x - 2) / (x - 1)),
    ("(x^2 + 2x + 1)/(x + 1)", x + 1),
    ("1/x + 1/(x+1)", (2 * x + 1) / (x * (x + 1))),
    ("x/(x+1) - 1/x", (x**2 - x - 1) / (x * (x + 1))),
    ("x/(x-1) - 1/(x-1)", 1),
    ("2x + 3x - x", 4 * x),
    ("2(x+1) + 3x", 5 * x + 2),
    ("sin(x)^2 + cos(x)^2", 1),
    ("tan(x) cos(x)", sp.sin(x)),
    ("e^x e^2", sp.exp(x + 2)),
    ("(x^2)^3 x", x**7),
    ("1/sqrt(x)", sp.sqrt(x) / x),
    ("x^2 + 1", x**2 + 1),
]


@pytest.mark.parametrize(("text", "expected"), SIMPLIFIED, ids=[text for text, _ in SIMPLIFIED])
def test_simplify_bank(text, expected):
    result = mathlint.compute(text, method="simplify")
    assert sp.simplify(result.answer - expected) == 0, result.to_text()
    assert all(step.text != "Simplify" for step in result.steps), result.to_text()


def texts(text):
    return [step.text for step in mathlint.compute(text, method="simplify").steps]


def test_algebraic_fractions_are_simplified_by_default():
    assert mathlint.compute("(x^2-4)/(x-2)").method == "simplify"


def test_factor_then_cancel_and_keep_the_excluded_value():
    result = mathlint.compute("(x^2-4)/(x^2+x-2)")
    assert [step.text for step in result.steps[1:3]] == [
        "Factor the numerator and the denominator",
        "Cancel the common factor x + 2",
    ]
    assert result.steps[1].rendered() == "(x - 2)*(x + 2)/((x - 1)*(x + 2))"
    assert result.conditions == ["x != -2"]
    assert result.summary.endswith("for x != -2")
    assert result.to_dict()["conditions"] == ["x != -2"]


def test_adding_fractions():
    steps = mathlint.compute("1/x + 1/(x+1)").steps
    assert steps[1].text == "Write every fraction over the common denominator x*(x + 1)"
    assert steps[2].text == "Add the numerators"
    assert steps[3].rendered() == "(2*x + 1)/(x*(x + 1))"


def test_same_denominators_are_added_straight_away():
    assert texts("x/(x-1) - 1/(x-1)")[1] == "The denominators are the same, so add the numerators"


def test_logarithms_are_combined():
    result = mathlint.compute("ln(x) + ln(y)")
    assert result.answer == sp.log(x * y)
    assert result.steps[1].text.startswith("Combine the logarithms")


def test_nothing_to_do():
    assert texts("x^2 + 1")[-1] == "This is already as simple as it gets"


def test_a_high_power_uses_the_binomial_theorem():
    steps = mathlint.compute("(x+1)^10").steps
    assert steps[1].text.startswith("Use the binomial theorem")
    assert len(steps) == 2
