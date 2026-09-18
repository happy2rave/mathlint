import pytest
import sympy as sp

import mathlint

x, y = sp.symbols("x y")

CASES = [
    ("x + y = 5\nx^2 + y^2 = 13", [{x: 2, y: 3}, {x: 3, y: 2}]),
    ("y = x^2\ny = x + 2", [{x: -1, y: 1}, {x: 2, y: 4}]),
    ("xy = 6\nx + y = 5", [{x: 2, y: 3}, {x: 3, y: 2}]),
    (
        "x^2 + y^2 = 25\nx^2 - y^2 = 7",
        [{x: -4, y: -3}, {x: -4, y: 3}, {x: 4, y: -3}, {x: 4, y: 3}],
    ),
    ("x^2 + y^2 = 1\nx + y = 2", []),
    ("y = x^2 + 1\ny = x", []),
]


@pytest.mark.parametrize(("text", "expected"), CASES, ids=[case[0] for case in CASES])
def test_nonlinear_system(text, expected):
    solution = mathlint.solve(text)
    assert solution.kind == "nonlinear-system"
    assert solution.assignments == expected


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_substitution_from_the_linear_equation():
    solution = mathlint.solve("x + y = 5\nx^2 + y^2 = 13")
    text = words(solution)
    assert "Solve the first equation for" in text
    assert "Substitute" in text


def test_only_squares_are_handled_like_a_linear_system():
    solution = mathlint.solve("x^2 + y^2 = 25\nx^2 - y^2 = 7")
    assert "u = x^2" in words(solution)


def test_several_solutions_in_the_answer():
    solution = mathlint.solve("x + y = 5\nx^2 + y^2 = 13")
    assert solution.summary == "x = 2, y = 3 or x = 3, y = 2"
    assert solution.to_dict()["kind_label"] == "System of equations"


def test_a_solution_that_divides_by_zero_is_rejected():
    # y = 6/x cannot use x = 0
    solution = mathlint.solve("xy = 6\nx + y = 5")
    assert all(assignment[x] != 0 for assignment in solution.assignments)
