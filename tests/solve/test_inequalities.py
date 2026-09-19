import pytest
import sympy as sp

import mathlint
from mathlint.solve.intervals import as_inequality, as_intervals, number_line

x = sp.Symbol("x")
oo = sp.oo
Interval = sp.Interval

LINEAR = [
    ("3 - 2x < 7", Interval.open(-2, oo)),
    ("2(x - 1) >= x + 3", Interval(5, oo)),
    ("x/2 + 1/3 <= 5/6", Interval(-oo, 1)),
    ("x + 1 < 2x", Interval.open(1, oo)),
    ("5x - 3 > 2x + 9", Interval.open(4, oo)),
    ("-x <= 4", Interval(-4, oo)),
    ("2x + 1 > 2x", sp.S.Reals),
    ("2x + 1 < 2x", sp.S.EmptySet),
    (r"3x-1\le 5", Interval(-oo, 2)),
    (r"2x\geq 4", Interval(2, oo)),
    ("4 ≥ 2x", Interval(-oo, 2)),
    ("1 < 2x + 3 <= 7", Interval.Lopen(-1, 2)),
]


@pytest.mark.parametrize(("text", "expected"), LINEAR, ids=[text for text, _ in LINEAR])
def test_linear_bank(text, expected):
    solution = mathlint.solve(text)
    assert isinstance(solution, mathlint.InequalitySolution)
    assert solution.answer == expected, solution.to_text()
    assert all(step.text != "Solve (computer algebra)" for step in solution.steps)


def texts(text):
    return [step.text for step in mathlint.solve(text).steps]


def test_dividing_by_a_negative_turns_the_sign_around():
    steps = mathlint.solve("3 - 2x < 7").steps
    assert "turns the inequality sign around" in steps[2].text
    assert steps[2].rendered() == "x > -2"


def test_swapping_sides_keeps_the_coefficient_positive():
    assert texts("x + 1 < 2x")[1].startswith("Swap the sides")


def test_a_number_on_each_side_is_checked():
    assert texts("3 - 2x < 7")[-1] == (
        "Check a number on each side: x = -1 gives 5 < 7, true; x = -3 gives 9 < 7, false"
    )


def test_no_unknown_left():
    assert texts("2x + 1 > 2x")[-1] == "There is no x left, and 1 > 0 is always true"


def test_answer_forms():
    solution = mathlint.solve("x/2 + 1/3 <= 5/6")
    assert solution.summary == "x <= 1, that is (-inf, 1]"
    data = solution.to_dict()
    assert data["kind_label"] == "Linear inequality"
    assert data["answer_latex"] == r"x \le 1"
    assert data["interval_latex"] == r"\left(-\infty, 1\right]"
    assert data["number_line"] == {
        "intervals": [
            {
                "from": None,
                "to": 1.0,
                "from_closed": False,
                "to_closed": True,
                "from_label": None,
                "to_label": "1",
            }
        ],
        "points": [],
    }


def test_interval_helpers():
    answer = sp.Union(Interval.open(-oo, -2), Interval(3, oo))
    assert as_inequality(x, answer) == (
        "x < -2 or x >= 3",
        r"x < -2 \quad\text{or}\quad x \ge 3",
    )
    assert as_intervals(answer)[0] == "(-inf, -2) U [3, inf)"
    everything_but_two = sp.Union(Interval.open(-oo, 2), Interval.open(2, oo))
    assert as_inequality(x, everything_but_two)[0] == "x != 2"
    assert number_line(sp.FiniteSet(1))["points"] == [{"at": 1.0, "label": "1"}]


def test_web_page_gets_an_inequality():
    import json

    from mathlint.web_api import handle

    reply = json.loads(handle("solve", json.dumps({"text": r"3-2x<7"})))
    assert reply["ok"] is True
    assert reply["result"]["interval_text"] == "(-2, inf)"
    reply = json.loads(handle("solve", json.dumps({"text": r"x\le 3"})))
    assert reply["result"]["answer_latex"] == r"x \le 3"


def test_more_than_one_letter_is_not_solved_yet():
    with pytest.raises(mathlint.UnsupportedError):
        mathlint.solve("x + y < 3")
