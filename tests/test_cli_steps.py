import json

from mathlint.cli import main


def test_rref_steps(capsys):
    assert main(["steps", "rref", "[[2, 1], [1, 3]]"]) == 0
    output = capsys.readouterr().out
    assert "R1 ->" in output or "R2 ->" in output
    assert "[ 1  0 ]" in output


def test_determinant_steps(capsys):
    assert main(["steps", "det", "[[3, 8], [4, 6]]"]) == 0
    assert "ad - bc" in capsys.readouterr().out


def test_json_format(capsys):
    main(["steps", "inverse", "[[4, 7], [2, 6]]", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["operation"] == "inverse"
    assert data["steps"]


def test_latex_format(capsys):
    main(["steps", "eigen", "[[2, 0], [0, 3]]", "--format", "latex"])
    assert "\\begin{enumerate}" in capsys.readouterr().out


def test_unreadable_matrix_exits_with_two(capsys):
    assert main(["steps", "rref", "not a matrix"]) == 2
    assert "mathlint:" in capsys.readouterr().err


def test_non_square_matrix_for_determinant(capsys):
    assert main(["steps", "det", "[[1, 2, 3], [4, 5, 6]]"]) == 2
    assert "square" in capsys.readouterr().err


def test_derivative_steps(capsys):
    assert main(["steps", "diff", "x^2 sin x"]) == 0
    output = capsys.readouterr().out
    assert "Product rule" in output
    assert "d/dx" in output


def test_integral_steps(capsys):
    assert main(["steps", "integrate", "x e^x"]) == 0
    assert "parts" in capsys.readouterr().out.lower()


def test_definite_integral_from_the_command_line(capsys):
    assert main(["steps", "integrate", "x^2", "--from", "0", "--to", "1"]) == 0
    assert "1/3" in capsys.readouterr().out


def test_half_a_range_is_refused(capsys):
    assert main(["steps", "integrate", "x^2", "--from", "0"]) == 2
    assert "--to" in capsys.readouterr().err


def test_variable_is_picked_up_from_the_expression(capsys):
    assert main(["steps", "diff", "t^3"]) == 0
    assert "d/dt" in capsys.readouterr().out
