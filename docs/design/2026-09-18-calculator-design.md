# v0.7 "Calculator" — design

Date: 2026-09-18
Status: approved as part of ROADMAP.md

## Goal

Anything without an `=` sign is worked out with steps: a number is calculated,
an expression is simplified, expanded or factored. The answer shows up while
you type, exact and as a decimal.

## Input

`mathlint.compute(text, method=None)`. `mathlint.solve` sends text without an
`=` here, so the Solve tab and `mathlint solve` take both.

- **Arithmetic** is text with no letters other than function names, `pi`, `e`
  and `of` (`20% of 150`). It is read by a small parser of its own, because the
  steps need what SymPy throws away: `12 ÷ 3 × 2` stays a division then a
  multiplication, `6/8` stays an unreduced fraction, `0.25` stays a decimal.
- **Expressions** (anything with a letter) are read by the usual parser, first
  unevaluated to show them as typed.

## Arithmetic

A tree of numbers (`int`, `frac` with its own numerator and denominator, `dec`,
and `exact` for roots, pi and anything else irrational), sums, products (each
factor multiplied or divided), fractions, powers, function calls, percentages
and factorials.

Each step does the next operation by the order of operations: the innermost
brackets first (a fraction bar, an exponent and a function's argument count as
brackets), then powers and roots, then multiplication and division, then
addition and subtraction, left to right. Integer arithmetic of the same rank is
done in one step (`2·3 + 4·5` → `6 + 20`).

| Operation | Steps |
|---|---|
| fractions added | a common denominator, then add the numerators, then reduce |
| fractions multiplied | multiply the numerators and the denominators, then reduce |
| dividing by a fraction | multiply by its reciprocal |
| decimals with fractions | the decimals written as fractions |
| percentages | `15%` is `0.15` |
| powers | `2^3 = 2·2·2`, negative and fractional exponents rewritten |
| roots | perfect powers, or the largest square factor taken out |
| functions | exact values (`sin(pi/6) = 1/2`) when there is one |

The final value is compared with SymPy's own evaluation of the whole input. If
they ever disagree the steps are dropped and only the verified answer is shown.

## Expressions

Methods, shown as chips like the equation methods:

| Method | Steps |
|---|---|
| `simplify` | like terms, exponent rules, logarithm rules, trigonometric identities, algebraic fractions (factor, cancel, excluded values) |
| `expand` | special products, distributing, multiplying brackets, collecting like terms |
| `factor` | common factor, difference of squares, perfect squares, two numbers that multiply to c and add to b, splitting the middle term, grouping, sums and differences of cubes, the factor theorem |

Every result is checked against the input by expanding the difference.

## Result

`Computation` (a `Solution`) with `kind` (`arithmetic` or `expression`),
`method`, `methods`, `answer`, `answer_latex` and `decimal`. Its `to_dict()` uses
the same fields as an equation's, so the Solve tab draws both the same way.
Equation answers get a `decimal` too.

## On the page

- The Solve tab takes expressions, and its label says so.
- A live answer under the input: after a short pause in typing, the engine
  works out the answer (only the answer) and shows it, or nothing if the input
  is not finished.
- Exact and decimal: the answer card shows both when they differ.
