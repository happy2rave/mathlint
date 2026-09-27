"""mathlint's stable Python API, from 1.0 on.

What ``mathlint.__all__`` names, with these signatures, is the public API:
semantic versioning applies to it, so a change here is a deliberate one (a new
major version, or an addition in a minor one). Everything else in the package
may change in any release.
"""

import inspect
from pathlib import Path

import mathlint

ROOT = Path(__file__).resolve().parent.parent

PUBLIC = {
    "__version__",
    "check",
    "solve",
    "compute",
    "analyze",
    "compare",
    "Report",
    "Step",
    "Verdict",
    "Comparison",
    "Computation",
    "EquationSolution",
    "SystemSolution",
    "InequalitySolution",
    "MathlintError",
    "ParseError",
    "UnsupportedError",
}

SIGNATURES = {
    "check": "(text: 'str') -> 'Report'",
    "solve": (
        "(text: 'str', method: 'str | None' = None, variable: 'str | None' = None)"
        " -> 'EquationSolution | SystemSolution | InequalitySolution | Computation'"
    ),
    "compute": "(text: 'str', method: 'str | None' = None) -> 'Computation'",
    "analyze": "(text: 'str') -> 'Computation'",
    "compare": (
        "(left: 'sp.Expr', right: 'sp.Expr', up_to_constant_in: 'sp.Symbol | None' = None)"
        " -> 'Comparison'"
    ),
}


def test_the_public_names():
    assert set(mathlint.__all__) == PUBLIC
    assert len(mathlint.__all__) == len(PUBLIC)
    for name in PUBLIC:
        assert hasattr(mathlint, name), name


def test_the_public_signatures():
    for name, signature in SIGNATURES.items():
        assert str(inspect.signature(getattr(mathlint, name))) == signature, name


def test_every_error_is_a_mathlint_error():
    assert issubclass(mathlint.ParseError, mathlint.MathlintError)
    assert issubclass(mathlint.UnsupportedError, mathlint.MathlintError)
    assert issubclass(mathlint.MathlintError, Exception)


def test_the_verdicts():
    assert {verdict.value for verdict in mathlint.Verdict} == {"OK", "WRONG", "WARNING", "UNSURE"}


def test_the_documented_example_works():
    report = mathlint.check("(x+1)^2\n= x^2 + 2x + 1")
    assert report.ok
    assert mathlint.solve("sqrt(x + 3) = x - 3").answers == [6]


def test_type_checkers_read_the_annotations():
    assert (ROOT / "src" / "mathlint" / "py.typed").exists()
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"Typing :: Typed"' in metadata
    assert '"Development Status :: 5 - Production/Stable"' in metadata
