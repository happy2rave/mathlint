"""Whether the notebook can read a line: the filter beam search puts candidates through.

It is mathlint's own check (``mathlint.readable``), the same one the page uses.
"""

from mathlint.readable import readable as reads

__all__ = ["reads"]
