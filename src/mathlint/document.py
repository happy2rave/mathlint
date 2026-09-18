"""Split a written solution into lines mathlint can compare.

Line 1 decides what the rest of the document means: an expression starts a
chain (``= ...`` on every following line), an equation starts an
equation-solving document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp

from .errors import ParseError, UnsupportedError
from .parse.latex import latex_to_plain
from .parse.plain import parse_expression, read_as
from .parse.unicode_math import normalize_unicode
from .steps.matrix import looks_like_matrix, parse_matrix

_ARROWS = [
    ("<=>", "<=>"),
    ("=>", "=>"),
    (r"\Leftrightarrow", "<=>"),
    (r"\iff", "<=>"),
    (r"\equiv", "<=>"),
    (r"\Rightarrow", "=>"),
    (r"\implies", "=>"),
    (r"\sim", "~"),
    ("~", "~"),
]
_PLAIN_EQUALS = re.compile(r"(?<![<>=!])=(?![=>])")
_OR = re.compile(r"\s+or\s+|\s*,\s*", re.IGNORECASE)
_NO_SOLUTION = re.compile(r"^no\s+solutions?$", re.IGNORECASE)
_SOLVE_PREFIX = re.compile(r"^solve\s+", re.IGNORECASE)
_PLUS_MINUS = "±"


@dataclass
class Line:
    """One line of the solution, already parsed."""

    number: int
    raw: str
    kind: str  # "expression" | "equation" | "solutions" | "matrix"
    expr: sp.Expr | None = None
    matrix: sp.Matrix | None = None
    equation: tuple[sp.Expr, sp.Expr] | None = None
    solutions: list[sp.Expr] | None = None
    no_solution: bool = False
    arrow: str = ""
    read_as: str = ""
    read_as_latex: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class Document:
    """A whole solution: its mode, its lines and the unknown being solved for."""

    mode: str  # "chain" | "equation" | "matrix"
    lines: list[Line]
    variable: sp.Symbol | None = None


def parse_document(text: str) -> Document:
    """Read a written solution into a :class:`Document`."""
    raw_lines = [
        (number, line.strip())
        for number, line in enumerate(text.splitlines(), start=1)
        if line.strip() and not line.strip().startswith("#")
    ]
    if not raw_lines:
        raise ParseError("there is nothing to check — write your solution one step per line")

    first_number, first_raw = raw_lines[0]
    first_body, _ = _split_arrow(normalize_unicode(first_raw))
    first_body = _SOLVE_PREFIX.sub("", first_body)
    if looks_like_matrix(first_body):
        mode = "matrix"
    elif _PLAIN_EQUALS.search(first_body):
        mode = "equation"
    else:
        mode = "chain"

    lines: list[Line] = []
    for number, raw in raw_lines:
        body, arrow = _split_arrow(normalize_unicode(raw))
        if number == first_number:
            body = _SOLVE_PREFIX.sub("", body)
        try:
            line = _parse_line(number, raw, body, arrow, mode)
        except ParseError as error:
            raise ParseError(error.message, line=number) from error
        except UnsupportedError as error:
            raise UnsupportedError(error.message, line=number) from error
        lines.append(line)

    variable = _find_variable(lines) if mode == "equation" else None
    return Document(mode=mode, lines=lines, variable=variable)


def _split_arrow(body: str) -> tuple[str, str]:
    body = body.strip()
    for token, arrow in _ARROWS:
        if body.startswith(token):
            return body[len(token) :].strip(), arrow
    return body, ""


def _parse_line(number: int, raw: str, body: str, arrow: str, mode: str) -> Line:
    if mode == "matrix":
        if body.startswith("~"):
            arrow, body = "~", body[1:].strip()
        elif number != 1 and body.startswith("="):
            arrow, body = "=", body[1:].strip()
        matrix = parse_matrix(body)
        return Line(
            number=number,
            raw=raw,
            kind="matrix",
            matrix=matrix,
            arrow=arrow,
            read_as=_compact_matrix(matrix),
            read_as_latex=sp.latex(matrix),
        )

    if "\\" in body:
        # "x=2\text{ or }x=3" and "x=\pm 2" have to be plain text before they
        # can be split into separate solutions
        body = latex_to_plain(body).strip()

    if mode == "chain":
        if number != 1 and body.startswith("="):
            body = body[1:].strip()
        parsed = parse_expression(body)
        return Line(
            number=number,
            raw=raw,
            kind="expression",
            expr=parsed.expr,
            arrow=arrow,
            read_as=read_as(parsed.expr),
            read_as_latex=sp.latex(parsed.expr),
            warnings=parsed.warnings,
        )

    if _NO_SOLUTION.match(body):
        return Line(
            number=number,
            raw=raw,
            kind="solutions",
            solutions=[],
            no_solution=True,
            arrow=arrow,
            read_as="no solution",
            read_as_latex=r"\text{no solution}",
        )

    parts = [part for part in _OR.split(body) if part.strip()]
    equations: list[tuple[sp.Expr, sp.Expr]] = []
    warnings: list[str] = []
    last_left: sp.Expr | None = None
    for part in parts:
        for piece in _expand_plus_minus(part):
            left, right, part_warnings = _parse_equation(piece, last_left)
            equations.append((left, right))
            warnings.extend(part_warnings)
            last_left = left

    if len(equations) == 1:
        left, right = equations[0]
        if left.is_Symbol and left not in right.free_symbols and right.free_symbols == set():
            return Line(
                number=number,
                raw=raw,
                kind="solutions",
                equation=(left, right),
                solutions=[right],
                arrow=arrow,
                read_as=f"{read_as(left)} = {read_as(right)}",
                read_as_latex=f"{sp.latex(left)} = {sp.latex(right)}",
                warnings=warnings,
            )
        return Line(
            number=number,
            raw=raw,
            kind="equation",
            equation=(left, right),
            arrow=arrow,
            read_as=f"{read_as(left)} = {read_as(right)}",
            read_as_latex=f"{sp.latex(left)} = {sp.latex(right)}",
            warnings=warnings,
        )

    solutions = [right for _, right in equations]
    rendered = " or ".join(f"{read_as(left)} = {read_as(right)}" for left, right in equations)
    rendered_latex = r" \quad\text{or}\quad ".join(
        f"{sp.latex(left)} = {sp.latex(right)}" for left, right in equations
    )
    return Line(
        number=number,
        raw=raw,
        kind="solutions",
        solutions=solutions,
        arrow=arrow,
        read_as=rendered,
        read_as_latex=rendered_latex,
        warnings=warnings,
    )


def _compact_matrix(matrix: sp.Matrix) -> str:
    rows = ", ".join(
        "[" + ", ".join(read_as(entry) for entry in matrix.row(index)) + "]"
        for index in range(matrix.rows)
    )
    return f"[{rows}]"


def _expand_plus_minus(part: str) -> list[str]:
    if _PLUS_MINUS not in part:
        return [part]
    return [part.replace(_PLUS_MINUS, "+"), part.replace(_PLUS_MINUS, "-")]


def _parse_equation(
    part: str, last_left: sp.Expr | None
) -> tuple[sp.Expr, sp.Expr, list[str]]:
    match = _PLAIN_EQUALS.search(part)
    if match is None:
        if last_left is None:
            raise ParseError("this line is not an equation — it needs an '=' sign")
        # "x = 2, 3" — the second part repeats the left-hand side
        parsed = parse_expression(part)
        return last_left, parsed.expr, parsed.warnings
    left_text, right_text = part[: match.start()], part[match.end() :]
    left = parse_expression(left_text)
    right = parse_expression(right_text)
    return left.expr, right.expr, left.warnings + right.warnings


def _find_variable(lines: list[Line]) -> sp.Symbol:
    first = lines[0]
    assert first.equation is not None
    left, right = first.equation
    unknowns = sorted(
        (left - right).free_symbols, key=lambda symbol: symbol.name  # type: ignore[operator]
    )
    if not unknowns:
        raise ParseError("this equation has no unknown to solve for", line=first.number)
    if len(unknowns) > 1:
        names = ", ".join(symbol.name for symbol in unknowns)
        raise UnsupportedError(
            f"mathlint can solve for one unknown at the moment, but this has {names}",
            line=first.number,
        )
    return unknowns[0]
