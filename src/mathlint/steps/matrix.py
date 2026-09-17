"""Read and print matrices.

People write matrices in at least four ways, and all of them turn up in
homework: nested brackets, MATLAB semicolons, bare rows, and LaTeX.
"""

from __future__ import annotations

import re

import sympy as sp

from ..errors import ParseError
from ..parse.plain import parse_expression, read_as
from ..parse.unicode_math import normalize_unicode

_ENVIRONMENT = re.compile(r"\\begin\{(p|b|v|V|B)?matrix\}(.*?)\\end\{(p|b|v|V|B)?matrix\}", re.S)


def parse_matrix(text: str) -> sp.Matrix:
    """Parse a matrix written in any of the supported notations."""
    text = normalize_unicode(text).strip()
    if not text:
        raise ParseError("there is no matrix here")

    environment = _ENVIRONMENT.search(text)
    if environment:
        rows = [row for row in environment.group(2).split(r"\\") if row.strip()]
        return _build([[cell for cell in row.split("&")] for row in rows])

    if text.startswith("[[") and text.endswith("]]"):
        return _build(_split_nested(text))

    body = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    if not any(char.isdigit() or char.isalpha() for char in body):
        raise ParseError("there is no matrix here")
    rows = [row for row in body.split(";") if row.strip()]
    if not rows:
        raise ParseError("there is no matrix here")
    return _build([_split_cells(row) for row in rows])


def _split_nested(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    depth = 0
    current = ""
    for char in text[1:-1]:
        if char == "[":
            depth += 1
            if depth == 1:
                current = ""
                continue
        if char == "]":
            depth -= 1
            if depth == 0:
                rows.append(_split_cells(current))
                continue
        if depth >= 1:
            current += char
    if not rows:
        raise ParseError("cannot read this matrix")
    return rows


def _split_cells(row: str) -> list[str]:
    if "," in row:
        return [cell for cell in row.split(",")]
    return [cell for cell in row.split() if cell]


def _build(rows: list[list[str]]) -> sp.Matrix:
    parsed: list[list[sp.Expr]] = []
    for row in rows:
        cells = [cell.strip() for cell in row if cell.strip()]
        if not cells:
            continue
        parsed.append([parse_expression(cell).expr for cell in cells])
    if not parsed:
        raise ParseError("there is no matrix here")
    width = len(parsed[0])
    if any(len(row) != width for row in parsed):
        raise ParseError("every row of a matrix needs the same number of entries")
    return sp.Matrix(parsed)


def format_matrix(matrix: sp.Matrix) -> str:
    """Print a matrix with its columns lined up, exact fractions and all."""
    cells = [
        [read_as(entry) for entry in matrix.row(index)]
        for index in range(matrix.rows)
    ]
    widths = [
        max(len(cells[row][column]) for row in range(matrix.rows)) for column in range(matrix.cols)
    ]
    lines = []
    for row in cells:
        rendered = "  ".join(value.rjust(widths[index]) for index, value in enumerate(row))
        lines.append(f"[ {rendered} ]")
    return "\n".join(lines)


def looks_like_matrix(text: str) -> bool:
    """True when a line of a solution is meant to be a matrix."""
    stripped = normalize_unicode(text).strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return True
    return bool(_ENVIRONMENT.search(stripped))
