import json

import pytest
import sympy as sp

import mathlint
from mathlint.errors import ParseError
from mathlint.web_api import handle

x, y = sp.symbols("x y")


def test_second_derivative_one_derivative_after_the_other():
    result = mathlint.compute("d^2/dx^2 x^3 sin x")
    assert result.kind == "derivative"
    assert sp.simplify(result.answer - sp.diff(x**3 * sp.sin(x), x, 2)) == 0
    texts = [step.text for step in result.steps]
    assert "The first derivative: differentiate x^3*sin(x)" in texts
    assert any(text.startswith("The second derivative: differentiate") for text in texts)


def test_third_derivative_of_a_polynomial():
    assert mathlint.compute("d^3/dx^3 (x^4 + x)").answer == 24 * x


@pytest.mark.parametrize(
    ("text", "slope"),
    [
        ("dy/dx: x^2 + y^2 = 25", -x / y),
        ("dy/dx x^3 + y^3 = 6xy", (x**2 - 2 * y) / (2 * x - y**2)),
        (r"\frac{dy}{dx}x^2+y^2=25", -x / y),
        ("y' for x y = 1", -y / x),
    ],
)
def test_implicit_differentiation(text, slope):
    result = mathlint.solve(text)
    assert result.kind == "implicit"
    assert sp.simplify(result.answer - slope) == 0, result.to_text()


def test_implicit_steps():
    steps = mathlint.compute("dy/dx: x^2 + y^2 = 25").steps
    assert steps[1].rendered() == "2*x + 2*y*y' = 0"
    assert steps[2].rendered() == "2*y*y' = -2*x"
    assert steps[3].rendered() == "y' = -x/y"
    assert mathlint.compute("dy/dx: x^2 + y^2 = 25").answer_plain == "dy/dx = -x/y"


def test_implicit_needs_x_and_y():
    with pytest.raises(ParseError):
        mathlint.compute("dy/dx: x^2 = 4")


@pytest.mark.parametrize(
    ("text", "answer"),
    [
        ("tangent to y = x^2 at x = 1", "y = 2*x - 1"),
        ("tangent line to y = x^3 - 2x at x = 2", "y = 10*x - 16"),
        ("tangent to sin(x) at 0", "y = x"),
        ("normal to y = x^2 at x = 1", "y = 3/2 - x/2"),
        ("normal to y = x^2 at x = 0", "x = 0"),
    ],
)
def test_tangent_and_normal_lines(text, answer):
    result = mathlint.solve(text)
    assert result.answer_plain == answer, result.to_text()
    assert result.decimal is None


def test_tangent_steps_and_graph():
    result = mathlint.compute("tangent to y = x^3 - 2x at x = 2")
    assert [step.rendered() for step in result.steps] == [
        "(2, 4)",
        "y' = 3*x^2 - 2, so the slope is 10",
        "y - 4 = 10*(x - 2)",
        "y = 10*x - 16",
    ]
    reply = json.loads(handle("solve", json.dumps({"text": "tangent to y = x^2 at x = 1"})))
    graph = reply["result"]["graph"]
    assert [curve["expr"] for curve in graph["curves"]] == ["x^2", "2*x - 1"]
    assert graph["marks"][0]["label"] == "(1, 1)"
