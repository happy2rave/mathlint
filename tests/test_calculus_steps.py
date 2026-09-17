import sympy as sp

from mathlint.parse.plain import parse_expression
from mathlint.steps import differentiate_solution, integrate_solution

x = sp.Symbol("x")


def expr(text):
    return parse_expression(text).expr


def words(solution):
    return " ".join(step.text for step in solution.steps).lower()


def test_product_rule_is_named():
    solution = differentiate_solution(expr("x^2 sin x"), x)
    assert "product rule" in words(solution)
    assert sp.simplify(solution.result - (2 * x * sp.sin(x) + x**2 * sp.cos(x))) == 0


def test_chain_rule_on_a_trig_function():
    solution = differentiate_solution(expr("sin(2x)"), x)
    assert "chain rule" in words(solution)
    assert sp.simplify(solution.result - 2 * sp.cos(2 * x)) == 0


def test_constant_factor_and_power_rule():
    solution = differentiate_solution(expr("3x^4"), x)
    assert "power rule" in words(solution)
    assert "constant" in words(solution)
    assert sp.simplify(solution.result - 12 * x**3) == 0


def test_exponential_chain_rule():
    solution = differentiate_solution(expr("e^(x^2)"), x)
    assert sp.simplify(solution.result - 2 * x * sp.exp(x**2)) == 0


def test_quotient_is_handled():
    solution = differentiate_solution(expr("sin(x)/x"), x)
    assert sp.simplify(solution.result - sp.diff(sp.sin(x) / x, x)) == 0


def test_logarithmic_differentiation_is_explained():
    solution = differentiate_solution(expr("x^x"), x)
    assert "logarithmic" in words(solution)
    assert sp.simplify(solution.result - x**x * (sp.log(x) + 1)) == 0


def test_integration_by_parts_is_named():
    solution = integrate_solution(expr("x e^x"), x)
    assert "parts" in words(solution)
    assert sp.simplify(solution.result - (x * sp.exp(x) - sp.exp(x))) == 0


def test_substitution_is_named():
    solution = integrate_solution(expr("sin(2x)"), x)
    assert "substitut" in words(solution)
    assert sp.simplify(solution.result + sp.cos(2 * x) / 2) == 0


def test_reciprocal_integral():
    solution = integrate_solution(expr("1/x"), x)
    assert sp.simplify(solution.result - sp.log(x)) == 0


def test_definite_integral_evaluates_the_bounds():
    solution = integrate_solution(expr("x^2"), x, lower=sp.Integer(0), upper=sp.Integer(1))
    assert solution.result == sp.Rational(1, 3)
    assert "F(1) - F(0)" in " ".join(step.text for step in solution.steps)


def test_integral_without_a_by_hand_method_says_so():
    solution = integrate_solution(expr("e^(x^2)"), x)
    assert "by hand" in solution.summary.lower() or "by hand" in words(solution)


def test_solution_can_be_rendered():
    solution = differentiate_solution(expr("x^2 sin x"), x)
    assert "Product rule" in solution.to_text()
    assert solution.to_dict()["operation"] == "diff"
