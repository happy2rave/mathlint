"""The one function the web page calls, from inside its Web Worker.

Requests and replies are JSON strings, which is the cheapest way across the
JavaScript/Python boundary in Pyodide. Every reply is ``{"ok": true, "result": ...}``
or ``{"ok": false, "error": "..."}`` — the page never has to guess.
"""

from __future__ import annotations

import json
import re

import sympy as sp

from ._version import __version__
from .check import check_document
from .document import parse_document
from .errors import MathlintError
from .graph import graph_for, sample
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


def _tutor(data: dict) -> dict:
    """Check a student's next line, including intermediate solver-only forms."""
    previous = data["previous"]
    attempt = data["attempt"]
    report = check_document(parse_document(f"{previous}\n{attempt}"))
    checked = report.steps[-1]
    if checked.verdict is not None and checked.verdict.value in {"OK", "WARNING"}:
        return {
            "accepted": True,
            "verdict": checked.verdict.value,
            "message": checked.message,
            "hints": list(checked.hints),
        }

    # A solver may show a useful intermediate form which is not itself a final
    # answer, such as "x - 3 = 0 or x - 2 = 0". The equation checker correctly
    # rejects that as a final solution line, so compare its parsed reading with
    # the solver's expected next line as a second, narrow proof.
    expected_line = parse_document(f"{previous}\n{data['expected']}").lines[-1]
    attempt_line = parse_document(f"{previous}\n{attempt}").lines[-1]
    if expected_line.read_as == attempt_line.read_as:
        return {
            "accepted": True,
            "verdict": "OK",
            "message": "matches the next worked step",
            "hints": [],
        }

    return {
        "accepted": False,
        "verdict": checked.verdict.value if checked.verdict else "UNSURE",
        "message": checked.message or "That line does not follow yet.",
        "hints": list(checked.hints),
    }


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
    from .solve import parse_equation, solve
    from .solve.inequality import looks_like_inequality
    from .solve.system import split_equations
    from .steps.derivatives import looks_like_implicit, looks_like_tangent
    from .steps.limits import looks_like_limit
    from .steps.odes import looks_like_ode
    from .steps.series import looks_like_series

    text = data["text"]
    variable = data.get("variable") or None
    worked_out = (
        looks_like_limit(text)
        or looks_like_tangent(text)
        or looks_like_implicit(text)
        or looks_like_ode(text)
        or looks_like_series(text)
    )
    if variable is None and "=" in text and not looks_like_inequality(text) and not worked_out:
        parts = split_equations(text)
        if len(parts) == 1:
            # a formula with no x: the page asks which letter, rather than guessing
            equation = parse_equation(parts[0])
            letters = sorted(
                symbol.name for symbol in equation.lhs.free_symbols | equation.rhs.free_symbols
            )
            if len(letters) > 1 and "x" not in letters:
                return {"needs_letter": True, "letters": letters}
    result = solve(text, method=data.get("method") or None, variable=variable)
    reply = result.to_dict()
    reply["graph"] = graph_for(text, result)
    return reply


def _plot(data: dict) -> dict:
    """More points for a graph that was moved or zoomed."""
    count = data.get("count", 400)
    return sample(data["curves"], data["variable"], data["x_min"], data["x_max"], count)


_SLOW = re.compile(r"\\int|\bint\b")
_COMPUTED = {"arithmetic", "expression", "derivative", "integral"}
PREVIEW_LIMIT = 300


def _preview(data: dict) -> dict:
    """The answer alone, shown under the input while it is typed.

    Half-typed input is normal here, so this never reports an error: it answers
    with ``{"latex": None}`` instead. Integrals are left for the Solve button,
    because a hard one can take seconds.
    """
    text = data.get("text", "")
    if not text.strip() or len(text) > PREVIEW_LIMIT or _SLOW.search(text):
        return {"latex": None}
    try:
        result = _solve({"text": text})
    except Exception:
        return {"latex": None}
    if result.get("needs_letter"):
        return {"latex": None}
    steps = result.get("steps", [])
    worked = [step for step in steps[1:] if step["text"] != "This is already as simple as it gets"]
    if not worked:
        return {"latex": None}  # nothing happened, so there is nothing to show
    latex = result["answer_latex"]
    if result.get("kind") in _COMPUTED:
        latex = "= " + latex
    return {"latex": latex, "decimal_latex": result.get("decimal_latex")}


def _only_variable(expression: sp.Expr) -> sp.Symbol:
    symbols = sorted(expression.free_symbols, key=lambda symbol: symbol.name)
    return symbols[0] if len(symbols) == 1 else sp.Symbol("x")


_HANDLERS = {
    "version": _version,
    "check": _check,
    "tutor": _tutor,
    "steps": _steps,
    "solve": _solve,
    "preview": _preview,
    "plot": _plot,
}
