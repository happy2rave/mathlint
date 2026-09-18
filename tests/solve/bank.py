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

POLYNOMIAL = [
    ("x^3 - 6x^2 + 11x - 6 = 0", "polynomial", [1, 2, 3]),
    ("x^3 = 4x", "polynomial", [-2, 0, 2]),
    ("x^4 - 5x^2 + 4 = 0", "polynomial", [-2, -1, 1, 2]),
    ("x^3 + x - 2 = 0", "polynomial", [1]),
    ("2x^3 - 3x^2 - 3x + 2 = 0", "polynomial", [-1, sp.Rational(1, 2), 2]),
    ("x^4 = 16", "polynomial", [-2, 2]),
    ("x^3 - 2 = 0", "polynomial", [sp.cbrt(2)]),
    ("x^5 - x = 0", "polynomial", [-1, 0, 1]),
    ("x^6 - 9x^3 + 8 = 0", "polynomial", [1, 2]),
]

RATIONAL = [
    ("1/x + 1/2 = 3/4", "rational", [4]),
    ("x/(x - 1) = 2", "rational", [2]),
    ("(x^2 - 1)/(x - 1) = 3", "rational", [2]),
    ("2/(x + 1) = 1/(x - 1)", "rational", [3]),
    ("x/(x - 2) = 2/(x - 2)", "rational", "none"),
    ("1/(x^2 - 4) = 1/(x - 2)", "rational", [-1]),
    ("x/(x + 1) + 1/(x - 1) = 2/(x^2 - 1)", "rational", "none"),
    ("(x + 3)/x = x - 1", "rational", [-1, 3]),
    (r"\frac{1}{x}=\frac{x}{4}", "rational", [-2, 2]),
]

RADICAL = [
    ("sqrt(x) = 3", "radical", [9]),
    ("sqrt(x + 3) = x - 3", "radical", [6]),
    ("sqrt(2x - 1) + 2 = x", "radical", [5]),
    ("sqrt(x) = -2", "radical", "none"),
    ("sqrt(x + 5) = sqrt(2x + 1)", "radical", [4]),
    ("sqrt(x) + sqrt(x + 5) = 5", "radical", [4]),
    ("x^(1/3) = 2", "radical", [8]),
    (r"\sqrt{x+7}=x+1", "radical", [2]),
]

ABSOLUTE = [
    ("|x - 3| = 5", "absolute", [-2, 8]),
    ("|2x + 1| = 7", "absolute", [-4, 3]),
    ("|x| = -1", "absolute", "none"),
    ("|x - 1| + 2 = 6", "absolute", [-3, 5]),
    ("|x - 2| = |2x + 1|", "absolute", [-3, sp.Rational(1, 3)]),
    ("|x + 1| = 2x", "absolute", [1]),
    ("|x - 4| = 0", "absolute", [4]),
]

BANK = LINEAR + QUADRATIC + POLYNOMIAL + RATIONAL + RADICAL + ABSOLUTE
