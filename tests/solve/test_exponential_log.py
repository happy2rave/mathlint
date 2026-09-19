import mathlint


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_same_base_is_the_default_when_it_applies():
    solution = mathlint.solve("4^x = 8")
    assert solution.methods == ["same-base", "logarithms"]
    assert "powers of 2" in words(solution)
    assert "exponents are equal" in words(solution)


def test_logarithms_work_as_the_other_method():
    solution = mathlint.solve("4^x = 8", method="logarithms")
    assert "logarithm of both sides" in words(solution)
    assert [str(value) for value in solution.answers] == ["3/2"]


def test_only_logarithms_when_there_is_no_common_base():
    solution = mathlint.solve("e^x = 5")
    assert solution.methods == ["logarithms"]


def test_isolate_the_power_first():
    solution = mathlint.solve("5e^(2x) - 3 = 7")
    assert "Isolate the power" in words(solution)


def test_a_power_is_never_negative():
    solution = mathlint.solve("2^x = -4")
    assert "always positive" in words(solution)


def test_substitution_for_a_quadratic_in_e_to_the_x():
    solution = mathlint.solve("e^(2x) - 3e^x + 2 = 0")
    assert "Substitute t = e^x" in words(solution)


def test_logarithms_are_combined_and_the_domain_is_checked():
    solution = mathlint.solve("ln(x) + ln(x - 2) = ln(3)")
    text = words(solution)
    assert "only defined for positive numbers" in text
    assert "Combine the logarithms" in text
    assert "x = -1 is not a solution" in text


def test_undo_the_logarithm():
    solution = mathlint.solve("ln(x) = 2")
    assert "Undo the logarithm" in words(solution)
    assert solution.summary == "x = e^2 (about x = 7.389056099)"
