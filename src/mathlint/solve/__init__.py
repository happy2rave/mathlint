"""Solving equations with steps.

Importing the solver modules registers them with the dispatcher.
"""

from __future__ import annotations

from . import (  # noqa: F401  (importing registers each solver)
    absolute,
    fallback,
    linear,
    polynomial,
    quadratic,
    radical,
    rational,
)
from .api import parse_equation, solve
from .solution import EquationSolution

__all__ = ["solve", "parse_equation", "EquationSolution"]
