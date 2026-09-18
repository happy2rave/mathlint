import json

import pytest

from mathlint.cli import main

WRONG = "(x+1)^2\n= x^2 + 2x + 2\n"
RIGHT = "(x+1)^2\n= x^2 + 2x + 1\n"


@pytest.fixture
def solution(tmp_path):
    def write(text):
        path = tmp_path / "solution.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    return write


def test_wrong_solution_exits_with_one(solution, capsys):
    code = main(["check", solution(WRONG)])
    assert code == 1
    assert "WRONG" in capsys.readouterr().out


def test_correct_solution_exits_with_zero(solution, capsys):
    assert main(["check", solution(RIGHT)]) == 0
    assert "No mistakes found" in capsys.readouterr().out


def test_reads_stdin(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(RIGHT))
    assert main(["check", "-"]) == 0
    assert "No mistakes found" in capsys.readouterr().out


def test_json_output(solution, capsys):
    main(["check", solution(WRONG), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    assert data["first_error"] == 2


def test_markdown_output(solution, capsys):
    main(["check", solution(WRONG), "--format", "markdown"])
    assert "| Line |" in capsys.readouterr().out


def test_unreadable_line_exits_with_two(solution, capsys):
    code = main(["check", solution("x^2\n= x ≤ 1\n")])
    assert code == 2
    assert "line 2" in capsys.readouterr().err


def test_missing_file_exits_with_two(capsys):
    assert main(["check", "does-not-exist.txt"]) == 2
    assert "does-not-exist.txt" in capsys.readouterr().err


def test_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "0.4.0" in capsys.readouterr().out
