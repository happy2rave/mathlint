"""Small deterministic practice sets matched to the problem just solved."""

from __future__ import annotations

import hashlib
import re

from .i18n import msg

_LABELS = (msg("Warm-up"), msg("Another one"), msg("Challenge"))

_BANK = {
    "polynomial": [
        "x^3 - 6x^2 + 11x - 6 = 0",
        "2x^3 - 3x^2 - 8x + 12 = 0",
        "x^4 - 5x^2 + 4 = 0",
    ],
    "rational": [
        "(x + 1)/(x - 2) = 2",
        "3/(x + 1) + 1 = 2",
        "2/(x - 3) = x/(x - 3)",
    ],
    "radical": [
        "sqrt(x + 4) = x - 2",
        "sqrt(2x + 3) = x",
        "sqrt(x + 7) + 1 = x",
    ],
    "absolute": ["|x - 2| = 5", "|2x + 1| = 7", "3|x - 1| = 12"],
    "exponential": ["2^x = 32", "3^(x - 1) = 9", "4^x = 2^(x + 3)"],
    "logarithmic": ["ln(x - 1) = ln(4)", "log(x) + log(x - 9) = 1", "ln(x^2) = ln(16)"],
    "linear-inequality": ["3x - 5 < 10", "7 - 2x >= 1", "-3 < 2x + 1 <= 9"],
    "polynomial-inequality": ["x^2 - 5x + 6 >= 0", "x^2 + x - 6 < 0", "x^3 - 4x <= 0"],
    "rational-inequality": ["(x + 1)/(x - 2) > 0", "(2x - 3)/(x + 4) <= 0", "1/(x - 1) < 2"],
    "absolute-inequality": ["|x - 3| < 5", "|2x + 1| >= 7", "3|x - 2| <= 12"],
    "compound-inequality": ["-3 < 2x + 1 <= 9", "1 <= 3x - 2 < 10", "-8 < 4 - 2x < 6"],
    "arithmetic": ["3/4 + 5/6", "2^3 - 3*(4 - 7)", "35% of 240"],
    "derivative": ["d/dx (x^3 cos x)", "d/dx ((x^2 + 1)/(x - 1))", "d/dx sin(x^2)"],
    "integral": ["int x cos(x) dx", "int (2x + 1)/(x^2 + x + 3) dx", "int_0^2 x^2 dx"],
    "limit": ["lim x->3 (x^2 - 9)/(x - 3)", "lim x->0 sin(x)/x", "lim x->oo (3x^2 + 1)/(x^2 - 2)"],
    "implicit": ["dy/dx: x^2 + xy + y^2 = 7", "dy/dx: x^3 + y^3 = 9", "dy/dx: sin(y) = x"],
    "tangent": [
        "tangent to y = x^2 + 1 at x = 2",
        "tangent to y = x^3 - x at x = 1",
        "tangent to y = sin(x) at x = 0",
    ],
    "normal": [
        "normal to y = x^2 at x = 1",
        "normal to y = x^3 at x = 1",
        "normal to y = sin(x) at x = 0",
    ],
    "ode": ["y' = 3y", "dy/dx + y = x", "y'' + 5y' + 6y = 0"],
    "series": ["maclaurin sin(x) order 5", "taylor ln(x) at 1 order 3", "maclaurin e^x order 4"],
    "analysis": ["(x^2 - 4)/(x - 1)", "x^3 - 3x", "1/(x^2 - 4)"],
    "expand": ["(2x - 3)(x + 4)", "(x - 5)^2", "(x + 2)^3"],
    "factor": ["x^2 + 7x + 12", "2x^2 - 5x - 3", "x^3 - 9x"],
    "simplify": ["(x^2 - 9)/(x^2 + x - 6)", "1/x + 1/(x + 1)", "(x^2 - 4x + 4)/(x - 2)"],
}


def practice_for(text: str, result: dict) -> list[dict[str, str]]:
    """Return three reproducible problems which exercise the same skill."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    kind = result.get("kind", "")
    variable = _variable(result.get("variable"))

    if kind == "linear":
        root = seed % 9 - 4
        shift = abs(root) + 2
        problems = [
            _linear(variable, 3, 5, root),
            _linear(variable, -2, 7, root + 2),
            f"4({variable} + {shift}) = {4 * (root + shift)}",
        ]
    elif kind == "quadratic":
        first = seed % 7 - 3
        second = first + 2
        problems = [
            _quadratic(variable, first, second),
            _quadratic(variable, first - 1, second + 1),
            _quadratic(variable, -second, first + 3),
        ]
    elif kind in {"linear-system", "nonlinear-system"}:
        x_value, y_value = seed % 5 + 1, (seed // 5) % 5 + 1
        problems = [
            f"x + y = {x_value + y_value}; 2x - y = {2 * x_value - y_value}",
            f"3x + y = {3 * x_value + y_value}; x - 2y = {x_value - 2 * y_value}",
            "x + y = 7; x^2 + y^2 = 25",
        ]
    else:
        key = result.get("method") if kind == "expression" else kind
        problems = list(_BANK.get(key, _BANK.get(kind, ())))

    problems = _rotate(problems, seed)
    method = "" if kind.endswith("system") else str(result.get("method") or "")
    return [
        {
            "label": _LABELS[index],
            "text": problem.replace("x", variable),
            "method": method,
        }
        for index, problem in enumerate(problems[:3])
    ]


def _variable(value: object) -> str:
    text = str(value or "x")
    return text if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", text) else "x"


def _linear(variable: str, coefficient: int, constant: int, root: int) -> str:
    return f"{coefficient}{variable} + {constant} = {coefficient * root + constant}"


def _quadratic(variable: str, first: int, second: int) -> str:
    middle = -(first + second)
    constant = first * second
    return f"{variable}^2 {_signed(middle)}{variable} {_signed(constant)}= 0"


def _signed(value: int) -> str:
    return f"+ {value} " if value >= 0 else f"- {abs(value)} "


def _rotate(problems: list[str], seed: int) -> list[str]:
    if not problems:
        return []
    start = seed % len(problems)
    return problems[start:] + problems[:start]
