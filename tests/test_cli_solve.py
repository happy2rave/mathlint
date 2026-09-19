import json

from mathlint.cli import main


def test_solve_prints_the_steps_and_the_answer(capsys):
    assert main(["solve", "x^2 - 5x + 6 = 0"]) == 0
    output = capsys.readouterr().out
    assert "Factor" in output
    assert "x = 2 or x = 3" in output


def test_other_methods_are_suggested(capsys):
    main(["solve", "x^2 - 5x + 6 = 0"])
    assert "--method formula" in capsys.readouterr().out


def test_choosing_a_method(capsys):
    assert main(["solve", "x^2 - 5x + 6 = 0", "--method", "formula"]) == 0
    assert "discriminant" in capsys.readouterr().out


def test_json_output(capsys):
    main(["solve", "2x + 3 = 7", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["answers"] == ["2"]
    assert data["kind"] == "linear"


def test_a_method_that_does_not_apply_exits_with_two(capsys):
    assert main(["solve", "2x + 3 = 7", "--method", "formula"]) == 2
    assert "does not apply" in capsys.readouterr().err


def test_no_equals_sign_works_it_out(capsys):
    assert main(["solve", "1/2 + 1/3"]) == 0
    output = capsys.readouterr().out
    assert "common denominator 6" in output
    assert "Answer: 5/6 (about 0.8333333333)" in output


def test_expand_from_the_command_line(capsys):
    assert main(["solve", "(x + 2)^2", "--method", "expand"]) == 0
    output = capsys.readouterr().out
    assert "Answer: x^2 + 4*x + 4" in output
    assert "--method simplify" in output


def test_nothing_to_read_exits_with_two(capsys):
    assert main(["solve", "2 +"]) == 2
    assert "mathlint:" in capsys.readouterr().err


def test_solve_a_formula_for_a_letter(capsys):
    assert main(["solve", "v = u + a t", "--for", "t"]) == 0
    assert "must not be 0" in capsys.readouterr().out


def test_a_system_from_the_command_line(capsys):
    assert main(["solve", "2x + y = 5; x - y = 1"]) == 0
    assert "x = 2, y = 1" in capsys.readouterr().out
