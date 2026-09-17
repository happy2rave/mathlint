import json

import sympy as sp

from mathlint.steps import solve_linalg
from mathlint.steps.matrix import parse_matrix


def test_rref_shows_each_row_operation():
    solution = solve_linalg("rref", parse_matrix("[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]"))
    assert solution.result == sp.eye(3)
    operations = [step.operation for step in solution.steps if step.operation]
    assert any("R1" in operation and "->" in operation for operation in operations)
    assert any("<->" in operation or "R2 ->" in operation for operation in operations)
    assert len(solution.steps) >= 4


def test_rref_of_a_dependent_system():
    solution = solve_linalg("rref", parse_matrix("[[1, 2], [2, 4]]"))
    assert solution.result == sp.Matrix([[1, 2], [0, 0]])
    assert "rank" in solution.summary.lower() or "row of zeros" in solution.summary.lower()


def test_determinant_of_two_by_two_uses_the_formula():
    solution = solve_linalg("det", parse_matrix("[[3, 8], [4, 6]]"))
    assert solution.result == -14
    assert "ad - bc" in " ".join(step.text for step in solution.steps)


def test_determinant_of_three_by_three_by_row_reduction():
    matrix = parse_matrix("[[6, 1, 1], [4, -2, 5], [2, 8, 7]]")
    solution = solve_linalg("det", matrix)
    assert solution.result == matrix.det()


def test_inverse_shows_the_augmented_matrix():
    matrix = parse_matrix("[[4, 7], [2, 6]]")
    solution = solve_linalg("inverse", matrix)
    assert solution.result == matrix.inv()
    assert any("identity" in step.text.lower() for step in solution.steps)


def test_inverse_of_a_singular_matrix_explains_why_not():
    solution = solve_linalg("inverse", parse_matrix("[[1, 2], [2, 4]]"))
    assert solution.result is None
    assert "no inverse" in solution.summary.lower()


def test_eigen_finds_values_and_vectors():
    solution = solve_linalg("eigen", parse_matrix("[[2, 0], [0, 3]]"))
    text = solution.to_text()
    assert "2" in text and "3" in text
    assert "characteristic" in text.lower()


def test_eigen_of_a_matrix_with_a_repeated_root():
    solution = solve_linalg("eigen", parse_matrix("[[2, 1], [0, 2]]"))
    assert "twice" in solution.to_text() or "multiplicity" in solution.to_text().lower()


def test_solution_renders_in_every_format():
    solution = solve_linalg("rref", parse_matrix("[[1, 2], [3, 4]]"))
    assert "R" in solution.to_text()
    assert "|" in solution.to_markdown()
    assert "\\begin{" in solution.to_latex()
    data = solution.to_dict()
    json.dumps(data)
    assert data["operation"] == "rref"
