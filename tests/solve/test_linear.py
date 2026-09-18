import mathlint


def texts(solution):
    return [step.text for step in solution.steps]


def test_linear_steps_name_what_they_do():
    solution = mathlint.solve("5 - x = 2x - 4")
    steps = " | ".join(texts(solution))
    assert "Add x to both sides" in steps
    assert "Divide both sides by" in steps
    assert solution.summary == "x = 3"


def test_brackets_are_expanded_first():
    solution = mathlint.solve("3(x - 1) = 2x + 5")
    assert texts(solution)[1] == "Expand the brackets"


def test_fractions_are_cleared():
    solution = mathlint.solve("x/2 + 1/3 = 5/6")
    assert any("Multiply both sides by 6" in text for text in texts(solution))


def test_identity_and_contradiction_are_explained():
    everything = mathlint.solve("2x + 1 = 2x + 1")
    assert "every real number" in everything.summary
    nothing = mathlint.solve("2x + 1 = 2x + 3")
    assert nothing.summary == "no real solution"


def test_answer_is_checked_at_the_end():
    solution = mathlint.solve("2x + 3 = 7")
    assert solution.steps[-1].text.startswith("Check x = 2")
