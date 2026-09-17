import mathlint
from mathlint.equivalence import Verdict

DERIVATIVE_WITH_SIGN_ERROR = """
d/dx [x^2 sin x]
= 2x sin x + x^2 cos x
= x(2 sin x + x cos x)
= x(2 sin x - x cos x)
"""

INTEGRATION_BY_PARTS = """
int x e^x dx
= x e^x - int e^x dx
= x e^x - e^x + C
"""


def test_finds_the_first_wrong_step():
    report = mathlint.check(DERIVATIVE_WITH_SIGN_ERROR)
    assert report.ok is False
    assert report.first_error is not None
    assert report.first_error.line == 5
    assert report.first_error.compared_to == 4
    assert report.steps[1].verdict is Verdict.OK
    assert report.steps[2].verdict is Verdict.OK


def test_correct_integration_by_parts_passes():
    report = mathlint.check(INTEGRATION_BY_PARTS)
    assert report.ok is True
    assert all(step.verdict in (None, Verdict.OK) for step in report.steps)
    assert report.notes == []


def test_missing_integration_constant_is_a_note():
    report = mathlint.check("int 2x dx\n= x^2")
    assert report.ok is True
    assert any("+ C" in note for note in report.notes)


def test_unfinished_answer_is_a_note():
    report = mathlint.check("d/dx(x^2 + x)\n= d/dx(x^2) + d/dx(x)")
    assert any("not finished" in note for note in report.notes)


def test_warning_for_step_true_only_for_positive_values():
    report = mathlint.check("sqrt(x^2)\n= x")
    assert report.steps[1].verdict is Verdict.WARNING
    assert report.ok is True


def test_parser_warning_travels_into_the_report():
    report = mathlint.check("1/2x\n= x/2")
    assert any("1/(2x)" in warning for warning in report.steps[0].warnings)
