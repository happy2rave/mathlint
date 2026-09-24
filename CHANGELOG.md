# Changelog

All notable changes are recorded here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.0] — 2026-09-24

Camera and handwriting: photograph a problem, or write it by hand, and it
lands in the notebook as math you can edit — read on the device, offline.

### Added

- **Photograph a problem,** printed or handwritten. The camera button in the
  notebook of Solve and Check fades the app away. Over the live picture only a
  faint outline of the notebook stays, with its ruled lines and red margin,
  plus the capture button. What is inside the outline is split into lines of
  writing and read while the photo dims. The lines are then written into the
  notebook behind a soft pen point; with reduced motion they simply appear.
  **Adjust** reads the same photo with a different crop, and **Choose a photo**
  takes one from the gallery (the way in without a camera).
- **Write it by hand.** The pen button opens one ruled line to write on with a
  finger, a stylus or the mouse. It reads by itself after a pause and shows
  what it read. In Solve the line replaces the one being written; in Check it
  adds the next line of working.
- What is read is never solved or checked before you have seen it. Symbols the
  recognizer was unsure of are named under the notebook ("Check the 3 on
  line 1"). Of the readings it considers, the first one the notebook can read
  is chosen.
- **mathlint's own recognizer:** a small image-to-LaTeX network (3.7 million
  weights, 3.9 MB). It runs in the browser in plain JavaScript, in its own
  thread, with no machine-learning runtime. It is downloaded the first time the
  camera or the pad opens, then kept for offline use; offline before that, the
  page says so. On generated held-out sets it reads 99.8% of printed lines,
  98.4% of handwritten lines and 95.9% of photographed handwritten lines
  exactly. A set of real photos is still to be collected, so the real-world
  rate is not yet measured. About shows how long a photo took to read.
- It learned only from data that may be used commercially: formulas generated
  from the math mathlint solves, typeset in open fonts and written with
  handwritten symbols from Detexify and HASYv2 (Open Database License) and
  handwriting fonts. Everything that trains and exports it is in `training/`.
- Photos and strokes never leave the device and are not kept.

### Changed

- The whole-site budget no longer counts the recognizer, which has budgets of
  its own (the model at most 4 MB, its code at most 60 KB gzipped).
- The red of wrong marks is a shade darker in the light theme, for contrast on
  its tinted background.

## [0.11.0] — 2026-09-24

App quality: your language, offline, your history, and math a screen reader
can read.

### Added

- **Romanian, Russian and Spanish.** The interface and everything the solver
  says — steps, method names, answers, checker verdicts and hints, the **Why?**
  panels, practice labels and error messages — in each language. The language
  follows the browser until one is chosen in About; switching says what is on
  the screen again. Translations are new: the English original is the
  reference, and corrections from native speakers are welcome.
- `mathlint solve`, `steps` and `check` take `--lang ro`, `--lang ru` or
  `--lang es`.
- **Works offline.** Every file of the site, the math engine included, is kept
  on the device after the first visit. A new version installs quietly and the
  page offers **Reload** instead of switching under you. About says when the
  device is ready.
- **Installable.** A web app manifest and icons: add mathlint to a phone's home
  screen and it opens like an app.
- **History and favourites.** Everything you solve, check and work out is kept
  on your device, newest first. Reopen any of it, star the problems you want to
  keep (they are never dropped, and stay when you clear the rest), delete one
  or all.
- **Math in words for screen readers,** in the chosen language: fractions,
  powers, roots, functions, sets, matrices, integrals, limits and derivatives.
  Keypad keys say their symbol, each result is announced once, and the checker's
  margin marks and the graph's points have words. The page passes an axe audit
  on every tab and sheet, at phone and desktop width.
- About shows how long the engine took to start.

### Changed

- The page no longer loads anything from other sites: Pyodide, SymPy, KaTeX,
  MathLive and the fonts are served from the site itself, each download pinned
  by its hash at build time.
- The engine loads less and overlaps more: mathlint's own code downloads while
  SymPy loads and is unpacked straight into Python, so micropip (and the
  packages it needs) are no longer fetched; the other solvers load while you
  read the first answer.
- CI checks performance budgets on every build: the page's own code, the
  stylesheets before the first paint, the size of the whole site and the time
  to import the engine.

## [0.10.1] — 2026-09-22

A new look, built for phones first. The notebook stays; everything around it
is new.

### Changed

- The web page is now an app shell: a top bar with the engine's state, and
  **Solve**, **Check** and **Work out** as tabs at the bottom of a phone or down
  the side of a wide screen. On a wide screen the notebook stays beside its
  results instead of above them.
- The notebook keeps its ruled lines, red margin and numbered lines, now drawn
  as a page with the margin running its full height. Each line has a button to
  remove it, and the keypad's delete key removes an empty line.
- On a phone the keypad docks at the bottom like the phone's own keyboard: it
  rises when you tap a line and steps aside when you are done, and its Enter
  key says what it will do (**Solve**, **Check**, **Go**, or a new line).
- Results are cards: the answer (with the method switcher), the graph with
  zoom buttons on it, the steps as a timeline with a progress bar, and practice
  problems drawn as math in a row you can swipe.
- Checking your working marks every line in the notebook's own margin — ✓, ✗,
  ! or ? — as well as in the report, which opens with the verdict.
- Examples open in a sheet, grouped (equations, systems and formulas,
  calculator, inequalities, calculus) and drawn as math; the open-textbook
  library lives there too. About, the privacy note and support are in their own
  sheet.
- A light and a dark theme, following the system unless one is chosen.
- A shared link to someone's working opens on the Check tab.

### Fixed

- Enter on the keypad inside **Try the next step** checks the attempt instead of
  running the Work out tab.
- A startup failure is shown on the Solve tab as well as on Check.

## [0.10.0] — 2026-09-20

Premium learning features, free and local.

### Added

- A **Why?** control on every worked step: the rule that permits it, a small
  example, and the mistake students most often make. Known classroom rules get
  a specific explanation; other solver transformations explain how they were
  verified instead of inventing a rule.
- Progressive worked solutions in the browser. The first step is visible,
  **Reveal next step** advances with a clear progress count, and **Show all
  steps** remains available.
- **Try the next step** tutor mode. A student can enter any mathematically valid
  next line in the math editor; mathlint checks it and either advances the
  solution or gives the same proof-backed feedback and hint as the checker.
- Newly revealed mathematics is briefly highlighted so the change is easy to
  locate. Animation is disabled when the operating system requests reduced
  motion.
- Three deterministic practice problems matched to the equation, system,
  inequality, calculation, expression method, or calculus skill just solved.
  A practice card loads directly into the solver.
- An attributed open-textbook library with worked solutions for exercises from
  OpenStax's *College Algebra with Corequisite Support 2e* (CC BY 4.0). The
  original exercise and book remain linked, while mathlint generates and
  verifies the working locally.

### Changed

- The README's limitations now reflect the systems, inequalities, graphs, and
  calculus capabilities already shipped.
- Version 0.10.0 and later is source-available under PolyForm Noncommercial
  1.0.0, with separate commercial licensing available from happy2rave. Earlier
  releases retain the license shipped with them.
- The official browser app includes a direct, accessible way to support ongoing
  development through Buy Me a Coffee.

## [0.9.0] — 2026-09-19

Calculus, complete.

### Added

- Limits with steps: `lim x->2 (x^2 - 4)/(x - 2)`, `lim x->0+ 1/x`,
  `lim x->oo ...`, or `\lim_{x\to 2}` from the editor. Putting the number in
  comes first; 0/0 is rewritten by factoring and cancelling, by the conjugate of
  a square root, or by L'Hopital's rule; at infinity the top and bottom are
  divided by the highest power of the bottom; a number over 0 is looked at from
  each side, and a limit whose sides disagree is said not to exist.

- Keys for limits, infinity and the inequality signs on the keypad's calculus
  tab.
- Higher derivatives (`d^2/dx^2 x^3 sin x`) one derivative after the other,
  each with its rules; implicit differentiation (`dy/dx: x^2 + y^2 = 25`) with
  the chain rule's y' named; tangent and normal lines
  (`tangent to y = x^2 at x = 1`) through the point and the slope, in
  point-slope form and solved for y, drawn with the curve on the graph.
- Partial fractions in full: polynomial division when the top is not smaller,
  the bottom factored, the fraction written with unknown numbers on top, the
  numbers found by putting in the roots or by comparing coefficients, and each
  piece integrated, with `ln|x - 1|` rather than `ln(x - 1)`.
- Trigonometric substitution in full for `sqrt(a^2 - x^2)`, `sqrt(a^2 + x^2)`
  and `sqrt(x^2 - a^2)`: the substitution and its `dx`, the integral in theta,
  and the way back to x through the right triangle. Every answer from either
  method is differentiated back before it is shown.

- Differential equations: `y' = 2y`, `dy/dx + 2y = e^x`, `y'' + 3y' + 2y = 0`,
  with initial conditions after a `;` (`y(0) = 1, y'(0) = 0`). First order is
  solved by separating the variables (with `ln|y|`) or with an integrating
  factor; second order with constant coefficients through the characteristic
  equation and its three cases, plus undetermined coefficients when the right
  side is not 0. Initial conditions fix the constants, and a particular
  solution is drawn on the graph. Every answer is put back into the equation.
  Implicit differentiation now needs `dy/dx:` with a colon, since
  `dy/dx = ...` is a differential equation.
- Taylor and Maclaurin series: `taylor ln(x) at 1 order 4`, `maclaurin e^x`.
  The table of derivatives and their values at the point, each term with its
  k!, the polynomial in powers of (x - a) with its O(...) remainder, and the
  general term of the series every course asks you to know. The graph draws
  the function and its polynomial together.
- A definite integral's graph shades the area between the curve and the
  x-axis, above the axis and below it in different colours, with the bounds
  marked.

### Fixed

- Integration steps showed SymPy's internal `_u` for the substituted variable.

### Changed

- Plain-text output writes negative powers as fractions: `1/x^2`, not `x^(-2)`.

## [0.8.0] — 2026-09-19

Inequalities and graphs.

### Added

- Inequalities: `mathlint.solve("3 - 2x < 7")` and the Solve tab take `<`, `<=`,
  `>`, `>=` (and `\le`, `\ge`, `≤`, `≥`). Linear inequalities are solved by the
  balance method; dividing by a negative number says that it turns the sign
  around, swapping sides says the same, and a number on each side of the answer
  is checked. Double inequalities like `1 < 2x + 3 <= 7` are split in two and
  intersected. The answer comes in inequality form (`x > -2`), in interval
  notation (`(-2, inf)`), and as the pieces of a number line.
- Sign charts for polynomial and rational inequalities: everything moved to
  one side (never multiplying by a denominator, whose sign is unknown), a
  negative leading number turned positive by flipping the sign, the side
  factored, and a table with one test number per interval and one row per
  factor. Zeros of a denominator are never part of the answer.
- Absolute-value inequalities: the absolute value on its own, then
  `|A| < b` as `-b < A < b` and `|A| > b` as `A < -b or A > b`; a negative or
  zero bound is explained without any algebra.
- The Solve tab draws the answer of an inequality on a number line — shaded
  intervals, filled circles for ends that belong to the answer, open circles
  for ends that do not, arrows for intervals that go on forever — under the
  answer and its interval notation. Sign charts show as tables. There are
  examples of each kind of inequality.
- A graph under every answer that has one: both sides of an equation with the
  solutions marked where they meet, the left side of an inequality with its
  answer shaded and its ends marked open or closed, each equation of a system
  in x and y (vertical lines too) with the solutions marked, and an expression
  as a function with its zeros. Drag to move, scroll or pinch to zoom, or use
  the buttons and the keyboard; the page asks for fresh points across the new
  range, and curves break at asymptotes instead of joining across them.
- Function analysis: `mathlint.analyze("x^3 - 3x")`, `--method analyze`, or
  "Analyze the function" on the Solve tab. The domain with what restricts it,
  the intercepts, vertical asymptotes (only from the sides the function is
  defined on) and holes, horizontal and oblique asymptotes, where it rises and
  falls with its local maxima and minima, where it bends up or down with its
  inflection points — each with its reason, and each point marked on the
  graph. Periodic functions list their infinitely many zeros; anything SymPy
  cannot settle exactly is said to be left out.

### Fixed

- Plain-text output wrote Euler's number as `E`, which reads back as a letter,
  and `e^(3/2)` as `e^3/2`, which reads back as `(e^3)/2`.

## [0.7.0] — 2026-09-19

Calculator: anything without an equals sign, worked out step by step.

### Added

- `mathlint.compute(text)` — arithmetic worked out one operation at a time, in
  the order of operations: brackets, powers and roots, multiplying and dividing,
  adding and subtracting. Fractions get a common denominator and are reduced;
  dividing by a fraction multiplies by its reciprocal; decimals, percentages
  (`20% of 150`), negative and fractional exponents, square and cube roots
  (`sqrt(72) = 6 sqrt(2)`), factorials, absolute values and exact values such
  as `sin(pi/6)` all have their own steps. The answer stays exact, with a
  decimal next to it, and is checked against SymPy before any step is shown.
- Expanding with steps: the special products `(a + b)^2`, `(a - b)^2`,
  `(a + b)(a - b)` and `(a + b)^3` by name, a number or letter in front of a
  bracket, two brackets term by term, like terms collected inside a bracket
  before it is multiplied out, and at the end. A product like `x^3 x^5` or
  `2x + 3x` is first shown as written, with the rule that tidies it.
- Factoring with steps, in the order a teacher checks: a common factor (or a
  minus sign), a difference of squares, a sum or difference of cubes, a perfect
  square, two numbers that multiply to c and add to b, splitting the middle
  term when x^2 has a number in front, a quadratic in disguise
  (`x^4 - 5x^2 + 4`), grouping in pairs, and the factor theorem for higher
  powers. Every new factor is factored again. A polynomial without brackets is
  factored by default.
- Simplifying with steps. Algebraic fractions are put over a common
  denominator, their numerators added, the top and bottom factored and the
  common factors cancelled, and the answer keeps the values the original was
  not defined for (`x != -2`). Logarithm, exponent, trigonometric and root
  rules each have their own step; anything they miss is simplified last.
  Anything else is simplified by default, and expressions that are already as
  simple as they get say so.
- High powers of a bracket, such as `(x + 1)^10`, are expanded with the
  binomial theorem in one step.
- One input for everything: `mathlint solve`, `mathlint.solve` and the Solve
  tab work out anything without an equals sign instead of refusing it, and
  send `d/dx ...` and `int ... dx` to the derivative and integral steps. The
  Solve tab has examples of each, offers Simplify, Expand and Factor as
  methods, and shows the values an answer must not take.
- Exact answers with a decimal alongside: `x = (1 + sqrt(5))/2` is also about
  1.618033989, and `1/2 + 1/3 = 5/6` about 0.8333333333. Whole numbers are left
  alone. The Solve tab shows the decimal under the answer, and the JSON output
  has `decimal`, `decimal_latex` and, for equations, `answers_decimal`.
- A live answer on the Solve tab: a moment after you stop typing, the answer
  (and its decimal) appears under the input, before you press Solve. Half-typed
  input shows nothing rather than an error, and integrals wait for the button.

## [0.6.0] — 2026-09-18

Many unknowns.

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
- Nonlinear systems in two unknowns: substitution from the equation that is
  linear in one unknown, or u = x^2, v = y^2 when both unknowns only appear
  squared; every pair is checked in both equations.
- Checking your own working on a system: one stage of the system per line,
  equations separated by `;`. A lost solution is an error that names the
  solution and the equation that breaks; extra solutions are a warning.

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

[Unreleased]: https://github.com/happy2rave/mathlint/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.12.0
[0.11.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.11.0
[0.10.1]: https://github.com/happy2rave/mathlint/releases/tag/v0.10.1
[0.10.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.10.0
[0.9.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.9.0
[0.8.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.8.0
[0.7.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.7.0
[0.6.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.6.0
[0.5.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.5.0
[0.4.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.4.0
[0.3.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.3.0
[0.2.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.2.0
[0.1.0]: https://github.com/happy2rave/mathlint/releases/tag/v0.1.0
