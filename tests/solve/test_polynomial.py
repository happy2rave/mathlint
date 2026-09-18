
import mathlint


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_rational_root_theorem_and_division():
    solution = mathlint.solve("x^3 - 6x^2 + 11x - 6 = 0")
    text = words(solution)
    assert "rational root theorem" in text
    assert "is a factor" in text
    assert "Divide" in text


def test_common_factor_comes_out_first():
    solution = mathlint.solve("x^3 = 4x")
    assert "Factor out x" in words(solution)


def test_substitution_for_a_biquadratic():
    solution = mathlint.solve("x^4 - 5x^2 + 4 = 0")
    assert "substitute u = x^2" in words(solution)


def test_roots_that_are_not_nice_numbers_are_approximated_and_said_to_be():
    solution = mathlint.solve("x^3 - x - 1 = 0")
    assert len(solution.answers) == 1
    assert abs(float(solution.answers[0]) - 1.3247179572) < 1e-8
    assert "no rational root" in words(solution)
