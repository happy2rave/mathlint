import pytest
import sympy as sp

import mathlint
from mathlint.errors import ParseError
from mathlint.steps.limits import DOES_NOT_EXIST, parse_limit

BANK = [
    ("lim x->3 x^2 + 1", 10),
    ("lim x->2 (x^2 - 4)/(x - 2)", 4),
    (r"\lim_{x\to 3}\frac{x^2-9}{x-3}", 6),
    ("lim x->0 sin(x)/x", 1),
    ("lim x->0 (1 - cos(x))/x^2", sp.Rational(1, 2)),
    ("lim x->4 (sqrt(x) - 2)/(x - 4)", sp.Rational(1, 4)),
    ("lim x->0 x/(sqrt(x + 1) - 1)", 2),
    ("lim x->oo (3x^2 + 2)/(x^2 - 5)", 3),
    ("lim x->oo (2x + 1)/(x^2 + 1)", 0),
    (r"\lim_{x\to\infty}\frac{1}{x}", 0),
    ("lim x->-oo x^3 - x", -sp.oo),
    ("lim x->oo e^x/x^2", sp.oo),
    ("lim x->0 1/x^2", sp.oo),
    ("lim x->0+ 1/x", sp.oo),
    ("lim x->0^- 1/x", -sp.oo),
    ("lim x->0 1/x", DOES_NOT_EXIST),
]


@pytest.mark.parametrize(("text", "expected"), BANK, ids=[text for text, _ in BANK])
def test_bank(text, expected):
    result = mathlint.compute(text)
    assert result.kind == "limit"
    if expected is DOES_NOT_EXIST:
        assert result.answer_plain == "does not exist"
    else:
        assert result.answer == expected, result.to_text()
    assert all(step.text != "Limit (computer algebra)" for step in result.steps), result.to_text()


def texts(text):
    return [step.text for step in mathlint.compute(text).steps]


def test_substitution_first():
    assert texts("lim x->3 x^2 + 1")[1].startswith("Put x = 3 straight in")


def test_factor_and_cancel():
    steps = mathlint.compute("lim x->2 (x^2 - 4)/(x - 2)").steps
    assert steps[1].text.startswith("Putting x = 2 in gives 0/0")
    assert steps[2].rendered() == "lim x->2 (x - 2)*(x + 2)/(x - 2)"
    assert steps[3].rendered() == "lim x->2 (x + 2)"


def test_conjugate():
    steps = texts("lim x->4 (sqrt(x) - 2)/(x - 4)")
    assert steps[2].startswith("Multiply the top and the bottom by the conjugate sqrt(x) + 2")


def test_lhopital():
    assert any(text.startswith("L'Hopital's rule") for text in texts("lim x->0 sin(x)/x"))


def test_divide_by_the_highest_power():
    step = mathlint.compute("lim x->oo (2x + 1)/(x^2 + 1)").steps[1]
    assert step.rendered() == "lim x->inf (2/x + 1/x^2)/(1 + 1/x^2)"
    assert step.latex().startswith(r"\lim_{x \to \infty}")


def test_both_sides_of_a_limit_that_does_not_exist():
    result = mathlint.compute("lim x->0 1/x")
    assert "from the left it goes to -inf; from the right it goes to inf" in result.steps[-1].text
    assert result.to_dict()["answer_latex"] == r"\text{does not exist}"
    assert result.decimal is None


def test_parsing():
    problem = parse_limit(r"\lim_{x\to0^+}\frac{1}{x}")
    assert (problem.point, problem.direction) == (0, "+")
    assert parse_limit("limit t -> -oo 1/t").point == -sp.oo
    assert parse_limit("x + 1") is None
    with pytest.raises(ParseError):
        parse_limit("lim (x^2)")


def test_solve_tab_takes_a_limit():
    # lim x->2 has an arrow, not an inequality
    assert mathlint.solve("lim x->2 (x^2 - 4)/(x - 2)").answer == 4
