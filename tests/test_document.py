import pytest
import sympy as sp

from mathlint.document import parse_document
from mathlint.errors import ParseError, UnsupportedError

x = sp.Symbol("x")


def test_chain_mode_strips_leading_equals():
    doc = parse_document("(x+1)^2\n= x^2 + 2x + 1")
    assert doc.mode == "chain"
    assert len(doc.lines) == 2
    assert doc.lines[1].expr == x**2 + 2 * x + 1
    assert doc.lines[1].kind == "expression"


def test_comments_and_blank_lines_are_skipped_but_numbers_are_kept():
    doc = parse_document("# my homework\n\nx^2\n\n= x*x")
    assert [line.number for line in doc.lines] == [3, 5]


def test_equation_mode_detects_unknown_and_solutions():
    doc = parse_document("x^2 - 5x + 6 = 0\n(x-2)(x-3) = 0\nx = 2 or x = 3")
    assert doc.mode == "equation"
    assert doc.variable == x
    assert doc.lines[1].kind == "equation"
    assert doc.lines[2].kind == "solutions"
    assert doc.lines[2].solutions == [sp.Integer(2), sp.Integer(3)]


def test_solve_keyword_and_plus_minus():
    doc = parse_document("solve 2x = 4\n=> x = ±2")
    assert doc.mode == "equation"
    assert doc.lines[1].arrow == "=>"
    assert doc.lines[1].solutions == [sp.Integer(2), sp.Integer(-2)]


def test_comma_separated_solutions_and_iff_arrow():
    doc = parse_document("x^2 = 4\n\\iff x = 2, x = -2")
    assert doc.lines[1].arrow == "<=>"
    assert doc.lines[1].solutions == [sp.Integer(2), sp.Integer(-2)]


def test_no_solution_line():
    doc = parse_document("x^2 = -1\nno solution")
    assert doc.lines[1].no_solution is True
    assert doc.lines[1].solutions == []


def test_single_solved_line_is_solutions():
    doc = parse_document("2x = 6\nx = 3")
    assert doc.lines[1].kind == "solutions"
    assert doc.lines[1].solutions == [sp.Integer(3)]


def test_two_unknowns_are_not_supported_yet():
    with pytest.raises(UnsupportedError) as excinfo:
        parse_document("x + y = 1\nx = 1 - y")
    assert "one unknown" in str(excinfo.value)


def test_parse_error_carries_the_line_number():
    with pytest.raises(ParseError) as excinfo:
        parse_document("x^2\n= x*x\n= x ≤ 1")
    assert excinfo.value.line == 3


def test_empty_input_is_an_error():
    with pytest.raises(ParseError):
        parse_document("# nothing here\n\n")


def test_read_as_is_filled_in():
    doc = parse_document("d/dx(x^2)\n= 2x")
    assert doc.lines[0].read_as == "d/dx [x^2]"
    assert doc.lines[1].read_as == "2*x"
