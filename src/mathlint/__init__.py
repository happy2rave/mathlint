"""mathlint — a linter for your math.

Give it your own worked solution, line by line, and it tells you which step is
wrong and why.

    >>> import mathlint
    >>> report = mathlint.check("(x+1)^2\\n= x^2 + 2x + 1")
    >>> report.ok
    True
"""

from __future__ import annotations

from ._version import __version__
from .calc import Computation, compute
from .calc import analyze_function as analyze
from .check import check_document
from .document import parse_document
from .equivalence import Comparison, Verdict, compare
from .errors import MathlintError, ParseError, UnsupportedError
from .report import Report, Step
from .solve import EquationSolution, InequalitySolution, SystemSolution, solve

__all__ = [
    "__version__",
    "check",
    "solve",
    "compute",
    "analyze",
    "Computation",
    "EquationSolution",
    "SystemSolution",
    "InequalitySolution",
    "Report",
    "Step",
    "Verdict",
    "Comparison",
    "compare",
    "MathlintError",
    "ParseError",
    "UnsupportedError",
]


def check(text: str) -> Report:
    """Check a written solution.

    ``text`` is the solution, one step per line. Raises :class:`ParseError` if a
    line cannot be read and :class:`UnsupportedError` if it can be read but not
    checked yet.
    """
    return check_document(parse_document(text))
