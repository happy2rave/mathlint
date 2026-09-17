"""mathlint — a linter for your math.

Give it your own worked solution, line by line, and it tells you which step is
wrong and why.
"""

from __future__ import annotations

from ._version import __version__
from .errors import MathlintError, ParseError, UnsupportedError

__all__ = ["__version__", "MathlintError", "ParseError", "UnsupportedError"]
