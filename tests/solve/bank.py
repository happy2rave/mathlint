"""The problem bank: equations with known answers, grouped by kind.

Each entry is (equation, kind, expected), where expected is a list of the real
solutions, "all" (every real number) or "none". The bank grows with every solver.
"""

import sympy as sp

sqrt, log, E = sp.sqrt, sp.log, sp.E

LINEAR = [
    ("2x + 3 = 7", "linear", [2]),
    ("3(x - 1) = 2x + 5", "linear", [8]),
    ("x/2 + 1/3 = 5/6", "linear", [1]),
    ("5 - x = 2x - 4", "linear", [3]),
    ("7 = 2x + 3", "linear", [2]),
    ("4(2x - 1) - 3(x + 2) = 0", "linear", [2]),
    ("0.5x = 2", "linear", [4]),
    (r"\frac{x}{3}-1=1", "linear", [6]),
    ("2x + 1 = 2x + 1", "linear", "all"),
    ("2x + 1 = 2x + 3", "linear", "none"),
]

BANK = LINEAR
