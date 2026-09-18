"""The calculator: arithmetic, simplifying, expanding and factoring, with steps."""

from __future__ import annotations

from . import expand  # noqa: F401 - each module adds its method
from .api import compute
from .computation import Computation

__all__ = ["compute", "Computation"]
