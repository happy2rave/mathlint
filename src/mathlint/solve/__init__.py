"""Solving equations with steps.

Importing the solver modules registers them with the dispatcher.
"""

from __future__ import annotations

from . import (  # noqa: F401  (importing registers each solver)
    absolute,
    exponential,
    fallback,
    linear,
    logarithmic,
    polynomial,
    quadratic,
    radical,
    rational,
)
from .api import parse_equation, solve
from .solution import EquationSolution
from .system import SystemSolution, solve_system

__all__ = ["solve", "solve_system", "parse_equation", "EquationSolution", "SystemSolution"]
