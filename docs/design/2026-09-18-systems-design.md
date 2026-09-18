# v0.6 "Many unknowns" — design

Date: 2026-09-18
Status: approved as part of ROADMAP.md

## Goal

Several equations, several unknowns, solved the way they are taught — with a
choice of method — and every solution substituted back into every equation.

## Input

`mathlint.solve(text)` treats text with more than one equation as a system.
Equations are separated by new lines or `;`, or written as a LaTeX
`\begin{cases} ... \end{cases}`. The unknowns are every letter that appears,
in alphabetical order.

## Result

`SystemSolution` (a `Solution`) with `unknowns`, `method`, `methods`,
`assignments` (one dict per solution) and `free` (the unknowns that can be
anything, when there are infinitely many solutions). `to_dict()` matches the
fields the Solve tab already reads: `kind_label`, `answer_latex`, `answers`,
`methods`, `steps`.

## Linear systems

Written as `A x = b` with `sympy.linear_eq_to_matrix`, fractions cleared first.

| Method | Applies to | Steps |
|---|---|---|
| `elimination` | 2 unknowns, 2 equations | scale the equations so one unknown has equal or opposite coefficients, add or subtract, solve, substitute back |
| `substitution` | 2 unknowns, 2 equations | solve one equation for one unknown (a coefficient of ±1 first), substitute, solve, substitute back |
| `gaussian` | any size | the augmented matrix `[A | b]`, row reduced with every row operation shown, the solution read off |
| `cramer` | square, `det A ≠ 0`, up to 3 unknowns | `D`, then `D_x`, `D_y`, ... with the column replaced, then `x = D_x / D` |
| `inverse` | square, `det A ≠ 0` | `x = A^-1 b` |

Default: elimination for two unknowns, Gaussian elimination otherwise.

No solution: a row `0 = c` (or `0 = c` after eliminating) is explained as
impossible — parallel lines for two unknowns. Infinitely many: the free unknowns
are named and every other unknown is written in terms of them.

## Later in v0.6

Nonlinear systems in two unknowns (#12), "solve for" a chosen letter (#13),
checking your own working on systems (#14), systems on the web page (#15).
