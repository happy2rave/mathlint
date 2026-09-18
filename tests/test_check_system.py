import mathlint
from mathlint.equivalence import Verdict

GOOD = """
2x + y = 5; x - y = 1
3x = 6; x - y = 1
x = 2; 2 - y = 1
x = 2; y = 1
"""

SLIP = """
2x + y = 5; x - y = 1
3x = 6; x - y = 1
x = 2; y = 3
"""


def test_a_correct_elimination_passes():
    report = mathlint.check(GOOD)
    assert report.mode == "system"
    assert report.ok is True
    assert all(step.verdict in (None, Verdict.OK) for step in report.steps)


def test_an_arithmetic_slip_is_caught_with_the_lost_solution():
    report = mathlint.check(SLIP)
    assert report.ok is False
    assert report.first_error is not None
    assert report.first_error.line == 4
    assert "x = 2, y = 1" in report.first_error.message


def test_dropping_an_equation_is_a_warning():
    report = mathlint.check("x + y = 2; x - y = 0\nx + y = 2")
    assert report.steps[1].verdict is Verdict.WARNING
    assert "more solutions" in report.steps[1].message


def test_nonlinear_system_steps():
    report = mathlint.check(
        "x + y = 5; xy = 6\ny = 5 - x; x(5 - x) = 6\ny = 5 - x; x^2 - 5x + 6 = 0"
    )
    assert report.ok is True


def test_latex_cases_lines():
    report = mathlint.check(
        r"\begin{cases}x+y=3\\x-y=1\end{cases}"
        "\n"
        r"\begin{cases}2x=4\\x-y=1\end{cases}"
    )
    assert report.mode == "system"
    assert report.ok is True
    assert "x + y = 3" in report.steps[0].read_as
