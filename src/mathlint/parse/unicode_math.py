"""Replace the unicode symbols people paste into a solution with plain ASCII.

Text copied out of a chat, a PDF or a textbook is full of characters that look
like math but are not the ones a parser expects: a real minus sign, a middle
dot for multiplication, superscript digits, Greek letters.
"""

from __future__ import annotations

import re

_SIMPLE = {
    "−": "-",  # minus sign
    "–": "-",  # en dash
    "—": "-",  # em dash
    "·": "*",  # middle dot
    "∙": "*",  # bullet operator
    "⋅": "*",  # dot operator
    "×": "*",  # multiplication sign
    "÷": "/",  # division sign
    "⁄": "/",  # fraction slash
    "√": "sqrt ",
    "∫": " int ",
    "∂": "d",  # partial derivative
    "π": "pi",
    "∞": "oo",
    "…": "...",
    " ": " ",  # non-breaking space
    " ": " ",  # thin space
    " ": " ",  # narrow no-break space
    "⇒": " => ",
    "→": " => ",
    "⇔": " <=> ",
    "≡": " <=> ",
    "½": "(1/2)",
    "⅓": "(1/3)",
    "⅔": "(2/3)",
    "¼": "(1/4)",
    "¾": "(3/4)",
}

_GREEK = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "Δ": "Delta",
    "ε": "epsilon",
    "ζ": "zeta",
    "η": "eta",
    "θ": "theta",
    "λ": "lamda",
    "Λ": "Lamda",
    "μ": "mu",
    "ν": "nu",
    "ρ": "rho",
    "σ": "sigma",
    "Σ": "Sigma",
    "τ": "tau",
    "φ": "phi",
    "ϕ": "phi",
    "χ": "chi",
    "ψ": "psi",
    "ω": "omega",
    "Ω": "Omega",
}

_SUPERSCRIPT = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
}
_SUPER_MINUS = "⁻"
_SUPER_RUN = re.compile(f"[{_SUPER_MINUS}{''.join(_SUPERSCRIPT)}]+")


def _superscript_run(match: re.Match[str]) -> str:
    run = match.group(0)
    negative = run.startswith(_SUPER_MINUS)
    digits = "".join(_SUPERSCRIPT.get(char, "") for char in run)
    if not digits:
        return "^"
    return f"^(-{digits})" if negative else f"^{digits}"


def normalize_unicode(text: str) -> str:
    """Rewrite unicode math characters as plain ASCII math."""
    text = _SUPER_RUN.sub(_superscript_run, text)
    for source, target in {**_SIMPLE, **_GREEK}.items():
        text = text.replace(source, target)
    return text
