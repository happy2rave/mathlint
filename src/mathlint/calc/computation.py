"""The result of working something out: the steps, the exact answer and a decimal."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..i18n import msg
from ..parse.plain import latex_of, read_as
from ..steps.solution import Solution

KIND_LABELS = {
    "arithmetic": msg("Arithmetic"),
    "expression": msg("Expression"),
    "derivative": msg("Derivative"),
    "integral": msg("Integral"),
    "analysis": msg("Function analysis"),
    "limit": msg("Limit"),
    "implicit": msg("Implicit differentiation"),
    "tangent": msg("Tangent line"),
    "normal": msg("Normal line"),
    "ode": msg("Differential equation"),
    "series": msg("Taylor series"),
}

METHOD_LABELS = {
    "calculate": msg("Calculate", context="method"),
    "simplify": msg("Simplify", context="method"),
    "expand": msg("Expand", context="method"),
    "factor": msg("Factor", context="method"),
    "derivative": msg("Differentiate", context="method"),
    "integral": msg("Integrate", context="method"),
    "analyze": msg("Analyze the function", context="method"),
    "limit": msg("Limit", context="method"),
    "implicit": msg("Implicit differentiation", context="method"),
    "tangent": msg("Tangent line", context="method"),
    "normal": msg("Normal line", context="method"),
    "ode": msg("Differential equation", context="method"),
    "series": msg("Taylor series", context="method"),
}

SIGNIFICANT_DIGITS = 10


@dataclass
class Computation(Solution):
    kind: str = "arithmetic"
    method: str = "calculate"
    methods: list[str] = field(default_factory=list)
    answer: sp.Expr | None = None
    answer_plain: str = ""
    answer_latex: str = ""
    decimal: str | None = None
    decimal_latex: str | None = None
    letters: list[str] = field(default_factory=list)
    #: conditions the answer comes with, such as "x != 2"
    conditions: list[str] = field(default_factory=list)
    #: points worth marking on a graph: {"x", "y", "what"}
    marks: list[dict] = field(default_factory=list)
    #: curves to draw, when the answer itself is not the function to draw
    plot: list = field(default_factory=list)
    #: a definite integral's bounds, to shade the area under the first curve
    area: tuple[float, float] | None = None

    def finish(self, value: sp.Expr, shown: str | None = None, shown_latex: str | None = None):
        self.answer = value
        self.result = value
        self.answer_plain = shown if shown is not None else read_as(value)
        self.answer_latex = shown_latex if shown_latex is not None else latex_of(value)
        self.decimal, decimal_latex = approximate(value, self.answer_plain)
        # ready to show under the answer
        self.decimal_latex = None if decimal_latex is None else rf"\approx {decimal_latex}"
        self.summary = msg("Answer: {answer}", answer=self.answer_plain)
        if self.decimal is not None:
            self.summary += msg(" (about {decimal})", decimal=self.decimal)
        if self.conditions:
            self.summary += msg(", for {conditions}", conditions=", ".join(self.conditions))

    def to_text(self) -> str:
        text = super().to_text()
        others = [method for method in self.methods if method != self.method]
        if others:
            options = ", ".join(f"--method {method}" for method in others)
            text += f"\nAlso try: {options}\n"
        return text

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update(
            {
                "kind": self.kind,
                "kind_label": KIND_LABELS.get(self.kind, "Expression"),
                "method": self.method,
                "methods": [
                    {"id": method, "label": METHOD_LABELS.get(method, method)}
                    for method in self.methods
                ],
                "letters": list(self.letters),
                "variable": None,
                "answers": [self.answer_plain],
                "answers_latex": [self.answer_latex],
                "answer_text": self.summary,
                "answer_latex": self.answer_latex,
                "decimal": self.decimal,
                "decimal_latex": self.decimal_latex,
                "conditions": list(self.conditions),
                "everything": False,
            }
        )
        return data


def approximate(value: sp.Expr, shown: str) -> tuple[str | None, str | None]:
    """A decimal for ``value`` when it says something the exact answer does not."""
    if value is None or value.free_symbols or value.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
        return None, None
    try:
        number = sp.N(value, SIGNIFICANT_DIGITS + 5)
    except (TypeError, ValueError):
        return None, None
    if not number.is_number:
        return None, None
    real, imaginary = number.as_real_imag()
    if abs(imaginary) > 1e-12 * max(1, abs(real)):
        return None, None
    text = format_decimal(float(real))
    if text == shown or text == shown.replace(" ", ""):
        return None, None
    latex = text
    if "e" in text:
        mantissa, exponent = text.split("e")
        latex = rf"{mantissa} \times 10^{{{int(exponent)}}}"
        text = f"{mantissa} * 10^{int(exponent)}"
    return text, latex


def format_decimal(value: float) -> str:
    text = f"{value:.{SIGNIFICANT_DIGITS}g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        return f"{mantissa}e{int(exponent)}"
    return "0" if text == "-0" else text
