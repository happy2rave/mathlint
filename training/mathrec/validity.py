"""Whether the notebook can read a line: the filter beam search puts candidates through."""

from __future__ import annotations

import re


def reads(latex: str) -> bool:
    """Whether mathlint's own readers understand the line, as the notebook would:
    a matrix, a limit, a differential equation, or relations between expressions."""
    from mathlint.parse.latex import latex_to_plain
    from mathlint.parse.plain import parse_expression
    from mathlint.steps import parse_matrix
    from mathlint.steps.limits import looks_like_limit, parse_limit
    from mathlint.steps.odes import looks_like_ode, parse_ode

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
        for side in re.split(r"=>|<=>|=|<|>|≤|≥|≠|\bor\b|;", plain.lstrip("=")):
            if side.strip():
                parse_expression(side)
        return True
    except Exception:
        return False
