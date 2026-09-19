import pytest
import sympy as sp

import mathlint
from mathlint.steps.integration_methods import differentiates_back

x = sp.Symbol("x")

INTEGRALS = [
    ("int 1/(x^2 - 1) dx", 1 / (x**2 - 1)),
    ("int (3x + 5)/((x + 1)(x + 2)) dx", (3 * x + 5) / ((x + 1) * (x + 2))),
    ("int (x^3 + 1)/(x^2 - 1) dx", (x**3 + 1) / (x**2 - 1)),
    ("int (x + 1)/(x (x^2 + 1)) dx", (x + 1) / (x * (x**2 + 1))),
    ("int 1/((x - 1)^2 (x + 1)) dx", 1 / ((x - 1) ** 2 * (x + 1))),
    ("int sqrt(1 - x^2) dx", sp.sqrt(1 - x**2)),
    ("int 1/sqrt(4 + x^2) dx", 1 / sp.sqrt(4 + x**2)),
    ("int 1/(x^2 sqrt(x^2 - 9)) dx", 1 / (x**2 * sp.sqrt(x**2 - 9))),
    ("int x^2/sqrt(9 - x^2) dx", x**2 / sp.sqrt(9 - x**2)),
    ("int sqrt(9 - 4x^2) dx", sp.sqrt(9 - 4 * x**2)),
]


@pytest.mark.parametrize(("text", "integrand"), INTEGRALS, ids=[text for text, _ in INTEGRALS])
def test_written_out_and_right(text, integrand):
    result = mathlint.compute(text)
    assert differentiates_back(result.answer, integrand, x), result.to_text()
    texts = [step.text for step in result.steps]
    assert not any(text.startswith("Apply the standard") for text in texts), result.to_text()


def rendered(text):
    return [step.rendered() for step in mathlint.compute(text).steps]


def test_partial_fractions_steps():
    steps = rendered("int (3x + 5)/((x + 1)(x + 2)) dx")
    assert "A/(x + 1) + B/(x + 2)" in steps
    assert "3*x + 5 = A*(x + 2) + B*(x + 1)" in steps
    assert "2 = 1*A, so A = 2" in steps
    assert mathlint.compute("int (3x + 5)/((x + 1)(x + 2)) dx").answer_plain == (
        "2*ln|x + 1| + ln|x + 2| + C"
    )


def test_repeated_factor_compares_coefficients():
    result = mathlint.compute("int 1/((x - 1)^2 (x + 1)) dx")
    texts = [step.text for step in result.steps]
    assert "Compare the numbers in front of each power of x on both sides, and solve" in texts
    assert "A/(x + 1) + B/(x - 1) + C/(x - 1)^2" in rendered("int 1/((x - 1)^2 (x + 1)) dx")


def test_long_division_first():
    texts = [step.text for step in mathlint.compute("int (x^3 + 1)/(x^2 - 1) dx").steps]
    assert texts[1].startswith("The top's degree is not smaller than the bottom's")


def test_trig_substitution_steps():
    result = mathlint.compute("int 1/(x^2 sqrt(x^2 - 9)) dx")
    texts = [step.text for step in result.steps]
    assert texts[1].startswith("The square root has the shape sqrt(x^2 - a^2) with a = 3")
    assert "Back to x with the right triangle for theta = asec(x/3)" in texts[-2]
    assert result.answer_plain == "sqrt(x^2 - 9)/(9*x) + C"


def test_secant_uses_its_standard_integral():
    texts = [step.text for step in mathlint.compute("int 1/sqrt(4 + x^2) dx").steps]
    assert "int sec(theta) dtheta = ln|sec(theta) + tan(theta)|" in texts


def test_no_dummy_variable_in_the_steps():
    for step in mathlint.compute("int 2x cos(x^2) dx").steps:
        assert "_u" not in step.rendered()


def test_a_definite_integral_with_partial_fractions():
    result = mathlint.compute(r"\int_2^3 \frac{1}{x^2-1}\,dx")
    assert sp.simplify(result.answer - sp.integrate(1 / (x**2 - 1), (x, 2, 3))) == 0
