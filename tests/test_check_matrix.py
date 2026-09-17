import mathlint
from mathlint.equivalence import Verdict

GOOD_ROW_REDUCTION = """
[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [0, 1/2, 1/2], [0, 2, 1]]
"""

BROKEN_ROW_REDUCTION = """
[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [0, 1/2, 1/2], [0, 2, 7]]
"""


def test_row_equivalent_steps_pass():
    report = mathlint.check(GOOD_ROW_REDUCTION)
    assert report.mode == "matrix"
    assert report.ok is True


def test_an_arithmetic_slip_in_a_row_operation_is_caught():
    report = mathlint.check(BROKEN_ROW_REDUCTION)
    assert report.ok is False
    assert report.first_error is not None
    assert report.first_error.line == 4
    assert "row" in report.first_error.message.lower()


def test_equals_sign_between_row_reduction_steps_is_a_warning():
    report = mathlint.check("[[2, 4], [1, 3]]\n= [[1, 2], [1, 3]]")
    assert report.steps[1].verdict is Verdict.WARNING
    assert "~" in report.steps[1].message


def test_identical_matrices_are_fine_with_an_equals_sign():
    report = mathlint.check("[[1, 2], [3, 4]]\n= [[1, 2], [3, 4]]")
    assert report.steps[1].verdict is Verdict.OK


def test_size_change_is_reported():
    report = mathlint.check("[[1, 2], [3, 4]]\n~ [[1, 2, 0], [3, 4, 0]]")
    assert report.first_error is not None
    assert "size" in report.first_error.message.lower()


def test_latex_matrices_work_too():
    report = mathlint.check(
        r"\begin{pmatrix} 2 & 4 \\ 1 & 3 \end{pmatrix}"
        "\n"
        r"~ \begin{pmatrix} 1 & 2 \\ 1 & 3 \end{pmatrix}"
    )
    assert report.ok is True
