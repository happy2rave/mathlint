import pytest
import sympy as sp

import mathlint
from mathlint.errors import ParseError, UnsupportedError
from mathlint.steps.odes import parse_ode

x = sp.Symbol("x")
C, C1, C2 = sp.symbols("C C1 C2")
e = sp.exp

GENERAL = [
    ("y' = 2y", C * e(2 * x)),
    ("dy/dx = x y", C * e(x**2 / 2)),
    ("y' - 3y = 6", C * e(3 * x) - 2),
    ("y' + y = x", C * e(-x) + x - 1),
    ("y'' + 3y' + 2y = 0", C1 * e(-2 * x) + C2 * e(-x)),
    ("y'' - 4y' + 4y = 0", (C1 + C2 * x) * e(2 * x)),
    ("y'' + 4y = 0", C1 * sp.cos(2 * x) + C2 * sp.sin(2 * x)),
    ("y'' + y = x", C1 * sp.cos(x) + C2 * sp.sin(x) + x),
]


@pytest.mark.parametrize(("text", "expected"), GENERAL, ids=[text for text, _ in GENERAL])
def test_general_solutions(text, expected):
    result = mathlint.solve(text)
    assert result.kind == "ode"
    assert sp.simplify(result.answer.rhs - expected) == 0, result.to_text()
    assert all(step.text != "Solve (computer algebra)" for step in result.steps)


INITIAL = [
    ("y' = x y; y(0) = 1", e(x**2 / 2)),
    ("y' + 2y = e^x; y(0) = 0", e(x) / 3 - e(-2 * x) / 3),
    ("y'' + 4y = 0; y(0) = 1, y'(0) = 0", sp.cos(2 * x)),
    (r"y^{\prime\prime}+y=0;y(0)=0,y^{\prime}(0)=1", sp.sin(x)),
]


@pytest.mark.parametrize(("text", "expected"), INITIAL, ids=[text for text, _ in INITIAL])
def test_initial_value_problems(text, expected):
    result = mathlint.solve(text)
    assert sp.simplify(result.answer.rhs - expected) == 0, result.to_text()


def texts(text):
    return [step.text for step in mathlint.compute(text).steps]


def test_separation_of_variables():
    steps = mathlint.compute("y' = 2y").steps
    assert steps[1].rendered() == "1/y dy = 2 dx"
    assert steps[2].rendered() == "ln|y| = C + 2*x"


def test_integrating_factor():
    steps = [step.rendered() for step in mathlint.compute("y' + y = x").steps]
    assert "mu = e^x" in steps
    assert "y' + y = x" in steps


def test_characteristic_equation():
    assert texts("y'' + 4y = 0")[2].startswith("Complex roots r = 0 ± 2i")
    assert mathlint.compute("y'' + 3y' + 2y = 0").steps[1].rendered() == "r^2 + 3*r + 2 = 0"


def test_implicit_differentiation_is_not_a_differential_equation():
    assert mathlint.solve("dy/dx: x^2 + y^2 = 25").kind == "implicit"
    assert mathlint.solve("dy/dx = x^2").kind == "ode"


def test_an_equation_nobody_solves_by_hand_says_so():
    with pytest.raises(UnsupportedError, match="not one mathlint can solve yet"):
        mathlint.solve("dy/dx = x^2 + y^2")


def test_errors():
    with pytest.raises(UnsupportedError):
        parse_ode("y''' = y")
    with pytest.raises(ParseError):
        parse_ode("y' = 1; y' = 2")


def test_an_initial_value_problem_is_drawn():
    import json

    from mathlint.web_api import handle

    reply = json.loads(handle("solve", json.dumps({"text": "y' = x y; y(0) = 1"})))
    graph = reply["result"]["graph"]
    assert graph["curves"][0]["expr"] == "e^(x^2/2)"
    assert graph["marks"][0]["label"] == "(0, 1)"
