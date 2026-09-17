"""Errors raised while reading a solution."""

from __future__ import annotations


class MathlintError(Exception):
    """Base class for every error mathlint raises on purpose."""


class ParseError(MathlintError):
    """The input could not be read.

    ``line`` is the 1-based line number in the solution, when known.
    """

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is None:
            return self.message
        return f"line {self.line}: {self.message}"


class UnsupportedError(MathlintError):
    """The input was understood, but mathlint cannot check it yet."""

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is None:
            return self.message
        return f"line {self.line}: {self.message}"
