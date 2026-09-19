"""The calculator: arithmetic, simplifying, expanding and factoring, with steps."""

from __future__ import annotations

from . import analyze, expand, factor, simplify  # noqa: F401 - each module adds its method
from .api import analyze_function, compute
from .computation import Computation

__all__ = ["compute", "analyze_function", "Computation"]
