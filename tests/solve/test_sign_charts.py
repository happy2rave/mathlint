import pytest
import sympy as sp

import mathlint

oo = sp.oo
Interval, Union, FiniteSet = sp.Interval, sp.Union, sp.FiniteSet

BANK = [
    # polynomial
    ("x^2 - 5x + 6 < 0", Interval.open(2, 3)),
    ("x^2 >= 4", Union(Interval(-oo, -2), Interval(2, oo))),
    ("-x^2 + 4 > 0", Interval.open(-2, 2)),
    ("(x - 1)^2 <= 0", FiniteSet(1)),
    ("(x - 1)^2 > 0", Union(Interval.open(-oo, 1), Interval.open(1, oo))),
    ("x^2 + 1 > 0", sp.S.Reals),
    ("x^2 + 1 < 0", sp.S.EmptySet),
    ("x^3 - 4x > 0", Union(Interval.open(-2, 0), Interval.open(2, oo))),
    ("x^2 - 2 < 0", Interval.open(-sp.sqrt(2), sp.sqrt(2))),
    ("x(x - 3) <= 4", Interval(-1, 4)),
    # rational
    ("(x - 1)/(x + 2) >= 0", Union(Interval.open(-oo, -2), Interval(1, oo))),
    ("1/x < 2", Union(Interval.open(-oo, 0), Interval.open(sp.Rational(1, 2), oo))),
    ("(x^2 - 4)/(x - 1) <= 0", Union(Interval(-oo, -2), Interval.Lopen(1, 2))),
    (r"\frac{x+3}{x-2}>0", Union(Interval.open(-oo, -3), Interval.open(2, oo))),
    # absolute values
    ("|x - 3| < 2", Interval.open(1, 5)),
    ("|2x + 1| >= 5", Union(Interval(-oo, -3), Interval(2, oo))),
    ("2|x| - 1 <= 3", Interval(-2, 2)),
    ("|x| < -1", sp.S.EmptySet),
    ("|x - 1| > -2", sp.S.Reals),
    ("|x - 2| <= 0", FiniteSet(2)),
    (r"\left|x+1\right|>3", Union(Interval.open(-oo, -4), Interval.open(2, oo))),
]


@pytest.mark.parametrize(("text", "expected"), BANK, ids=[text for text, _ in BANK])
def test_bank(text, expected):
    solution = mathlint.solve(text)
    assert solution.answer == expected, solution.to_text()
    assert all(step.text != "Solve (computer algebra)" for step in solution.steps)


def step(text, starting):
    solution = mathlint.solve(text)
    return next(item for item in solution.steps if item.text.startswith(starting))


def test_the_sign_chart_is_a_table():
    chart = step("x^2 - 5x + 6 < 0", "Make a sign chart")
    assert chart.rendered().splitlines()[0].split("|")[1].strip() == "(-inf, 2)"
    assert r"\begin{array}{c|ccc}" in chart.latex()
    assert chart.rendered().splitlines()[-1].split("|")[1:] == [
        "     +     ",
        "   -    ",
        "    +    ",
    ]


def test_rows_run_left_to_right():
    rows = step("x^3 - 4x > 0", "Make a sign chart").rendered().splitlines()[2:5]
    assert [row.split("|")[0].strip() for row in rows] == ["x + 2", "x", "x - 2"]


def test_a_denominator_is_never_multiplied_across():
    solution = mathlint.solve("1/x < 2")
    assert "Do not multiply by the denominator" in solution.steps[1].text
    assert any("never part of the answer" in item.text for item in solution.steps)


def test_multiplying_by_minus_one_turns_the_sign():
    assert step("-x^2 + 4 > 0", "Multiply both sides by -1").rendered() == "x^2 - 4 < 0"


def test_absolute_values_split_into_two():
    assert step("|x - 3| < 2", "An absolute value").rendered() == "-2 < x - 3 < 2"
    assert step("|2x + 1| >= 5", "An absolute value").rendered() == (
        "2*x + 1 <= -5 or 2*x + 1 >= 5"
    )


def test_methods_and_labels():
    data = mathlint.solve("x^2 < 4").to_dict()
    assert data["kind_label"] == "Polynomial inequality"
    assert data["methods"] == [{"id": "sign-chart", "label": "Sign chart"}]
    assert mathlint.solve("2x < 4", method="sign-chart").answer == Interval.open(-oo, 2)
