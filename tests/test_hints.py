import sympy as sp

from mathlint.hints import find_hints

x = sp.Symbol("x")


def test_whole_expression_sign_flip():
    hints = find_hints(-(x + 1), x + 1)
    assert any("sign of the whole" in hint for hint in hints)


def test_constant_factor():
    hints = find_hints(2 * x, x)
    assert any("factor" in hint and "2" in hint for hint in hints)


def test_constant_difference():
    hints = find_hints(x + 3, x + 1)
    assert any("constant" in hint for hint in hints)


def test_term_disappeared():
    hints = find_hints(x**2 + x, x**2)
    assert any("disappeared" in hint for hint in hints)


def test_term_sign_flipped():
    hints = find_hints(x**2 + sp.sin(x), x**2 - sp.sin(x))
    assert any("sign" in hint and "sin(x)" in hint for hint in hints)


def test_no_hints_when_nothing_obvious():
    assert find_hints(sp.sin(x) ** 3, sp.cos(x) ** 5 + x) == []
