"""Whether the notebook can read a line of LaTeX.

The recognizer's beam search offers a few readings of a photo, best first; the
page keeps the first one this accepts, so a slip that makes nonsense gives way
to the next likeliest reading. Training filters its own candidates the same way.
"""

from __future__ import annotations

import re

from .parse.latex import latex_to_plain
from .parse.plain import parse_expression
from .steps import parse_matrix
from .steps.limits import looks_like_limit, parse_limit
from .steps.odes import looks_like_ode, parse_ode

# what separates the expressions of a line: relations, "or", and ";"
_BETWEEN = re.compile(r"=>|<=>|=|<|>|≤|≥|≠|\bor\b|;")


def readable(latex: str) -> bool:
    """A matrix, a limit, a differential equation, or relations between expressions."""
    try:
        if latex.startswith(r"\sim"):  # a row-reduction step: the matrix after it
            latex = latex[len(r"\sim") :]
        if latex.startswith(r"\begin{pmatrix}"):
            parse_matrix(latex)
            return True
        if looks_like_limit(latex):
            return parse_limit(latex) is not None
        if looks_like_ode(latex):
            parse_ode(latex)
            return True
        plain = latex_to_plain(latex)
        sides = [side for side in _BETWEEN.split(plain.lstrip("=")) if side.strip()]
        for side in sides:
            parse_expression(side)
        return bool(sides)
    except Exception:
        return False
