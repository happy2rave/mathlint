import mathlint


def test_version_is_exposed():
    assert mathlint.__version__ == "0.5.0"


def test_errors_are_exposed():
    err = mathlint.ParseError("boom", line=3)
    assert str(err) == "line 3: boom"
    assert isinstance(err, mathlint.MathlintError)
