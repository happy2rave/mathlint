import sympy as sp

from mathlint.equivalence import Verdict, compare

x, y = sp.symbols("x y")
C = sp.Symbol("C")


def test_equal_expressions_are_proved_exactly():
    result = compare((x + 1) ** 2, x**2 + 2 * x + 1)
    assert result.verdict is Verdict.OK
    assert result.method == "exact"


def test_sign_error_is_caught_with_a_counterexample():
    left = x * (2 * sp.sin(x) + x * sp.cos(x))
    right = x * (2 * sp.sin(x) - x * sp.cos(x))
    result = compare(left, right)
    assert result.verdict is Verdict.WRONG
    assert result.counterexample == {"x": "1"}
    assert result.values is not None
    assert any("sign" in hint for hint in result.hints)
    assert any("cos(x)" in hint for hint in result.hints)


def test_step_that_only_holds_for_positive_values_is_a_warning():
    result = compare(sp.sqrt(x**2), x)
    assert result.verdict is Verdict.WARNING
    assert "positive" in result.message


def test_derivative_is_evaluated_before_comparing():
    result = compare(sp.Derivative(x**2 * sp.sin(x), x), 2 * x * sp.sin(x) + x**2 * sp.cos(x))
    assert result.verdict is Verdict.OK


def test_definite_integral_is_evaluated():
    result = compare(sp.Integral(x**2, (x, 0, 1)), sp.Rational(1, 3))
    assert result.verdict is Verdict.OK


def test_indefinite_integral_is_compared_up_to_a_constant():
    integral = sp.Integral(x * sp.exp(x), x)
    result = compare(integral, x * sp.exp(x) - sp.exp(x) + C, up_to_constant_in=x)
    assert result.verdict is Verdict.OK


def test_wrong_antiderivative_is_caught():
    integral = sp.Integral(x * sp.exp(x), x)
    result = compare(integral, x * sp.exp(x) + sp.exp(x), up_to_constant_in=x)
    assert result.verdict is Verdict.WRONG


def test_two_variables_are_supported():
    result = compare((x + y) ** 2, x**2 + 2 * x * y + y**2)
    assert result.verdict is Verdict.OK


def test_no_real_values_gives_unsure():
    result = compare(sp.log(-(x**2) - 1), sp.Integer(0))
    assert result.verdict is Verdict.UNSURE


def test_unequal_constants_are_wrong():
    result = compare(sp.Integer(2), sp.Integer(3))
    assert result.verdict is Verdict.WRONG
    assert result.values == ("2", "3")
