"""What mathlint found, and how to print it."""

from __future__ import annotations

from dataclasses import dataclass, field

from .equivalence import Verdict
from .i18n import msg

_COLORS = {
    Verdict.OK: "\033[32m",
    Verdict.WRONG: "\033[31m",
    Verdict.WARNING: "\033[33m",
    Verdict.UNSURE: "\033[36m",
}
_RESET = "\033[0m"
_METHOD_WORDS = {"exact": msg("proved exactly"), "numeric": msg("checked with numbers")}


@dataclass
class Step:
    """One line of the solution and what mathlint made of it."""

    line: int
    raw: str
    read_as: str
    read_as_latex: str = ""
    verdict: Verdict | None = None
    method: str | None = None
    message: str = ""
    compared_to: int | None = None
    hints: list[str] = field(default_factory=list)
    counterexample: dict[str, str] | None = None
    values: tuple[str, str] | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "raw": self.raw,
            "read_as": self.read_as,
            "read_as_latex": self.read_as_latex,
            "verdict": self.verdict.value if self.verdict else None,
            "method": self.method,
            "message": self.message,
            "compared_to": self.compared_to,
            "hints": list(self.hints),
            "counterexample": self.counterexample,
            "values": list(self.values) if self.values else None,
            "warnings": list(self.warnings),
        }


@dataclass
class Report:
    """The result of checking a whole solution."""

    mode: str
    steps: list[Step]
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no step is wrong (warnings and unsure steps are allowed)."""
        return self.first_error is None

    @property
    def first_error(self) -> Step | None:
        for step in self.steps:
            if step.verdict is Verdict.WRONG:
                return step
        return None

    def to_text(self, color: bool = False) -> str:
        lines: list[str] = []
        for step in self.steps:
            lines.append(f"{step.line:>3}  {step.raw}")
            lines.append(f"     read as: {step.read_as}")
            if step.verdict is not None:
                method = _METHOD_WORDS.get(step.method or "")
                message = f"{step.message} ({method})" if method else step.message
                lines.append(f"     {_paint(step.verdict, color)}  {message}")
            if step.counterexample and step.values and step.compared_to:
                point = _render_point(step.counterexample)
                lines.append(
                    f"     counterexample: {point}  ->  "
                    f"line {step.compared_to} = {step.values[0]}, "
                    f"line {step.line} = {step.values[1]}"
                )
            elif step.values and step.compared_to:
                lines.append(
                    f"     line {step.compared_to} = {step.values[0]}, "
                    f"line {step.line} = {step.values[1]}"
                )
            for hint in step.hints:
                lines.append(f"     hint: {hint}")
            for warning in step.warnings:
                lines.append(f"     note: {warning}")
            lines.append("")

        error = self.first_error
        if error is not None and error.compared_to is not None:
            lines.append(f"First error: line {error.compared_to} -> {error.line}")
        elif error is not None:
            lines.append(f"First error: line {error.line}")
        else:
            lines.append("No mistakes found.")
        for note in self.notes:
            lines.append(f"note: {note}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        rows = [
            "| Line | Your step | Read as | Verdict | Comment |",
            "| --- | --- | --- | --- | --- |",
        ]
        for step in self.steps:
            comment = step.message
            if step.counterexample and step.values:
                point = _render_point(step.counterexample)
                comment += f" (at {point}: {step.values[0]} vs {step.values[1]})"
            for hint in step.hints:
                comment += f" — {hint}"
            verdict = step.verdict.value if step.verdict else ""
            rows.append(
                f"| {step.line} | `{step.raw}` | `{step.read_as}` | {verdict} | {comment} |"
            )
        if self.notes:
            rows.append("")
            rows.extend(f"- note: {note}" for note in self.notes)
        return "\n".join(rows)

    def to_dict(self) -> dict:
        error = self.first_error
        return {
            "ok": self.ok,
            "mode": self.mode,
            "first_error": error.line if error else None,
            "steps": [step.to_dict() for step in self.steps],
            "notes": list(self.notes),
        }


def _render_point(counterexample: dict[str, str]) -> str:
    return ", ".join(f"{name} = {value}" for name, value in counterexample.items())


def _paint(verdict: Verdict, color: bool) -> str:
    if not color:
        return verdict.value
    return f"{_COLORS[verdict]}{verdict.value}{_RESET}"
