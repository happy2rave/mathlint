# v0.5 "Solve it" — design

Date: 2026-09-18
Status: approved as part of ROADMAP.md

## Goal

Type one equation in one unknown, get the answer first and the steps after —
the steps a teacher would write, verified by substituting every answer back.

## API

```python
mathlint.solve("x^2 - 5x + 6 = 0", method=None) -> EquationSolution
```

`EquationSolution` extends `Solution` with `kind` (the problem class), `method`,
`methods` (what the method switcher offers), `variable` and `answers`. `to_dict()`
adds `answers`, `answers_latex`, `answer_text`, `kind`, `method`, `methods`.

Errors: no `=` → `ParseError`; more than one unknown → `UnsupportedError`
(systems and "solve for" are v0.6).

## Pipeline

```
text -> Equation(lhs, rhs) -> classify -> solver(kind) -> candidates -> verify -> answers
```

* `solve/core.py` — `Equation`, `Work` (writes equation steps into the solution),
  `Outcome` (`finite` values, `none`, or `all` real numbers).
* `solve/classify.py` — `linear`, `quadratic`, `polynomial`, `rational`,
  `radical`, `absolute`, `exponential`, `logarithmic`, `other`.
* One module per kind. Solvers may call back into the dispatcher for the
  equation they reduce to (rational -> polynomial, radical -> squared equation).
* `solve/verify.py` — substitute each candidate into the *original* equation;
  keep it if both sides agree (exactly, or to 30 digits), otherwise show why it is
  rejected (divides by zero, root of a negative number, the sides differ).
* `solve/fallback.py` — anything else: SymPy's `solveset` over the reals, labelled
  as such.

Answers are real. Complex roots of a quadratic are mentioned in a note.

## Methods

| Kind | Methods | Default |
|---|---|---|
| quadratic | `factoring`, `formula`, `completing-square`, `square-root` | square-root if b = 0, factoring if the roots are rational, otherwise formula |
| exponential | `same-base`, `logarithms` | same-base when both sides are powers of one base |
| everything else | one method | — |

## Web

The engine moves into a module Web Worker (`web/worker.js`); the page talks to it
with promises and restarts it after a 20 second time limit. A new default **Solve**
tab: one math field, the keypad, a Solve button (and keypad ↵), the answer shown
large, method chips, then the steps. Existing tabs stay.

## CLI

`mathlint solve "EQUATION" [--method M] [--format text|markdown|latex|json]`

## Tests

A problem bank (`tests/solve/test_bank.py`): each entry is an equation, its kind
and its real solution set; every entry must be classified correctly, solved with
steps, and verified. Solver-specific tests check the steps name the rule used.

## Commits

1. Engine in a Web Worker with a time limit.
2. Solve API, classifier, verification, fallback, linear equations.
3. Quadratics with four methods.
4. Higher-degree polynomials.
5. Rational equations.
6. Radical and absolute-value equations.
7. Exponential and logarithmic equations.
8. Solve tab on the web page with the method switcher.
9. `mathlint solve`, docs, release v0.5.0.
