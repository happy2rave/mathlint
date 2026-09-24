"""Why each step is allowed: the rule, a tiny example, and the usual mistake.

A step is matched by the words it starts with or contains, so a new solver that
writes its steps the way the others do gets its explanations for free. When a
step has no specialised match, it receives a verification explanation so the
interface can still answer "Why?" without inventing a classroom rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .i18n import msg


@dataclass(frozen=True)
class Why:
    rule: str
    example: str
    mistake: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "example": self.example, "mistake": self.mistake}


_TABLE: list[tuple[str, Why]] = [
    # --- arithmetic ------------------------------------------------------------------
    (
        r"^(Multiply|Divide|Add|Subtract|Add and subtract)",
        Why(
            msg(
                "Order of operations: brackets first, then powers and roots, "
                "then multiply and divide from left to right, then add and "
                "subtract from left to right."
            ),
            msg("2 + 3*4 = 2 + 12 = 14, and 12 : 3 * 2 = 4 * 2 = 8."),
            msg("Working strictly left to right: 2 + 3*4 is not 5*4 = 20."),
        ),
    ),
    (
        r"common denominator",
        Why(
            msg(
                "Fractions can only be added when they count the same size "
                "of piece: rewrite each over a common denominator, "
                "multiplying top and bottom by the same number."
            ),
            "1/2 + 1/3 = 3/6 + 2/6 = 5/6.",
            msg("Adding tops and bottoms: 1/2 + 1/3 is not 2/5."),
        ),
    ),
    (
        r"denominators are the same",
        Why(
            msg(
                "With equal denominators, add or subtract the numerators and keep the denominator."
            ),
            "3/7 + 2/7 = 5/7.",
            msg("Adding the denominators too: 3/7 + 2/7 is not 5/14."),
        ),
    ),
    (
        r"^Reduce the fraction|^Divide: \d",
        Why(
            msg("Dividing the top and the bottom by the same number does not change a fraction."),
            "6/8 = (6 : 2)/(8 : 2) = 3/4.",
            msg("Subtracting instead of dividing: 6/8 is not (6 - 2)/(8 - 2) = 4/6."),
        ),
    ),
    (
        r"numerators, and multiply the denominators|whole number by the numerator",
        Why(
            msg(
                "To multiply fractions, multiply top by top and bottom by "
                "bottom; a whole number n is n/1."
            ),
            msg("2/3 * 3/4 = 6/12 = 1/2, and 2 * 3/4 = 6/4 = 3/2."),
            msg("Finding a common denominator first: that is for adding, not multiplying."),
        ),
    ),
    (
        r"reciprocal|flipped over|flip",
        Why(
            msg("Dividing by a fraction is multiplying by it upside down (its reciprocal)."),
            "3/4 : 2/5 = 3/4 * 5/2 = 15/8.",
            msg("Flipping the first fraction instead of the second."),
        ),
    ),
    (
        r"negative exponent",
        Why(
            msg("A negative exponent means one over the positive power: a^-n = 1/a^n."),
            "2^-3 = 1/2^3 = 1/8.",
            msg("Making the answer negative: 2^-3 is not -8."),
        ),
    ),
    (
        r"power 0 is 1",
        Why(
            msg("Any number except 0 to the power 0 is 1, because a^n / a^n = a^0 = 1."),
            "7^0 = 1, (-3)^0 = 1.",
            msg("Answering 0: 7^0 is 1, not 0."),
        ),
    ),
    (
        r"^A power of \d+/\d+|is the (square|cube|\d+th) root",
        Why(
            msg(
                "A fractional exponent is a root: a^(1/n) is the n-th root "
                "of a, and a^(m/n) is that root to the power m."
            ),
            msg("8^(2/3) = (cube root of 8)^2 = 2^2 = 4."),
            msg("Multiplying by the fraction: 8^(2/3) is not 8 * 2/3."),
        ),
    ),
    (
        r"^Take out the factor",
        Why(
            msg("sqrt(ab) = sqrt(a) sqrt(b), so a perfect-square factor can come out of the root."),
            msg("sqrt(72) = sqrt(36 * 2) = 6 sqrt(2)."),
            msg(
                "Taking out a factor that is not a perfect square: sqrt(72) "
                "is not 2 sqrt(18) in simplest form, because 18 still has "
                "the square 9 in it."
            ),
        ),
    ),
    (
        r"percentage",
        Why(
            msg("Per cent means per hundred: p% = p/100."),
            "20% of 150 = 0.2 * 150 = 30.",
            msg("Dividing by 10 instead of 100: 20% is 0.2, not 2."),
        ),
    ),
    (
        r"Rationalise the denominator",
        Why(
            msg(
                "Multiplying the top and the bottom by the same root clears "
                "the root from the bottom, and does not change the value."
            ),
            msg("1/sqrt(2) = sqrt(2)/2."),
            msg("Multiplying only the bottom, which changes the value."),
        ),
    ),
    # --- expanding and factoring ---------------------------------------------------
    (
        r"\(a \+ b\)\^2|\(a - b\)\^2",
        Why(
            msg(
                "(a + b)^2 = (a + b)(a + b) = a^2 + 2ab + b^2; with a minus, "
                "the middle term is -2ab."
            ),
            "(x + 3)^2 = x^2 + 6x + 9.",
            msg("Forgetting the middle term: (x + 3)^2 is not x^2 + 9."),
        ),
    ),
    (
        r"\(a \+ b\)\(a - b\)|Difference of squares",
        Why(
            msg(
                "(a + b)(a - b) = a^2 - b^2, because the middle terms +ab "
                "and -ab cancel. Read backwards, it factors a difference of "
                "two squares."
            ),
            "x^2 - 9 = (x - 3)(x + 3).",
            msg("Trying the same with a sum: x^2 + 9 does not factor this way."),
        ),
    ),
    (
        r"Multiply every term in the first bracket",
        Why(
            msg(
                "Every term of the first bracket multiplies every term of "
                "the second (FOIL: first, outer, inner, last for two terms "
                "each)."
            ),
            "(x + 1)(x + 2) = x^2 + 2x + x + 2 = x^2 + 3x + 2.",
            msg(
                "Multiplying only first with first and last with last: (x + "
                "1)(x + 2) is not x^2 + 2."
            ),
        ),
    ),
    (
        r"^Multiply each term in the bracket|minus sign in front of a bracket",
        Why(
            msg(
                "Distributive law: a(b + c) = ab + ac. A minus in front "
                "multiplies every term by -1."
            ),
            msg("3(x - 1) = 3x - 3, and -(x - 3) = -x + 3."),
            msg("Multiplying only the first term: 3(x - 1) is not 3x - 1."),
        ),
    ),
    (
        r"^Collect like terms|Add the numbers",
        Why(
            msg("Like terms have the same letters to the same powers; add their numbers in front."),
            msg("2x + 3x = 5x, but 2x + 3x^2 stays as it is."),
            msg("Adding unlike terms: x + x^2 is not 2x^3."),
        ),
    ),
    (
        r"^Take out the common factor|Take out a minus sign",
        Why(
            msg(
                "The distributive law read backwards: a number or letter in "
                "every term can be written once, in front of a bracket."
            ),
            "6x^2 + 9x = 3x(2x + 3).",
            msg("Leaving something out of the bracket: check by multiplying back out."),
        ),
    ),
    (
        r"Perfect square",
        Why(
            msg(
                "a^2 + 2ab + b^2 = (a + b)^2: first and last terms are "
                "squares and the middle is twice their product."
            ),
            "x^2 - 6x + 9 = (x - 3)^2.",
            msg("Using it when the middle term is not 2ab: x^2 + 5x + 9 is not a perfect square."),
        ),
    ),
    (
        r"two numbers that multiply|two terms that multiply",
        Why(
            msg(
                "(x + m)(x + n) = x^2 + (m + n)x + mn, so to factor x^2 + bx "
                "+ c, find m and n with m + n = b and mn = c."
            ),
            msg("x^2 + 5x + 6: 2 + 3 = 5 and 2 * 3 = 6, so (x + 2)(x + 3)."),
            msg("Getting a sign wrong: x^2 - x - 6 is (x - 3)(x + 2), not (x + 3)(x - 2)."),
        ),
    ),
    (
        r"Split the middle term|common factor of each pair|common bracket|Group the terms",
        Why(
            msg(
                "Grouping: split the terms into pairs, take a common factor "
                "out of each pair, and the brackets left over match."
            ),
            "2x^2 + 5x + 3 = 2x^2 + 2x + 3x + 3 = 2x(x + 1) + 3(x + 1) = (x + 1)(2x + 3).",
            msg("Pairs whose brackets do not match: then another split or grouping is needed."),
        ),
    ),
    (
        r"cubes",
        Why(
            msg("a^3 - b^3 = (a - b)(a^2 + ab + b^2) and a^3 + b^3 = (a + b)(a^2 - ab + b^2)."),
            "x^3 - 8 = (x - 2)(x^2 + 2x + 4).",
            msg("Writing (a - b)^3: that is a different expression."),
        ),
    ),
    (
        r"factor theorem",
        Why(
            msg(
                "If p(r) = 0, then (x - r) is a factor of p(x). Rational "
                "roots are among (divisors of the constant)/(divisors of the "
                "leading number)."
            ),
            msg("x^3 - 6x^2 + 11x - 6 is 0 at x = 1, so (x - 1) is a factor."),
            msg("Trying numbers that cannot be roots instead of the divisors."),
        ),
    ),
    # --- simplifying -------------------------------------------------------------------
    (
        r"^Cancel the common factor",
        Why(
            msg(
                "A factor that multiplies the whole top and the whole bottom "
                "can be cancelled — as long as it is not 0, which is why the "
                "excluded values are kept."
            ),
            msg("(x - 2)(x + 2)/(x - 2) = x + 2, for x != 2."),
            msg("Cancelling terms, not factors: (x + 2)/2 is not x + 1 or x."),
        ),
    ),
    (
        r"Combine the logarithms",
        Why(
            "ln(a) + ln(b) = ln(ab), ln(a) - ln(b) = ln(a/b), k ln(a) = ln(a^k).",
            "ln(2) + ln(5) = ln(10).",
            msg("ln(a + b) is not ln(a) + ln(b)."),
        ),
    ),
    (
        r"exponent rules|powers with the same base|power of a power",
        Why(
            "a^m a^n = a^(m+n), a^m / a^n = a^(m-n), (a^m)^n = a^(mn).",
            msg("x^3 x^5 = x^8, and (x^2)^3 = x^6."),
            msg("Multiplying the exponents when multiplying powers: x^3 x^5 is not x^15."),
        ),
    ),
    (
        r"trigonometric identities",
        Why(
            msg("sin^2 x + cos^2 x = 1 (Pythagoras on the unit circle) and tan x = sin x / cos x."),
            msg("sin^2 x + cos^2 x = 1, and tan x cos x = sin x."),
            msg("Writing sin^2 x as sin(x^2)."),
        ),
    ),
    # --- equations -------------------------------------------------------------------
    (
        r"(Subtract|Add) .+ (from|to) both sides",
        Why(
            msg(
                "An equation stays true when the same thing is added to or "
                "subtracted from both sides; it is how a term moves across."
            ),
            msg("2x + 3 = 7: subtract 3 from both sides to get 2x = 4."),
            msg("Changing only one side, or moving a term without changing its sign."),
        ),
    ),
    (
        r"^Divide both sides",
        Why(
            msg(
                "Dividing both sides by the same non-zero number keeps an "
                "equation true. For an inequality, dividing by a negative "
                "number turns the sign around."
            ),
            msg("2x = 4 gives x = 2; -2x < 4 gives x > -2."),
            msg(
                "Dividing by an expression that can be 0 (it can lose a "
                "solution), or keeping the inequality sign when dividing by "
                "a negative number."
            ),
        ),
    ),
    (
        r"product is zero",
        Why(
            msg("If a product is 0, one of its factors is 0 (the zero-product property)."),
            msg("(x - 2)(x - 3) = 0 means x - 2 = 0 or x - 3 = 0."),
            msg(
                "Using it when the other side is not 0: (x - 2)(x - 3) = 6 "
                "does not give x = 8 or 9."
            ),
        ),
    ),
    (
        r"quadratic formula|discriminant",
        Why(
            msg(
                "For ax^2 + bx + c = 0, x = (-b ± sqrt(b^2 - 4ac))/(2a). The "
                "discriminant b^2 - 4ac says how many real solutions there "
                "are."
            ),
            "x^2 - 5x + 6 = 0: x = (5 ± 1)/2, so 3 or 2.",
            msg(
                "Forgetting that -b changes sign when b is negative, or "
                "dividing only part of the top by 2a."
            ),
        ),
    ),
    (
        r"complet(e|ing) the square",
        Why(
            msg(
                "x^2 + bx = (x + b/2)^2 - (b/2)^2: half of b, squared, turns "
                "the start of a quadratic into a perfect square."
            ),
            msg("x^2 + 6x + 5 = 0 becomes (x + 3)^2 = 4."),
            msg("Adding (b/2)^2 to one side only."),
        ),
    ),
    (
        r"[Ss]quare both sides|isolate",
        Why(
            msg(
                "Squaring both sides removes a square root, but it can "
                "create answers that do not work in the original, so every "
                "answer is checked."
            ),
            msg("sqrt(x) = x - 2 gives x = (x - 2)^2, whose root x = 1 does not work."),
            msg("Skipping the check and keeping x = 1."),
        ),
    ),
    (
        r"^Check",
        Why(
            msg(
                "Putting an answer back into the original is the only proof "
                "it works: some steps (squaring, clearing denominators) can "
                "add answers that do not."
            ),
            msg("x = 4 in sqrt(x) = x - 2: 2 = 2, so it works."),
            msg("Checking in a later line instead of the original."),
        ),
    ),
    # --- inequalities --------------------------------------------------------------------
    (
        r"sign chart|change sign where a factor is zero",
        Why(
            msg(
                "A product or quotient can only change sign where one of its "
                "factors is 0 (or a denominator is 0), so one test number "
                "per interval tells the sign everywhere in it."
            ),
            msg("(x - 2)(x - 3) < 0 is negative only between 2 and 3."),
            msg("Multiplying both sides by an expression whose sign is unknown."),
        ),
    ),
    (
        r"absolute value .* means",
        Why(
            msg(
                "|A| is the distance of A from 0: |A| < b means -b < A < b, "
                "and |A| > b means A < -b or A > b."
            ),
            msg("|x - 3| < 2 means 1 < x < 5."),
            msg("Writing |A| > b as -b > A > b, which no number satisfies."),
        ),
    ),
    # --- systems -----------------------------------------------------------------------
    (
        r"[Ee]liminat",
        Why(
            msg(
                "Adding a multiple of one equation to another keeps the "
                "solutions the same; the multiple is chosen so one unknown "
                "disappears."
            ),
            msg("x + y = 5 and x - y = 1: adding gives 2x = 6."),
            msg("Multiplying only one side of an equation."),
        ),
    ),
    (
        r"[Ss]ubstitut.*(from|into) the",
        Why(
            msg("An equation solved for one unknown can replace that unknown everywhere else."),
            msg("y = 5 - x into 2x + y = 8 gives 2x + 5 - x = 8."),
            msg("Substituting back into the same equation it came from."),
        ),
    ),
    # --- calculus ----------------------------------------------------------------------
    (
        r"^Product rule",
        Why(
            "(uv)' = u'v + uv'.",
            msg("(x^2 sin x)' = 2x sin x + x^2 cos x."),
            msg("(uv)' is not u'v'."),
        ),
    ),
    (
        r"^Quotient rule",
        Why(
            "(u/v)' = (u'v - uv')/v^2.",
            "(x/(x + 1))' = ((x + 1) - x)/(x + 1)^2 = 1/(x + 1)^2.",
            msg("Getting the order of the top wrong: it is u'v - uv', not uv' - u'v."),
        ),
    ),
    (
        r"^Chain rule",
        Why(
            msg(
                "(f(g(x)))' = f'(g(x)) g'(x): differentiate the outside, "
                "keep the inside, multiply by the derivative of the inside."
            ),
            msg("(sin(x^2))' = cos(x^2) * 2x."),
            msg("Forgetting to multiply by the inside's derivative."),
        ),
    ),
    (
        r"^Power rule",
        Why(
            msg(
                "(x^n)' = n x^(n-1); and backwards, the integral of x^n is "
                "x^(n+1)/(n+1) for n != -1."
            ),
            msg("(x^3)' = 3x^2; the integral of x^3 is x^4/4."),
            msg("Using it for x^-1: its integral is ln|x|, not x^0/0."),
        ),
    ),
    (
        r"L'Hopital",
        Why(
            msg(
                "For a 0/0 or infinity/infinity limit, lim f/g = lim f'/g' "
                "when the right side exists."
            ),
            msg("lim x->0 sin(x)/x = lim cos(x)/1 = 1."),
            msg(
                "Using the quotient rule instead of differentiating top and "
                "bottom separately, or using it when the limit is not 0/0 or "
                "infinity/infinity."
            ),
        ),
    ),
    (
        r"^Putting x = .* gives 0/0|^Put .* straight in",
        Why(
            msg(
                "Try putting the number in first: for a continuous function "
                "that is the limit. 0/0 means the expression must be "
                "rewritten before it says anything."
            ),
            msg("lim x->3 x^2 + 1 = 10."),
            msg("Reading 0/0 as 0, or as 'does not exist'."),
        ),
    ),
    (
        r"highest power in the bottom",
        Why(
            msg(
                "Dividing the top and the bottom by the same power of x "
                "changes nothing, and every c/x^k goes to 0 at infinity."
            ),
            msg("(3x^2 + 2)/(x^2 - 5) = (3 + 2/x^2)/(1 - 5/x^2), which goes to 3."),
            msg("Dividing only the top."),
        ),
    ),
    (
        r"^Integration by parts",
        Why(
            msg(
                "The integral of u dv is uv minus the integral of v du — the "
                "product rule backwards. Choose u so it gets simpler when "
                "differentiated."
            ),
            msg("The integral of x e^x is x e^x - e^x + C."),
            msg("Choosing u = e^x and dv = x dx, which makes the new integral harder."),
        ),
    ),
    (
        r"^Substitute u =",
        Why(
            msg(
                "Substitution is the chain rule backwards: if the integrand "
                "is f(g(x)) g'(x), put u = g(x) and du = g'(x) dx."
            ),
            msg("The integral of 2x cos(x^2): u = x^2 gives the integral of cos(u) du = sin(x^2)."),
            msg("Forgetting to change dx into du."),
        ),
    ),
    (
        r"simpler fractions|Put x = .*every other term",
        Why(
            msg(
                "A proper fraction with a factored denominator is a sum of "
                "simpler fractions, one for each factor (and each power of a "
                "repeated factor)."
            ),
            "1/(x^2 - 1) = (1/2)/(x - 1) - (1/2)/(x + 1).",
            msg("Skipping polynomial division when the top's degree is not smaller."),
        ),
    ),
    (
        r"has the shape sqrt",
        Why(
            msg(
                "sqrt(a^2 - x^2) with x = a sin t, sqrt(a^2 + x^2) with x = "
                "a tan t, and sqrt(x^2 - a^2) with x = a sec t each become a "
                "single trigonometric function."
            ),
            msg("sqrt(1 - x^2) with x = sin t becomes cos t."),
            msg("Forgetting dx = a cos t dt (or the matching dx)."),
        ),
    ),
    (
        r"add \+ C",
        Why(
            msg(
                "Constants disappear when differentiating, so an "
                "antiderivative is only known up to a constant C."
            ),
            msg("x^2, x^2 + 1 and x^2 - 7 all have derivative 2x."),
            msg("Leaving out + C."),
        ),
    ),
    (
        r"separate the variables",
        Why(
            msg("When y' = g(x) h(y), dy/h(y) = g(x) dx, and integrating both sides solves it."),
            msg("y' = 2y gives dy/y = 2 dx, so ln|y| = 2x + C and y = C e^(2x)."),
            msg("Forgetting the constant, or putting it on both sides as two different constants."),
        ),
    ),
    (
        r"integrating factor",
        Why(
            msg(
                "For y' + P y = Q, multiplying by mu = e^(integral of P) "
                "makes the left side the derivative of mu*y."
            ),
            "y' + y = x: mu = e^x, so (e^x y)' = x e^x.",
            msg("Multiplying only the left side by mu."),
        ),
    ),
    (
        r"characteristic equation",
        Why(
            msg("y = e^(rx) solves a y'' + b y' + c y = 0 exactly when a r^2 + b r + c = 0."),
            "y'' + 3y' + 2y = 0: r = -1, -2, so y = C1 e^(-x) + C2 e^(-2x).",
            msg("For a double root, using C1 e^(rx) + C2 e^(rx) instead of (C1 + C2 x) e^(rx)."),
        ),
    ),
    (
        r"series builds a polynomial",
        Why(
            msg(
                "The Taylor polynomial matches the function's value and "
                "derivatives at the point: the k-th term is f^(k)(a)/k! (x - "
                "a)^k."
            ),
            "e^x = 1 + x + x^2/2! + x^3/3! + ...",
            msg("Forgetting the k! in the denominators."),
        ),
    ),
    (
        r"^Point-slope form",
        Why(
            msg(
                "The line through (x1, y1) with slope m is y - y1 = m(x - "
                "x1); the slope of a tangent is the derivative at the point."
            ),
            msg("y = x^2 at x = 1: slope 2, so y - 1 = 2(x - 1), y = 2x - 1."),
            msg("Using the derivative as a formula (2x) instead of its value at the point (2)."),
        ),
    ),
    (
        r"^Differentiate both sides with respect to x\. y depends on x",
        Why(
            msg(
                "Implicit differentiation: y is a function of x, so by the "
                "chain rule the derivative of y^n is n y^(n-1) y'."
            ),
            msg("x^2 + y^2 = 25 gives 2x + 2y y' = 0, so y' = -x/y."),
            msg("Differentiating y^2 as 2y without the y'."),
        ),
    ),
]

_COMPILED = [(re.compile(pattern), why) for pattern, why in _TABLE]


_START = Why(
    msg("This is the problem exactly as mathlint read it, before doing any work."),
    msg("For 2(x + 3) = 10, the first line stays 2(x + 3) = 10."),
    msg("Starting from a different expression because a sign, bracket, or exponent was misread."),
)

_VERIFIED_TRANSFORMATION = Why(
    msg(
        "This transformation is checked symbolically against the "
        "line before it and the original problem before mathlint "
        "shows it."
    ),
    msg("Expanding (x + 1)^2 to x^2 + 2x + 1 changes its form but not its value."),
    msg(
        "Changing only one term, dropping a restriction, or trusting "
        "a familiar-looking step without checking the whole line."
    ),
)


def why_for(text: str) -> Why:
    """The best available explanation for a step, found by its wording."""
    if text.strip().lower().startswith("start from"):
        return _START
    for pattern, why in _COMPILED:
        if pattern.search(text):
            return why
    return _VERIFIED_TRANSFORMATION
