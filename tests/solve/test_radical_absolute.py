import mathlint


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_isolate_then_square_then_reject_the_extra_root():
    solution = mathlint.solve("sqrt(2x - 1) + 2 = x")
    text = words(solution)
    assert "Isolate the root" in text
    assert "Square both sides" in text
    assert "x = 1 is not a solution" in text


def test_a_square_root_is_never_negative():
    solution = mathlint.solve("sqrt(x) = -2")
    assert "never negative" in words(solution)


def test_two_roots_take_two_rounds():
    solution = mathlint.solve("sqrt(x) + sqrt(x + 5) = 5")
    assert words(solution).count("Square both sides") == 2


def test_cube_root_is_cubed():
    solution = mathlint.solve("x^(1/3) = 2")
    assert "Cube both sides" in words(solution)


def test_absolute_value_splits_into_two_cases():
    solution = mathlint.solve("|x - 1| + 2 = 6")
    text = words(solution)
    assert "Isolate the absolute value" in text
    assert "Case 1" in text and "Case 2" in text


def test_absolute_value_is_never_negative():
    solution = mathlint.solve("|x| = -1")
    assert "never negative" in words(solution)


def test_case_that_fails_the_check_is_dropped():
    solution = mathlint.solve("|x + 1| = 2x")
    assert "x = -1/3 is not a solution" in words(solution)
