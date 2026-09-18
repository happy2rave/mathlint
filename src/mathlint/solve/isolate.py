"""Get one term alone on one side: ``sqrt(x + 3) = x - 3``, ``|x - 1| = 4``.

Radical, absolute-value, exponential and logarithmic equations all start the same
way: isolate the one awkward piece, then undo it. That only works when the
equation is linear in that piece; when it is not, the caller falls back.
"""

from __future__ import annotations

import sympy as sp

from .core import Equation


def isolate(equation: Equation, piece: sp.Expr) -> Equation | None:
    """Rewrite ``equation`` as ``piece = rest``, or return None if that is impossible."""
    marker = sp.Dummy("piece")
    # xreplace, not subs: subs(sqrt(x), m) would also rewrite sqrt(x + 5) as sqrt(m^2 + 5)
    replaced = sp.expand(equation.expr.xreplace({piece: marker}))
    if not replaced.has(marker):
        return None
    polynomial = sp.Poly(replaced, marker) if replaced.is_polynomial(marker) else None
    if polynomial is None or polynomial.degree() != 1:
        return None
    coefficient, rest = polynomial.all_coeffs()
    if coefficient.has(marker) or rest.has(marker):
        return None
    value = sp.simplify(-rest / coefficient)
    if value.has(piece):
        return None
    return Equation(piece, value)


def already_isolated(equation: Equation, piece: sp.Expr) -> bool:
    return equation.lhs == piece and not equation.rhs.has(piece)
