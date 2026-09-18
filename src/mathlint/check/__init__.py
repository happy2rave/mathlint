"""Checkers: compare the lines of a solution and build a report."""

from __future__ import annotations

from ..document import Document
from ..report import Report
from .chain import check_chain
from .equation import check_equation
from .matrix import check_matrix
from .system import check_system

__all__ = ["check_document", "check_chain", "check_equation", "check_matrix", "check_system"]


def check_document(document: Document) -> Report:
    """Run the checker that matches the document's mode."""
    if document.mode == "equation":
        return check_equation(document)
    if document.mode == "matrix":
        return check_matrix(document)
    if document.mode == "system":
        return check_system(document)
    return check_chain(document)
