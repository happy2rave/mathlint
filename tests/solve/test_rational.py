import mathlint


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_excluded_values_come_first():
    solution = mathlint.solve("2/(x + 1) = 1/(x - 1)")
    assert solution.steps[1].text.startswith("A denominator can never be zero")
    assert "x != -1" in solution.steps[1].rendered()


def test_multiply_by_the_common_denominator():
    solution = mathlint.solve("1/x + 1/2 = 3/4")
    assert "Multiply both sides by the common denominator 4*x" in words(solution)


def test_a_root_that_was_excluded_is_dropped_with_a_reason():
    solution = mathlint.solve("(x^2 - 1)/(x - 1) = 3")
    assert "excluded at the start" in words(solution)
    assert [str(value) for value in solution.answers] == ["2"]
