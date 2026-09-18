"""The one function the web page calls, from inside its Web Worker.

Requests and replies are JSON strings, which is the cheapest way across the
JavaScript/Python boundary in Pyodide. Every reply is ``{"ok": true, "result": ...}``
or ``{"ok": false, "error": "..."}`` — the page never has to guess.
"""

from __future__ import annotations

import json

import sympy as sp

from ._version import __version__
from .check import check_document
from .document import parse_document
from .errors import MathlintError
from .parse.plain import parse_expression
from .steps import differentiate_solution, integrate_solution, parse_matrix, solve_linalg


def handle(kind: str, payload: str) -> str:
    """Answer one request from the page."""
    try:
        data = json.loads(payload) if payload else {}
        handler = _HANDLERS.get(kind)
        if handler is None:
            raise ValueError(f"unknown request {kind!r}")
        return json.dumps({"ok": True, "result": handler(data)})
    except MathlintError as error:
        return json.dumps({"ok": False, "error": str(error)})
    except Exception as error:  # the page must always get an explanation
        return json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"})


def _version(_: dict) -> str:
    return __version__


def _check(data: dict) -> dict:
    return check_document(parse_document(data["text"])).to_dict()


def _steps(data: dict) -> dict:
    operation = data["operation"]
    target = data["target"]
    if operation not in ("diff", "integrate"):
        return solve_linalg(operation, parse_matrix(target)).to_dict()

    expression = parse_expression(target).expr
    variable = _only_variable(expression)
    if operation == "diff":
        return differentiate_solution(expression, variable).to_dict()
    lower = data.get("lower", "").strip()
    upper = data.get("upper", "").strip()
    return integrate_solution(
        expression,
        variable,
        lower=parse_expression(lower).expr if lower else None,
        upper=parse_expression(upper).expr if upper else None,
    ).to_dict()


def _solve(data: dict) -> dict:
    from .solve import solve

    return solve(data["text"], method=data.get("method") or None).to_dict()


def _only_variable(expression: sp.Expr) -> sp.Symbol:
    symbols = sorted(expression.free_symbols, key=lambda symbol: symbol.name)
    return symbols[0] if len(symbols) == 1 else sp.Symbol("x")


_HANDLERS = {
    "version": _version,
    "check": _check,
    "steps": _steps,
    "solve": _solve,
}
