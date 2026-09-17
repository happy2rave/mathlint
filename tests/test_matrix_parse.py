import pytest
import sympy as sp

from mathlint.errors import ParseError
from mathlint.steps.matrix import format_matrix, parse_matrix

EXPECTED = sp.Matrix([[1, 2], [3, 4]])


@pytest.mark.parametrize(
    "text",
    [
        "[[1,2],[3,4]]",
        "[1 2; 3 4]",
        "1 2; 3 4",
        "[1, 2; 3, 4]",
        r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}",
        r"\begin{bmatrix}1 & 2\\3 & 4\end{bmatrix}",
    ],
)
def test_matrix_formats(text):
    assert parse_matrix(text) == EXPECTED


def test_entries_may_be_expressions():
    matrix = parse_matrix("[[1/2, sqrt(2)],[pi, -3]]")
    assert matrix[0, 0] == sp.Rational(1, 2)
    assert matrix[0, 1] == sp.sqrt(2)
    assert matrix[1, 0] == sp.pi


def test_single_row_and_column():
    assert parse_matrix("[1, 2, 3]") == sp.Matrix([[1, 2, 3]])
    assert parse_matrix("[1; 2; 3]") == sp.Matrix([[1], [2], [3]])


def test_ragged_matrix_is_an_error():
    with pytest.raises(ParseError) as excinfo:
        parse_matrix("[[1,2],[3]]")
    assert "same number" in str(excinfo.value)


def test_not_a_matrix_is_an_error():
    with pytest.raises(ParseError):
        parse_matrix("x + 1")


def test_format_matrix_aligns_columns():
    text = format_matrix(sp.Matrix([[1, sp.Rational(1, 2)], [-30, 4]]))
    rows = text.splitlines()
    assert rows[0] == "[   1  1/2 ]"
    assert rows[1] == "[ -30    4 ]"
