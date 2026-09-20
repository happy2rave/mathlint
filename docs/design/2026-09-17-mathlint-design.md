# mathlint — design

Date: 2026-09-17
Status: approved (v0.1–v0.3 scope)

## 1. Purpose

`mathlint` is "a linter for your math". Students type their own worked solution
line by line; mathlint finds the **first wrong step** and proves it with a
counterexample. Later versions also show step-by-step solutions.

Existing tools (Symbolab, Wolfram) show *their* steps and are closed source.
SymPy has the math but no student-facing checker. mathlint fills that gap.

## 2. Releases

| Version | Feature |
|---------|---------|
| v0.1 | Mistake finder: expression chains (incl. `d/dx`, indefinite/definite integrals), single-variable equation solving, plain text + LaTeX input, CLI, Python API, web page |
| v0.2 | Linear algebra steps: RREF, determinant, inverse, eigenvalues/eigenvectors with exact fractions; matrix chains (`~` row-equivalent) in the checker; web tab |
| v0.3 | Calculus steps: derivatives with named rules, integrals via SymPy's manual integration rules, definite integrals; web tab |

Every release: CHANGELOG entry, git tag, GitHub Release with wheel + sdist,
web page redeployed.

## 3. Architecture

```
src/mathlint/
  _version.py
  __init__.py        public API: check(), steps (v0.2+)
  errors.py          ParseError, UnsupportedError
  parse/
    unicode.py       unicode math (−, ·, ², √, π, ∫, λ) -> ascii
    latex.py         LaTeX subset -> plain text (own converter, no guessing)
    plain.py         plain text -> SymPy (safe parse_expr wrapper)
    calculus.py      d/dx ..., int ... dx  ->  Derivative(...), Integral(...)
  document.py        split input into lines, detect mode, parse each line
  numeric.py         sample points, safe numeric evaluation
  equivalence.py     compare two expressions -> Verdict + evidence
  hints.py           sign flip / missing term / constant factor hints
  check/
    chain.py         expression-chain checker
    equation.py      equation-solving checker
  report.py          Report/Step dataclasses -> text / markdown / json
  cli.py             `mathlint check`, `mathlint steps` (v0.2+)
web/                 static page (Pyodide + KaTeX from jsDelivr)
tests/
```

Data flow: text → lines → parsed lines (each echoes "read as") → checker compares
each line with the previous → `Report` → renderer.

## 4. Input format (check)

* Blank lines and lines starting with `#` are ignored.
* **Line 1 is the task.**
  * An expression (may contain `d/dx`, `int ... dx`) → **chain mode**.
    Following lines are expressions, optionally starting with `=`.
  * An equation `lhs = rhs` (optionally prefixed with `solve`) → **equation mode**.
    Following lines are equations or solution lists: `x = 2 or x = 3`,
    `x = 2, x = 3`, `x = ±2`, `no solution`. Lines may start with `=>`, `⇒`,
    `\Rightarrow`, `\implies`, `<=>`, `⇔`, `\iff`.
* A line containing a backslash is LaTeX; otherwise plain text.

### Plain text
`2x sin x + x^2 cos x`, `e^x`, `ln|x|`, `sqrt(x)`, `sin^2(x)`, `pi`, implicit
multiplication. `e` is Euler's number, `C` is a symbol (integration constant),
`i` is a plain symbol. `1/2x` is read as `x/2` and produces a warning.

### Calculus notation
* `d/dx expr` / `\frac{d}{dx} expr`: applies to the bracketed group right after
  it, otherwise to the rest of the line.
* `int f dx`, `∫ f dx`, `int_a^b f dx`, `\int_{a}^{b} f \, dx`: the integrand is
  everything up to the matching `d<var>`.

### LaTeX subset
`\frac \dfrac \tfrac \sqrt \sqrt[n] \left \right \cdot \times \div`, `{}` groups,
`\sin \cos \tan \cot \sec \csc \arcsin \arccos \arctan \sinh \cosh \tanh \ln \log \exp`
(argument without parentheses = following factors up to `+ - =` or the next
function), `\sin^2 x`, `\pi \infty \pm`, `|x|`, spacing commands. Anything else
raises `ParseError` naming the unsupported command. Never guess.

### Safety
`parse_expr` uses `eval`. Before parsing: character whitelist, no `__`, no
attribute access, max 2000 characters per line; globals are a fixed dictionary
with `__builtins__` emptied. After parsing: reject integer power towers with
literal exponents > 10 000.

## 5. Verdicts

`OK`, `WRONG`, `WARNING`, `UNSURE`. `WRONG` requires evidence (a counterexample
or a lost solution). Each step also records `method` (`exact` or `numeric`).

### Chain mode
For consecutive expressions `a`, `b`:

1. Evaluate derivatives (`doit(integrals=False)`); definite integrals are
   evaluated (symbolically, numerically if needed).
2. If any line has an indefinite integral, compare `d/dvar (a - b)` with 0
   instead (equality up to a constant; `C` allowed).
3. Numeric test first: nice points (1, 2, 3, −1, −2, 1/2, …) then seeded random
   points; evaluate at 30 digits; skip points where a side is non-real/undefined.
   A difference beyond relative tolerance 1e-10 → candidate counterexample.
4. On disagreement: if all positive points agree → `WARNING` "only true for
   positive values"; otherwise `WRONG` with the nicest counterexample and hints.
5. On agreement: try `simplify(a - b) == 0` → `OK (exact)`; else `OK (numeric)`.
6. No usable points and no exact proof → `UNSURE`.

Final line: still contains an unevaluated derivative/integral → `WARNING`
"not finished"; indefinite integral answer without `C` → `WARNING` "add + C".

Hints on `WRONG`: whole sign flipped (`a + b = 0`); a term's sign flipped; a term
missing/added; off by a constant; off by a constant factor.

### Equation mode
One unknown. Solution sets over the reals via `solveset`.

* Solutions lost vs previous line → `WRONG` ("lost x = 0 — did you divide by x?").
* Extra solutions vs previous line → `WARNING` (allowed with `=>`, `WRONG` with `<=>`).
* Final solutions not satisfying line 1 → `WRONG`.
* Sets that cannot be compared → `UNSURE`.

## 6. Output

* Python: `check(text) -> Report`; `Report.ok`, `.first_error`, `.steps`,
  `.to_text(color=False)`, `.to_markdown()`, `.to_dict()`.
* CLI: `mathlint check FILE|-` with `--format text|markdown|json`, `--no-color`
  (also honours `NO_COLOR`). Exit codes: 0 no errors, 1 a `WRONG` step,
  2 input/usage error.
* Every step shows the original line, "read as" (SymPy string with `^`), verdict,
  message, hints, counterexample.

## 7. Web page

Static `web/` folder deployed to GitHub Pages by Actions. Loads Pyodide
(v314.0.7, SymPy 1.14) and KaTeX from jsDelivr, installs the mathlint wheel built
in CI. Textarea, examples menu, Check button, results with KaTeX-rendered
"read as", shareable link (input stored in the URL hash, never sent to a server),
loading indicator. v0.2/v0.3 add tabs.

## 8. v0.2 linear algebra steps

`mathlint steps rref|det|inverse|eigen MATRIX`. Matrix input: `[[1,2],[3,4]]`,
MATLAB style `[1 2; 3 4]`, LaTeX `pmatrix/bmatrix`. Exact rationals.

* rref: Gauss–Jordan; each op recorded (`R1 <-> R2`, `R2 -> R2 - 3 R1`, `R1 -> 1/2 R1`).
* det: 2×2 formula; larger via row reduction with sign/scale bookkeeping.
* inverse: Gauss–Jordan on `[A | I]`; singular → explain.
* eigen: characteristic polynomial, factorisation, roots with multiplicity,
  eigenvectors from rref of `A − λI`.
* Checker: lines that are matrices; `~` = row-equivalent (same RREF), `=` = equal.
* Output: text, markdown, latex, json.

## 9. v0.3 calculus steps

`mathlint steps diff EXPR [--var x]`, `mathlint steps integrate EXPR [--from a --to b]`.

* diff: own rule engine — constant, power, constant multiple, sum, product,
  quotient, chain, exp/log/trig/inverse trig, general `a^x`; logarithmic
  differentiation for `f(x)^g(x)`. Each step names the rule and why it applies.
* integrate: `sympy.integrals.manualintegrate.integral_steps` mapped to
  explanations; unknown rule → generic text; no method → say so.
* definite: antiderivative steps, then `F(b) − F(a)`.

## 10. Quality

TDD with pytest; ruff. CI on Linux/Windows/macOS, Python 3.10–3.14. Release
workflow builds sdist + wheel and attaches them to the GitHub Release; optional
PyPI trusted-publishing job (enabled once the maintainer registers the project
on PyPI). Community files: README, LICENSE, CHANGELOG, CONTRIBUTING, SECURITY,
and issue templates (including "mathlint misread my input"). The initial
releases used MIT; current licensing is documented in the repository README.

## 11. Out of scope (for now)

Inequalities, systems of nonlinear equations, multivariable calculus steps,
handwriting/OCR, step explanations in languages other than English.
