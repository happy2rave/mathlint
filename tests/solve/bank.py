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

QUADRATIC = [
    ("x^2 - 5x + 6 = 0", "quadratic", [2, 3]),
    ("2x^2 = 8", "quadratic", [-2, 2]),
    ("x^2 + 2x + 5 = 0", "quadratic", "none"),
    ("x^2 - 2x - 1 = 0", "quadratic", [1 - sqrt(2), 1 + sqrt(2)]),
    ("x^2 = 3x", "quadratic", [0, 3]),
    ("(x + 1)^2 = 4", "quadratic", [-3, 1]),
    ("4x^2 - 12x + 9 = 0", "quadratic", [sp.Rational(3, 2)]),
    ("2x^2 + 3x - 2 = 0", "quadratic", [-2, sp.Rational(1, 2)]),
    ("-x^2 + 4 = 0", "quadratic", [-2, 2]),
    ("x^2/2 - x = 4", "quadratic", [-2, 4]),
    ("x^{2}-5x+6=0", "quadratic", [2, 3]),
]

BANK = LINEAR + QUADRATIC
