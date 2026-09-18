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


def test_no_equals_sign_exits_with_two(capsys):
    assert main(["solve", "2x + 3"]) == 2
    assert "'=' sign" in capsys.readouterr().err


def test_solve_a_formula_for_a_letter(capsys):
    assert main(["solve", "v = u + a t", "--for", "t"]) == 0
    assert "must not be 0" in capsys.readouterr().out


def test_a_system_from_the_command_line(capsys):
    assert main(["solve", "2x + y = 5; x - y = 1"]) == 0
    assert "x = 2, y = 1" in capsys.readouterr().out
