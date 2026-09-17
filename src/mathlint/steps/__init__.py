"""Worked solutions: show the steps, not just the answer."""

from __future__ import annotations

from .calculus import differentiate_solution, integrate_solution
from .linalg import solve_linalg
from .matrix import format_matrix, looks_like_matrix, parse_matrix
from .solution import Solution, SolutionStep

__all__ = [
    "solve_linalg",
    "differentiate_solution",
    "integrate_solution",
    "parse_matrix",
    "format_matrix",
    "looks_like_matrix",
    "Solution",
    "SolutionStep",
]
