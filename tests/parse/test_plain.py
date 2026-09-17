import pytest
import sympy as sp

from mathlint.errors import ParseError
from mathlint.parse.plain import parse_expression, read_as

x, y, t = sp.symbols("x y t")


def parsed(text):
    return parse_expression(text).expr


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2x sin x + x^2 cos x", 2 * x * sp.sin(x) + x**2 * sp.cos(x)),
        ("x(2sin(x) + x cos(x))", x * (2 * sp.sin(x) + x * sp.cos(x))),
        ("e^x", sp.exp(x)),
        ("x e^x - e^x", x * sp.exp(x) - sp.exp(x)),
        ("sin^2(x) + cos^2 x", sp.sin(x) ** 2 + sp.cos(x) ** 2),
        ("sin^-1 x", sp.asin(x)),
        ("arctan x", sp.atan(x)),
        ("ln|x|", sp.log(sp.Abs(x))),
        ("|x - 1|", sp.Abs(x - 1)),
        ("2|x| + |y|", 2 * sp.Abs(x) + sp.Abs(y)),
        ("sin 2x", sp.sin(2 * x)),
        ("sin x cos x", sp.sin(x) * sp.cos(x)),
        ("sqrt x", sp.sqrt(x)),
        ("sqrt(x^2 + 1)", sp.sqrt(x**2 + 1)),
        ("(x+1)(x-1)", (x + 1) * (x - 1)),
        ("xy + 1", x * y + 1),
        ("3.5t", sp.Float("3.5") * t),
        ("pi/2", sp.pi / 2),
    ],
)
def test_plain_expressions(text, expected):
    assert sp.simplify(parsed(text) - expected) == 0


def test_unicode_is_normalised():
    assert sp.simplify(parsed("3 − 2·x²") - (3 - 2 * x**2)) == 0
    assert sp.simplify(parsed("√(x+1)") - sp.sqrt(x + 1)) == 0
    assert sp.simplify(parsed("2π") - 2 * sp.pi) == 0


def test_symbol_with_index_is_not_split():
    assert parsed("x1 + 2") == sp.Symbol("x_1") + 2


def test_ambiguous_slash_warns():
    result = parse_expression("1/2x")
    assert result.expr == x / 2
    assert any("1/(2x)" in w for w in result.warnings)


def test_ambiguous_power_warns():
    result = parse_expression("e^2x")
    assert result.expr == x * sp.exp(2)
    assert any("e^(2x)" in w.replace(" ", "") for w in result.warnings)


def test_no_warning_for_spaced_power():
    assert parse_expression("x^2 cos x").warnings == []


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("__import__('os')", "not allowed"),
        ("x.real", "attribute"),
        ("9^9^9^9", "too big"),
        ("100000!", "too big"),
        ("x" * 2001, "too long"),
        ("sin", "needs an argument"),
        ("(x+1", "bracket"),
        ("x ≤ 1", "≤"),
    ],
)
def test_rejected_inputs(text, fragment):
    with pytest.raises(ParseError) as excinfo:
        parse_expression(text)
    assert fragment in str(excinfo.value)


def test_read_as_uses_caret():
    assert read_as(parsed("x^2 sin x")) == "x^2*sin(x)"
