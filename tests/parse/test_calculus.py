import pytest
import sympy as sp

from mathlint.errors import ParseError
from mathlint.parse.plain import parse_expression

x, t = sp.symbols("x t")


def parsed(text):
    return parse_expression(text).expr


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("d/dx x^2 sin x", sp.Derivative(x**2 * sp.sin(x), x)),
        ("d/dx(x^2) + 1", sp.Derivative(x**2, x) + 1),
        ("d/dx [x^2 sin x]", sp.Derivative(x**2 * sp.sin(x), x)),
        ("d^2/dx^2 (x^3)", sp.Derivative(x**3, (x, 2))),
        ("int x e^x dx", sp.Integral(x * sp.exp(x), x)),
        ("x e^x - int e^x dx", x * sp.exp(x) - sp.Integral(sp.exp(x), x)),
        ("int_0^1 x^2 dx", sp.Integral(x**2, (x, 0, 1))),
        ("int_(0)^(pi/2) sin x dx", sp.Integral(sp.sin(x), (x, 0, sp.pi / 2))),
        ("∫ 2t dt", sp.Integral(2 * t, t)),
        ("2 int x dx", 2 * sp.Integral(x, x)),
    ],
)
def test_calculus_notation(text, expected):
    assert parsed(text) == expected


def test_derivative_of_the_whole_rest_of_the_line():
    assert parsed("d/dx x^2 + 3x") == sp.Derivative(x**2 + 3 * x, x)


def test_integral_without_dx_is_an_error():
    with pytest.raises(ParseError) as excinfo:
        parse_expression("int x^2")
    assert "dx" in str(excinfo.value)
