"""Solving equations with steps.

Importing the solver modules registers them with the dispatcher.
"""

from __future__ import annotations

from . import fallback, linear, polynomial, quadratic, rational  # noqa: F401  (registration)
from .api import parse_equation, solve
from .solution import EquationSolution

__all__ = ["solve", "parse_equation", "EquationSolution"]
