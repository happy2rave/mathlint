import pytest
import sympy as sp

from mathlint.errors import ParseError
from mathlint.parse.plain import parse_expression

x = sp.Symbol("x")


def parsed(text):
    return parse_expression(text).expr


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"\frac{d}{dx} x^2 \sin x", sp.Derivative(x**2 * sp.sin(x), x)),
        (r"2x \sin x + x^2 \cos x", 2 * x * sp.sin(x) + x**2 * sp.cos(x)),
        (r"x(2\sin x + x\cos x)", x * (2 * sp.sin(x) + x * sp.cos(x))),
        (r"\int x e^x \, dx", sp.Integral(x * sp.exp(x), x)),
        (r"\int_{0}^{\pi} \sin x \, dx", sp.Integral(sp.sin(x), (x, 0, sp.pi))),
        (r"\frac{1}{2}x^{2}", x**2 / 2),
        (r"\sqrt{x^2+1}", sp.sqrt(x**2 + 1)),
        (r"\sqrt[3]{x}", x ** sp.Rational(1, 3)),
        (r"\left( x + 1 \right)^2 \cdot 3", 3 * (x + 1) ** 2),
        (r"\ln\left|x\right|", sp.log(sp.Abs(x))),
        (r"\sin^2 x", sp.sin(x) ** 2),
        (r"e^{2x}", sp.exp(2 * x)),
        (r"2 \pi", 2 * sp.pi),
        (r"\frac{x^2 - 1}{x - 1}", (x**2 - 1) / (x - 1)),
    ],
)
def test_latex_expressions(text, expected):
    assert sp.simplify(parsed(text) - expected) == 0


def test_unsupported_command_is_reported():
    with pytest.raises(ParseError) as excinfo:
        parse_expression(r"\mathbb{R}")
    assert "mathbb" in str(excinfo.value)
