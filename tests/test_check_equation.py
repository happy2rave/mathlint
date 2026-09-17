import mathlint
from mathlint.equivalence import Verdict


def test_lost_solution_is_wrong():
    report = mathlint.check("x^2 = x\nx = 1")
    assert report.ok is False
    assert report.first_error is not None
    assert "x = 0" in report.first_error.message


def test_extraneous_solution_is_warned_then_caught_at_the_end():
    report = mathlint.check("sqrt(x) = x - 2\nx = (x-2)^2\nx = 1 or x = 4")
    assert report.steps[1].verdict is Verdict.WARNING
    assert report.ok is False
    assert report.first_error is not None
    assert report.first_error.line == 3
    assert "does not satisfy" in report.first_error.message


def test_correct_quadratic_passes():
    report = mathlint.check("x^2 - 5x + 6 = 0\n(x-2)(x-3) = 0\nx = 2 or x = 3")
    assert report.ok is True


def test_implication_arrow_allows_extra_solutions():
    report = mathlint.check("sqrt(x) = x - 2\n=> x = (x-2)^2\n=> x = 4")
    assert report.steps[1].verdict is Verdict.OK
    assert report.ok is True


def test_no_solution_answer():
    report = mathlint.check("x^2 = -1\nno solution")
    assert report.ok is True
