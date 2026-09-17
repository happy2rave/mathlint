"""The files in examples/ must keep doing what their comments promise."""

from pathlib import Path

import pytest

import mathlint

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize(
    ("name", "expected_ok", "expected_error_line"),
    [
        ("derivative-sign-slip.txt", False, 5),
        ("integration-by-parts.txt", True, None),
        ("squaring-invents-a-root.txt", False, 4),
    ],
)
def test_examples(name, expected_ok, expected_error_line):
    report = mathlint.check((EXAMPLES / name).read_text(encoding="utf-8"))
    assert report.ok is expected_ok
    if expected_error_line is None:
        assert report.first_error is None
    else:
        assert report.first_error is not None
        assert report.first_error.line == expected_error_line
