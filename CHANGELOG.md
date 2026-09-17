# Changelog

All notable changes are recorded here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/happy2rave/mathlint/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.2.0
[0.1.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.1.0
