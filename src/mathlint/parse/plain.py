"""Read plain typed math (``2x sin x + x^2 cos x``) into a SymPy expression.

The parser is deliberately strict and noisy: anything it cannot read is an
error, and anything it reads in a way the student might not expect produces a
warning. Guessing silently is the one thing a checker must never do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    split_symbols,
    standard_transformations,
)

from ..errors import ParseError
from .unicode_math import normalize_unicode

MAX_LENGTH = 2000

#: Functions a student may write, mapped to their SymPy name.
FUNCTIONS: dict[str, str] = {
    name: name
    for name in (
        "sin cos tan cot sec csc asin acos atan acot asec acsc "
        "sinh cosh tanh coth sech csch asinh acosh atanh acoth "
        "exp log sqrt cbrt Abs sign floor ceiling"
    ).split()
}
FUNCTIONS.update(
    {
        "ln": "log",
        "abs": "Abs",
        "ceil": "ceiling",
        "arcsin": "asin",
        "arccos": "acos",
        "arctan": "atan",
        "arccot": "acot",
        "arcsec": "asec",
        "arccsc": "acsc",
        "arcsinh": "asinh",
        "arccosh": "acosh",
        "arctanh": "atanh",
    }
)

#: ``sin^-1 x`` means arcsine, not one over sine.
INVERSE = {
    "sin": "asin",
    "cos": "acos",
    "tan": "atan",
    "cot": "acot",
    "sec": "asec",
    "csc": "acsc",
    "sinh": "asinh",
    "cosh": "acosh",
    "tanh": "atanh",
}

_SAFE_NAMES = (
    "sin cos tan cot sec csc asin acos atan acot asec acsc "
    "sinh cosh tanh coth sech csch asinh acosh atanh acoth "
    "exp log sqrt cbrt root Abs sign factorial floor ceiling "
    "Derivative Integral Symbol Function Integer Float Rational pi oo "
    # the evaluate=False pass rewrites operators into these constructors
    "Add Mul Pow Eq Ne Lt Le Gt Ge And Or Not"
).split()

_GLOBAL_DICT: dict[str, object] = {"__builtins__": {}}
for _name in _SAFE_NAMES:
    _GLOBAL_DICT[_name] = getattr(sp, _name)

# ``e`` is Euler's number; ``E`` and ``I`` stay ordinary symbols, because in
# engineering they usually mean Young's modulus and a current or a moment.
_LOCAL_DICT: dict[str, object] = {
    "e": sp.E,
    "inf": sp.oo,
    "infty": sp.oo,
}
for _alias, _target in FUNCTIONS.items():
    _LOCAL_DICT[_alias] = getattr(sp, _target)

_TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    split_symbols,
    implicit_multiplication,
)

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER = re.compile(r"\d+(?:\.\d*)?|\.\d+")
_ALLOWED_CHARS = re.compile(r"[0-9A-Za-z_\s+\-*/^().,!|]")
_ATTRIBUTE = re.compile(r"\.\s*[A-Za-z_]")
_INDEXED_SYMBOL = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z])(\d+)(?![A-Za-z0-9_.])")
_BIG_FACTORIAL = re.compile(r"\d{4,}\s*!")
_BIG_POWER = re.compile(r"\^\s*-?\s*\d{5,}")
_POWER_TOWER = re.compile(r"\d\s*\^\s*\(?\s*\d+\s*\)?\s*\^")
_EMPTY_BRACKETS = re.compile(r"\(\s*\)")
_AMBIGUOUS_SLASH = re.compile(r"(\d*)\s*/\s*(\d+)([A-Za-z(])")
_AMBIGUOUS_POWER = re.compile(r"([A-Za-z0-9_]+)\s*\^\s*(-?\d+)([A-Za-z(])")


@dataclass
class Parsed:
    """A parsed line: the expression plus anything worth telling the student."""

    expr: sp.Expr
    warnings: list[str] = field(default_factory=list)


class _PlainPrinter(sp.printing.str.StrPrinter):
    """Print the way a student writes, not the way SymPy stores it.

    ``Derivative(x**2, x)`` says nothing to someone checking their homework;
    ``d/dx [x^2]`` is the same thing in their own notation.
    """

    def _print_Derivative(self, expr: sp.Derivative) -> str:
        operators = " ".join(
            f"d/d{variable}" if count == 1 else f"d^{count}/d{variable}^{count}"
            for variable, count in expr.variable_count
        )
        return f"{operators} [{self._print(expr.expr)}]"

    def _print_Integral(self, expr: sp.Integral) -> str:
        body = self._print(expr.function)
        for limit in expr.limits:
            if len(limit) == 3:
                variable, lower, upper = limit
                body = (
                    f"int from {self._print(lower)} to {self._print(upper)} "
                    f"of {body} d{variable}"
                )
            else:
                body = f"int {body} d{limit[0]}"
        return body


def read_as(expr: sp.Expr) -> str:
    """Render an expression the way this parser reads it back."""
    return _PlainPrinter().doprint(expr).replace("**", "^")


def parse_expression(text: str) -> Parsed:
    """Parse one line of typed or LaTeX math."""
    text = normalize_unicode(text)
    if "\\" in text:
        from .latex import latex_to_plain

        text = latex_to_plain(text)
    text = text.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    _validate(text)
    text = _INDEXED_SYMBOL.sub(r"\1_\2", text)

    from .calculus import rewrite_calculus

    text = rewrite_calculus(text)
    text = rewrite_abs(text)
    text = rewrite_functions(text)

    warnings = _ambiguity_warnings(text)
    expr = _parse_sympy(text)
    return Parsed(expr=expr, warnings=warnings)


def _validate(text: str) -> None:
    if len(text) > MAX_LENGTH:
        raise ParseError(f"this line is too long (limit {MAX_LENGTH} characters)")
    if "__" in text:
        raise ParseError("'__' is not allowed")
    if _ATTRIBUTE.search(text):
        raise ParseError("attribute access (a dot before a letter) is not allowed")
    if _BIG_FACTORIAL.search(text) or _BIG_POWER.search(text) or _POWER_TOWER.search(text):
        raise ParseError("that number is too big to compute")
    for char in text:
        if not _ALLOWED_CHARS.match(char):
            raise ParseError(f"cannot read the character {char!r}")
    if _EMPTY_BRACKETS.search(text):
        # what an unfilled box in the web page's editor turns into
        raise ParseError("there is an empty box on this line — fill it in or delete it")
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ParseError("unbalanced bracket")
    if depth:
        raise ParseError("unbalanced bracket")


def _ambiguity_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    for match in _AMBIGUOUS_SLASH.finditer(text):
        before, number, after = match.groups()
        warnings.append(
            f"`{before}/{number}{after}` is read as ({before or '1'}/{number})*{after} — "
            f"write {before}/({number}{after}) if you meant that"
        )
    for match in _AMBIGUOUS_POWER.finditer(text):
        base, exponent, after = match.groups()
        warnings.append(
            f"`{base}^{exponent}{after}` is read as ({base}^{exponent})*{after} — "
            f"write {base}^({exponent}{after}) if you meant that"
        )
    return warnings


def rewrite_abs(text: str) -> str:
    """Turn ``|x|`` into ``Abs(x)``."""
    out: list[str] = []
    open_bars = 0
    previous = ""
    for char in text:
        if char == "|":
            closing = open_bars and (previous.isalnum() or previous in ")!|")
            if closing:
                out.append(")")
                open_bars -= 1
                previous = ")"
            else:
                out.append(" Abs(")
                open_bars += 1
                previous = "("
            continue
        out.append(char)
        if not char.isspace():
            previous = char
    if open_bars:
        raise ParseError("unbalanced | ... | bars")
    return "".join(out)


def rewrite_functions(text: str) -> str:
    """Give every function call explicit brackets: ``sin 2x`` -> ``sin(2*x)``."""
    out: list[str] = []
    index = 0
    while index < len(text):
        match = _IDENT.match(text, index)
        if match and match.group(0) in FUNCTIONS:
            rendered, index = _function_call(text, index)
            out.append(rendered)
        elif match:
            out.append(match.group(0))
            index = match.end()
        else:
            out.append(text[index])
            index += 1
    return "".join(out)


def _function_call(text: str, index: int) -> tuple[str, int]:
    match = _IDENT.match(text, index)
    assert match is not None
    name = match.group(0)
    after_name, exponent = _read_exponent(text, match.end())
    start = _skip_spaces(text, after_name)
    if start < len(text) and text[start] == "(":
        inner, end = _balanced(text, start)
        argument = rewrite_functions(inner)
    else:
        raw, end = _read_factor_run(text, start)
        if not raw.strip():
            raise ParseError(f"{name} needs an argument")
        argument = raw
    canonical = FUNCTIONS[name]
    if exponent is not None and exponent.replace(" ", "") in {"-1", "(-1)"}:
        if canonical not in INVERSE:
            raise ParseError(f"{name}^-1 is not supported")
        return f"{INVERSE[canonical]}({argument})", end
    if exponent is not None:
        return f"({canonical}({argument}))^({exponent})", end
    return f"{canonical}({argument})", end


def _read_exponent(text: str, index: int) -> tuple[int, str | None]:
    start = _skip_spaces(text, index)
    if start >= len(text) or text[start] != "^":
        return index, None
    start = _skip_spaces(text, start + 1)
    sign = ""
    if start < len(text) and text[start] in "+-":
        sign = text[start]
        start = _skip_spaces(text, start + 1)
    if start < len(text) and text[start] == "(":
        inner, end = _balanced(text, start)
        return end, f"{sign}({inner})"
    match = _NUMBER.match(text, start) or _IDENT.match(text, start)
    if match is None:
        raise ParseError("a power needs an exponent")
    return match.end(), f"{sign}{match.group(0)}"


def _read_factor_run(text: str, index: int) -> tuple[str, int]:
    """Read the factors that belong to a bracket-less function argument.

    ``sin 2x + 1`` -> the argument is ``2x``; the ``+ 1`` stays outside.
    """
    pieces: list[str] = []
    while index < len(text):
        start = _skip_spaces(text, index)
        if start >= len(text):
            index = start
            break
        char = text[start]
        match = _IDENT.match(text, start)
        if match:
            name = match.group(0)
            if name in FUNCTIONS:
                if pieces:
                    break
                rendered, index = _function_call(text, start)
                pieces.append(rendered)
                continue
            index = match.end()
            piece = name
            if index < len(text) and text[index] == "(":
                inner, index = _balanced(text, index)
                piece += f"({rewrite_functions(inner)})"
            pieces.append(piece)
            continue
        if _NUMBER.match(text, start):
            number = _NUMBER.match(text, start)
            assert number is not None
            pieces.append(number.group(0))
            index = number.end()
            continue
        if char == "(":
            inner, index = _balanced(text, start)
            pieces.append(f"({rewrite_functions(inner)})")
            continue
        if char == "^":
            index, exponent = _read_exponent(text, start)
            pieces.append(f"^({rewrite_functions(exponent or '')})")
            continue
        if char == "!":
            pieces.append("!")
            index = start + 1
            continue
        break
    return " ".join(pieces), index


def _balanced(text: str, index: int) -> tuple[str, int]:
    """Return the contents of the bracket starting at ``index`` and what follows."""
    depth = 0
    for position in range(index, len(text)):
        if text[position] == "(":
            depth += 1
        elif text[position] == ")":
            depth -= 1
            if depth == 0:
                return text[index + 1 : position], position + 1
    raise ParseError("unbalanced bracket")


def _skip_spaces(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _parse_sympy(text: str) -> sp.Expr:
    if not text.strip():
        raise ParseError("this line has no math on it")
    try:
        unevaluated = parse_expr(
            text,
            local_dict=dict(_LOCAL_DICT),
            global_dict=dict(_GLOBAL_DICT),
            transformations=_TRANSFORMATIONS,
            evaluate=False,
        )
    except ParseError:
        raise
    except Exception as exc:  # SyntaxError, TokenError, TypeError...
        raise ParseError(f"cannot read this line ({type(exc).__name__})") from exc
    _guard_size(unevaluated)
    try:
        return parse_expr(
            text,
            local_dict=dict(_LOCAL_DICT),
            global_dict=dict(_GLOBAL_DICT),
            transformations=_TRANSFORMATIONS,
        )
    except Exception as exc:
        raise ParseError(f"cannot read this line ({type(exc).__name__})") from exc


def _guard_size(expr: sp.Basic) -> None:
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Pow):
            exponent = node.exp
            if exponent.is_Number and abs(exponent) > 10000:
                raise ParseError("that number is too big to compute")
            if isinstance(exponent, sp.Pow) and exponent.base.is_Number and exponent.exp.is_Number:
                raise ParseError("that number is too big to compute")
        if isinstance(node, sp.factorial):
            argument = node.args[0]
            if argument.is_Number and argument > 1000:
                raise ParseError("that number is too big to compute")
