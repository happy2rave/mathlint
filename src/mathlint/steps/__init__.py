"""Worked solutions: show the steps, not just the answer."""

from __future__ import annotations

from .linalg import solve_linalg
from .matrix import format_matrix, looks_like_matrix, parse_matrix
from .solution import Solution, SolutionStep

__all__ = [
    "solve_linalg",
    "parse_matrix",
    "format_matrix",
    "looks_like_matrix",
    "Solution",
    "SolutionStep",
]
