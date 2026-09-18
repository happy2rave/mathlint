# Changelog

All notable changes are recorded here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Towards v0.6, "Many unknowns".

### Added

- Systems of linear equations — one per line, separated by `;`, or a LaTeX
  `cases` block — solved by elimination, substitution, Gaussian elimination,
  Cramer's rule or the inverse matrix, and checked in every equation. A system
  with no solution says why; one with infinitely many names its free unknowns.
- Solving a formula for a chosen letter: `variable="t"`, `... for t`, or
  `mathlint solve --for t`. Dividing by a letter comes with the reminder that
  it must not be 0.
- The Solve tab takes several equations (Add an equation), asks which letter
  to solve a formula for when there is no x, and has "Solve for" chips.

## [0.5.0] — 2026-09-18

Solve it: type an equation, get the answer and the steps.

### Added

- `mathlint.solve(text, method=None)` and `mathlint solve EQUATION` — one
  equation in one unknown, solved with the steps a teacher would write:
  - linear equations: expand, clear fractions, collect the unknown, divide;
  - quadratics with four methods to choose from: factoring, the quadratic
    formula, completing the square, square roots;
  - higher powers: common factors, substitution, the rational root theorem and
    synthetic division, with approximate roots said to be approximate;
  - rational equations: excluded values first, then the common denominator;
  - radical equations: isolate and square, as many rounds as needed;
  - absolute values: split into two cases;
  - exponentials: the same base, logarithms, or substitution;
  - logarithms: the domain, combining logarithms, undoing the logarithm.
- Every answer is substituted back into the original equation as the last step;
  answers that divide by zero or leave the domain are rejected with the reason.
- A **Solve** tab, now the first thing on the web page: the answer first, chips
  to switch the method, then the steps.
- The math engine runs in a Web Worker, so the page never freezes; every request
  has a 20 second limit and a Stop button.
- A problem bank of equations with known answers runs with every test.

### Changed

- Expressions print as a student writes them: `|x|` instead of `Abs(x)`, `ln`
  instead of `log`, `e^2` instead of `exp(2)`.

## [0.4.0] — 2026-09-18

Math that looks like math while you write it.

### Added

- The web page's sheet is now a math editor (MathLive): every line is typeset as
  you type — fractions stack, powers rise, roots, derivatives, integrals and
  matrices look the way they do on paper.
- A calculator-style keypad in the spirit of Photomath, with 123, f(x), calculus
  and abc tabs. Keys insert whole structures (a fraction with two boxes, an
  integral with its `dx`) and the cursor lands in the first empty box. The same
  keypad drives the step-by-step tab, including the limits of an integral.
- Enter starts a new line and Backspace on an empty line removes it. Typing still
  works: `/` makes a fraction, `^` a power, `sqrt`, `sin`, `pi`, `int` become
  symbols. "Type as text" switches back to the plain text box, and converts both
  ways.
- mathlint reads the LaTeX the editor writes: `\differentialD`, `\exponentialE`,
  `\lvert`/`\rvert`, `\mleft`/`\mright`, `\lbrace`/`\rbrace`, `\lor`, `\sim`
  between row-reduction steps, and `\text{ or }` between solutions.
- An empty box left in a formula is reported as "there is an empty box on this
  line" instead of a parse error.

### Fixed

- After a release, browsers could keep running the previous version of the web
  page from their cache. The page's own files are now loaded with a version
  stamp.

## [0.3.0] — 2026-09-17

Calculus, worked out.

### Added

- `mathlint steps diff EXPR` — derivatives with the rule named at every step:
  product, quotient, chain, power, exponential, and logarithmic differentiation
  when the variable is in the base and the exponent.
- `mathlint steps integrate EXPR [--from A --to B]` — integrals explained through
  SymPy's by-hand rules: substitution, parts, cyclic parts, rewriting, partial
  fractions, and the standard forms. Definite integrals show F(b) - F(a).
- `--var` to choose the variable; with one unknown in the expression it is picked
  automatically.
- Derivatives and integrals on the web page, next to the linear algebra.

### Changed

- Expressions are printed the way they are written by hand: `d/dx [x^2]` instead
  of `Derivative(x**2, x)`, and `int f dx` instead of `Integral(f, x)`. This shows
  up in the `read as:` line of every report.
- Worked solutions print in plain ASCII, so a legacy Windows console cannot mangle
  them.

## [0.2.0] — 2026-09-17

Linear algebra.

### Added

- `mathlint steps rref|det|inverse|eigen MATRIX` — worked solutions with every
  row operation written out and every entry kept as an exact fraction. Output as
  text, Markdown, LaTeX or JSON.
- Matrices as input anywhere: `[[1,2],[3,4]]`, MATLAB style `[1 2; 3 4]`, and
  LaTeX `pmatrix`/`bmatrix`.
- Checking a row reduction: put your matrices one per line with `~` between them.
  mathlint solves for the coefficients that turn one matrix into the next, so it
  reports the operation you performed, catches rows that are not combinations of
  the rows above, steps that cannot be undone, and rows that only work out
  through an operation nobody would write on purpose.
- A second tab on the web page for the worked solutions.

### Fixed

- The command now prints reports as UTF-8 on terminals that would otherwise
  mangle the dashes.

## [0.1.0] — 2026-09-17

First release: the mistake finder.

### Added

- `mathlint.check(text)` — check a written solution and get a report back.
- Expression chains: algebra, `d/dx`, definite integrals, and indefinite
  integrals compared up to a constant so `+ C` is handled.
- Equation solving with one unknown: lost solutions are errors, gained
  solutions are warnings, and the final answer is checked against the original
  equation.
- Verdicts `OK`, `WRONG`, `WARNING` and `UNSURE`. A step is only `WRONG` when a
  concrete value makes the two lines differ, and that value is shown.
- Hints for common slips: a flipped sign, a lost term, a constant factor.
- Input as typed text (`2x sin x`, `e^x`, `ln|x|`, `sin^2 x`, `int f dx`) or as
  a documented subset of LaTeX. Every line is echoed back as it was understood.
- `mathlint check` command with text, Markdown and JSON output, and exit code 1
  when a step is wrong.
- A web page that runs SymPy and mathlint in the browser through Pyodide.

[Unreleased]: https://github.com/happy2rave/mathlint/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.5.0
[0.4.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.4.0
[0.3.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.3.0
[0.2.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.2.0
[0.1.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.1.0
