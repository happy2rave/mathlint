"""Convert a documented subset of LaTeX into the plain typed format.

SymPy ships a LaTeX parser, but it silently misreads common student input —
``2x \\sin x + x^2 \\cos x`` comes back as ``2x*sin(x**2 + x)*cos(x)``. For a
tool whose whole job is to say "this line is wrong", a silent misread is worse
than no support at all. So this converter handles a subset it can handle
correctly and refuses everything else by name.
"""

from __future__ import annotations

import re

from ..errors import ParseError

_GREEK = {
    "alpha": "alpha",
    "beta": "beta",
    "gamma": "gamma",
    "delta": "delta",
    "epsilon": "epsilon",
    "varepsilon": "epsilon",
    "zeta": "zeta",
    "eta": "eta",
    "theta": "theta",
    "vartheta": "theta",
    "iota": "iota",
    "kappa": "kappa",
    "lambda": "lamda",
    "mu": "mu",
    "nu": "nu",
    "xi": "xi",
    "rho": "rho",
    "sigma": "sigma",
    "tau": "tau",
    "upsilon": "upsilon",
    "phi": "phi",
    "varphi": "phi",
    "chi": "chi",
    "psi": "psi",
    "omega": "omega",
    "Gamma": "Gamma",
    "Delta": "Delta",
    "Theta": "Theta",
    "Lambda": "Lamda",
    "Xi": "Xi",
    "Sigma": "Sigma",
    "Phi": "Phi",
    "Psi": "Psi",
    "Omega": "Omega",
}

_FUNCTIONS = {
    name: name
    for name in (
        "sin cos tan cot sec csc sinh cosh tanh coth "
        "arcsin arccos arctan arccot ln log exp"
    ).split()
}

_SYMBOLS = {
    "cdot": "*",
    "times": "*",
    "div": "/",
    "pm": "±",
    "mp": "∓",
    "pi": "pi",
    "infty": "oo",
    "int": " int ",
    "partial": "d",
    "le": "≤",
    "leq": "≤",
    "ge": "≥",
    "geq": "≥",
    "ne": "≠",
    "neq": "≠",
    "Rightarrow": " => ",
    "implies": " => ",
    "to": " => ",
    "Leftrightarrow": " <=> ",
    "iff": " <=> ",
    "equiv": " <=> ",
    "sim": " ~ ",
    "lor": " or ",
    # MathLive, the editor on the web page, writes these
    "differentialD": " d ",
    "exponentialE": " e ",
    "imaginaryI": " i ",
    "lvert": "|",
    "rvert": "|",
    "vert": "|",
    "lbrack": "(",
    "rbrack": ")",
    "lbrace": "(",
    "rbrace": ")",
}

_SPACING = {",", ";", ":", "!", " ", "quad", "qquad", "thinspace", "medspace", "\\"}
_UNWRAP = {"mathrm", "operatorname", "text", "mathit"}
_DROP = {"left", "right", "mleft", "mright", "displaystyle", "limits"}

_COMMAND = re.compile(r"\\([A-Za-z]+|.)")
_EMPTY_SCRIPT = re.compile(r"[\^_]\s*\{\s*\}")
_EMPTY_BOX = "there is an empty box on this line — fill it in or delete it"
_DERIVATIVE_NUMERATOR = re.compile(r"^\s*d(\s*\^\s*\d+)?\s*$")
_DERIVATIVE_DENOMINATOR = re.compile(r"^\s*d\s*([A-Za-z][A-Za-z0-9_]*)(\s*\^\s*\d+)?\s*$")


def latex_to_plain(text: str) -> str:
    """Convert LaTeX math into the plain format, or raise :class:`ParseError`."""
    if r"\placeholder" in text or _EMPTY_SCRIPT.search(text):
        raise ParseError(_EMPTY_BOX)
    out: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char != "\\":
            out.append(char)
            index += 1
            continue
        match = _COMMAND.match(text, index)
        if match is None:
            raise ParseError("a stray backslash")
        name = match.group(1)
        index = match.end()
        rendered, index = _command(name, text, index)
        out.append(rendered)
    return "".join(out)


def _command(name: str, text: str, index: int) -> tuple[str, int]:
    if name in _SPACING:
        return " ", index
    if name in _DROP:
        if index < len(text) and text[index] == ".":
            index += 1
        return "", index
    if name in _UNWRAP:
        content, index = _read_group(text, index)
        return latex_to_plain(content), index
    if name in ("frac", "dfrac", "tfrac", "cfrac"):
        return _fraction(text, index)
    if name == "sqrt":
        return _root(text, index)
    if name == "binom":
        raise ParseError("\\binom is not supported")
    # names are padded so that ``x\cos x`` cannot glue into one symbol ``xcos``
    if name in _FUNCTIONS:
        return f" {_FUNCTIONS[name]} ", index
    if name in _SYMBOLS:
        symbol = _SYMBOLS[name]
        return symbol if not symbol.isalnum() else f" {symbol} ", index
    if name in _GREEK:
        return f" {_GREEK[name]} ", index
    if name in ("{", "}", "(", ")", "[", "]", "|"):
        return name, index
    raise ParseError(f"\\{name} is not supported yet")


def _fraction(text: str, index: int) -> tuple[str, int]:
    numerator, index = _read_group(text, index)
    denominator, index = _read_group(text, index)
    numerator = latex_to_plain(numerator)
    denominator = latex_to_plain(denominator)
    if not numerator.strip() or not denominator.strip():
        raise ParseError(_EMPTY_BOX)
    if _DERIVATIVE_NUMERATOR.match(numerator) and _DERIVATIVE_DENOMINATOR.match(denominator):
        # \frac{d}{dx} is an operator, not a fraction.
        return f"{numerator.strip()}/{denominator.strip()}", index
    return f"(({numerator})/({denominator}))", index


def _root(text: str, index: int) -> tuple[str, int]:
    degree = None
    if index < len(text) and text[index] == "[":
        end = text.find("]", index)
        if end == -1:
            raise ParseError("unbalanced bracket after \\sqrt")
        degree = latex_to_plain(text[index + 1 : end])
        index = end + 1
    radicand, index = _read_group(text, index)
    radicand = latex_to_plain(radicand)
    if not radicand.strip() or (degree is not None and not degree.strip()):
        raise ParseError(_EMPTY_BOX)
    if degree is None:
        return f"sqrt(({radicand}))", index
    return f"(({radicand}))^(1/({degree}))", index


def _read_group(text: str, index: int) -> tuple[str, int]:
    """Read ``{...}``, or a single token when the braces are left out."""
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text):
        raise ParseError("this LaTeX command is missing its argument")
    if text[index] == "{":
        depth = 0
        for position in range(index, len(text)):
            if text[position] == "{":
                depth += 1
            elif text[position] == "}":
                depth -= 1
                if depth == 0:
                    return text[index + 1 : position], position + 1
        raise ParseError("unbalanced { } braces")
    if text[index] == "\\":
        match = _COMMAND.match(text, index)
        if match is None:
            raise ParseError("a stray backslash")
        return match.group(0), match.end()
    return text[index], index + 1
