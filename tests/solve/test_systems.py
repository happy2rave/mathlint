import json

import pytest
import sympy as sp

import mathlint

x, y, z = sp.symbols("x y z")

UNIQUE = [
    ("2x + y = 5\nx - y = 1", {x: 2, y: 1}),
    ("x + y = 10; x - y = 2", {x: 6, y: 4}),
    ("y = 2x - 1\n3x + y = 9", {x: 2, y: 3}),
    ("3x + 2y = 16\n4x - 5y = -17", {x: 2, y: 5}),
    ("x/2 + y/3 = 4\nx - y = 3", {x: 6, y: 3}),
    ("x + y + z = 6\n2x - y + z = 3\nx + 2y - z = 2", {x: 1, y: 2, z: 3}),
    (r"\begin{cases}x+y=3\\x-y=1\end{cases}", {x: 2, y: 1}),
]


@pytest.mark.parametrize(("text", "expected"), UNIQUE, ids=[entry[0] for entry in UNIQUE])
def test_unique_solution(text, expected):
    solution = mathlint.solve(text)
    assert solution.kind == "linear-system"
    assert solution.assignments == [expected]
    assert solution.free == []


@pytest.mark.parametrize(
    "method", ["elimination", "substitution", "gaussian", "cramer", "inverse"]
)
def test_every_method_agrees(method):
    solution = mathlint.solve("3x + 2y = 16\n4x - 5y = -17", method=method)
    assert solution.assignments == [{x: 2, y: 5}]


def test_default_methods():
    assert mathlint.solve("2x + y = 5\nx - y = 1").method == "elimination"
    assert mathlint.solve("x + y + z = 6\n2x - y + z = 3\nx + 2y - z = 2").method == "gaussian"


def words(solution):
    return " | ".join(step.text for step in solution.steps)


def test_elimination_names_what_it_does():
    text = words(mathlint.solve("3x + 2y = 16\n4x - 5y = -17", method="elimination"))
    assert "Multiply the first equation by" in text
    assert "cancels" in text


def test_substitution_solves_for_the_easy_unknown():
    text = words(mathlint.solve("2x + y = 5\nx - y = 1", method="substitution"))
    assert "Solve the first equation for y" in text
    assert "Substitute" in text


def test_cramer_uses_determinants():
    text = words(mathlint.solve("2x + y = 5\nx - y = 1", method="cramer"))
    assert "determinant" in text


def test_gaussian_uses_the_augmented_matrix():
    text = words(mathlint.solve("2x + y = 5\nx - y = 1", method="gaussian"))
    assert "augmented matrix" in text


def test_no_solution_is_explained():
    solution = mathlint.solve("x + y = 2\n2x + 2y = 5")
    assert solution.assignments == []
    assert "no solution" in solution.summary
    assert "parallel" in words(solution)


def test_infinitely_many_solutions_name_the_free_unknown():
    solution = mathlint.solve("x + y = 2\n2x + 2y = 4")
    assert solution.free == [y]
    assert solution.assignments == [{x: 2 - y, y: y}]
    assert "any real number" in solution.summary


def test_gaussian_with_a_free_unknown():
    solution = mathlint.solve("x + y + z = 1\n2x + 2y + 2z = 2\nx - y = 0")
    assert solution.free == [z]
    assert solution.assignments == [{x: (1 - z) / 2, y: (1 - z) / 2, z: z}]


def test_every_equation_is_checked():
    solution = mathlint.solve("2x + y = 5\nx - y = 1")
    assert solution.steps[-1].text.startswith("Check")


def test_a_method_that_does_not_apply_is_refused():
    with pytest.raises(mathlint.UnsupportedError):
        mathlint.solve("x + y + z = 6\n2x - y + z = 3\nx + 2y - z = 2", method="substitution")


def test_to_dict():
    data = mathlint.solve("2x + y = 5\nx - y = 1").to_dict()
    json.dumps(data)
    assert data["answers"] == [{"x": "2", "y": "1"}]
    assert data["answer_text"] == "x = 2, y = 1"
    assert data["kind_label"] == "System of linear equations"
