import json

import pytest
import sympy as sp

import mathlint
from mathlint.solve.classify import classify
from mathlint.solve.core import Equation, Outcome, Work
from mathlint.solve.verify import verify
from mathlint.steps.solution import Solution

x = sp.Symbol("x")


@pytest.mark.parametrize(
    ("lhs", "rhs", "kind"),
    [
        (2 * x + 3, 7, "linear"),
        (x**2 - 5 * x + 6, 0, "quadratic"),
        (x**3 - x, 0, "polynomial"),
        (1 / x + 1, 2, "rational"),
        (sp.sqrt(x + 3), x - 3, "radical"),
        (sp.Abs(x - 3), 5, "absolute"),
        (2**x, 8, "exponential"),
        (sp.exp(2 * x), 5, "exponential"),
        (sp.log(x), 2, "logarithmic"),
        (sp.sin(x), sp.Rational(1, 2), "other"),
    ],
)
def test_classify(lhs, rhs, kind):
    assert classify(Equation(lhs, rhs), x) == kind


def test_verify_rejects_a_root_that_does_not_solve_the_original():
    solution = Solution(operation="solve", title="t")
    work = Work(solution, x)
    kept = verify(Equation(sp.sqrt(x + 3), x - 3), x, Outcome.of([1, 6]), work)
    assert kept.values == [6]
    assert any("not a solution" in step.text for step in solution.steps)


def test_verify_rejects_division_by_zero():
    solution = Solution(operation="solve", title="t")
    work = Work(solution, x)
    kept = verify(Equation(x / (x - 2), 2 / (x - 2)), x, Outcome.of([2]), work)
    assert kept.values == []
    assert any("denominator" in step.text for step in solution.steps)


def test_equation_needs_an_equals_sign():
    with pytest.raises(mathlint.ParseError):
        mathlint.solve("x + 1")


def test_two_unknowns_need_v06():
    with pytest.raises(mathlint.UnsupportedError):
        mathlint.solve("x + y = 1")


def test_fallback_is_labelled():
    solution = mathlint.solve("sin(x) = 1/2")
    assert solution.kind == "other"
    assert any("SymPy" in step.text for step in solution.steps)


def test_to_dict_carries_the_answers():
    data = mathlint.solve("2x + 3 = 7").to_dict()
    json.dumps(data)
    assert data["answers"] == ["2"]
    assert data["answer_text"] == "x = 2"
    assert data["kind"] == "linear"
    assert data["variable"] == "x"


def test_unknown_method_is_refused():
    with pytest.raises(mathlint.UnsupportedError):
        mathlint.solve("2x + 3 = 7", method="formula")
