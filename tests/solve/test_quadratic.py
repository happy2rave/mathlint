import pytest

import mathlint


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_methods_offered_for_a_factorable_quadratic():
    solution = mathlint.solve("x^2 - 5x + 6 = 0")
    assert solution.methods == ["factoring", "formula", "completing-square"]
    assert solution.method == "factoring"


def test_formula_is_the_default_when_the_roots_are_irrational():
    solution = mathlint.solve("x^2 - 2x - 1 = 0")
    assert solution.method == "formula"
    assert "factoring" not in solution.methods


@pytest.mark.parametrize(
    ("method", "fragment"),
    [
        ("factoring", "Factor"),
        ("formula", "discriminant"),
        ("completing-square", "to both sides to complete the square"),
    ],
)
def test_every_method_reaches_the_same_answer(method, fragment):
    solution = mathlint.solve("x^2 - 5x + 6 = 0", method=method)
    assert [str(value) for value in solution.answers] == ["2", "3"]
    assert fragment in words(solution)


def test_square_root_method_for_a_bracket_squared():
    solution = mathlint.solve("(x + 1)^2 = 4")
    assert solution.method == "square-root"
    assert "square root of both sides" in words(solution)


def test_factoring_names_the_two_numbers():
    solution = mathlint.solve("x^2 - 5x + 6 = 0", method="factoring")
    assert "multiply to 6 and add up to -5" in words(solution)


def test_negative_discriminant_mentions_the_complex_solutions():
    solution = mathlint.solve("x^2 + 2x + 5 = 0")
    assert "no real solution" in words(solution)
    assert "complex" in words(solution)


def test_leading_coefficient_is_made_positive():
    solution = mathlint.solve("-x^2 + 4 = 0")
    assert "Multiply both sides by -1" in words(solution)
