# mathlint

[![CI](https://github.com/happy2rave/mathlint/actions/workflows/ci.yml/badge.svg)](https://github.com/happy2rave/mathlint/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/happy2rave/mathlint)](https://github.com/happy2rave/mathlint/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A linter for your math.** Type an equation and get it solved, step by step —
or write out a solution yourself, and mathlint tells you which step is wrong and
proves it with a counterexample.

Other tools show you *their* solution. mathlint also checks *yours*. It is free,
open source, and runs on your own device. The plan is in [ROADMAP.md](ROADMAP.md).

**[Try it in your browser](https://happy2rave.github.io/mathlint/)** — nothing to
install, and nothing you type leaves the page. You write on a math editor with a
calculator-style keypad, so fractions, powers, roots and integrals look like they
do on paper while you type.

```console
$ mathlint check solution.txt

  1  d/dx [x^2 sin x]
     read as: d/dx [x^2*sin(x)]
  2  = 2x sin x + x^2 cos x
     read as: 2*x*sin(x) + x^2*cos(x)
     OK  equal to line 1 (proved exactly)
  3  = x(2 sin x + x cos x)
     read as: x*(2*sin(x) + x*cos(x))
     OK  equal to line 2 (proved exactly)
  4  = x(2 sin x - x cos x)
     read as: x*(2*sin(x) - x*cos(x))
     WRONG  not equal to line 3
     counterexample: x = 1  ->  line 3 = 2.22324, line 4 = 1.14264
     hint: the sign of x^2*cos(x) flipped

First error: line 3 -> 4
```

## Solve an equation

```console
$ mathlint solve "x^2 - 5x + 6 = 0"
Solve x^2 - 5*x + 6 = 0
=======================

1. Start from
      x^2 - 5*x + 6 = 0

2. Factor: find two numbers that multiply to 6 and add up to -5: -2 and -3
      (x - 3)*(x - 2) = 0

3. A product is zero exactly when one of its factors is zero
      x - 3 = 0 or x - 2 = 0

4. Solve each one
      x = 2 or x = 3

5. Check x = 2: both sides equal 0

6. Check x = 3: both sides equal 0

x = 2 or x = 3

Other ways to solve it: --method formula, --method completing-square
```

One unknown, and the method a teacher would use for each kind of equation:

| Kind | How it is solved |
|---|---|
| Linear | expand, clear fractions, collect the unknown, divide |
| Quadratic | factoring, the quadratic formula, completing the square or square roots — your choice |
| Higher powers | common factors, substitution (`x^4 - 5x^2 + 4 = 0`), the rational root theorem |
| Unknown in a denominator | excluded values first, then multiply by the common denominator |
| Square roots | isolate and square, as many times as needed |
| Absolute values | split into two cases |
| Exponentials | the same base, logarithms, or substitution (`e^(2x) - 3e^x + 2 = 0`) |
| Logarithms | the domain first, combine, undo the logarithm |

Several equations are solved as a system — one per line, or separated by `;` —
by elimination, substitution, Gaussian elimination, Cramer's rule or the inverse
matrix, and a system with no solution or infinitely many says so and why:

```bash
mathlint solve "3x + 2y = 16; 4x - 5y = -17" --method cramer
mathlint solve "x + y = 5; x^2 + y^2 = 13"
```

Systems with squares or products in them are solved by substitution, or by
treating `x^2` and `y^2` as the unknowns when nothing else appears.

A formula with several letters is solved for the one you name, the others
treated as known — and dividing by a letter comes with the reminder that it
must not be 0:

```bash
mathlint solve "v = u + a t" --for t
mathlint solve "1/f = 1/u + 1/v" --for v
```

Every answer is put back into the original equation at the end. Squaring,
clearing denominators and undoing logarithms can all produce answers that do not
really work; those are rejected, with the reason. From Python:

```python
import mathlint

solution = mathlint.solve("sqrt(x + 3) = x - 3")
solution.answers      # [6] - x = 1 was rejected in the check
solution.methods      # the methods that apply; pass method="..." to pick one
```

## Work anything out

Anything without an equals sign is worked out instead of solved, with the same
command and on the same tab of the web page:

```console
$ mathlint solve "1/2 + 1/3"
Calculate 1/2 + 1/3
===================

1. Start from
      1/2 + 1/3

2. Write the fractions over the common denominator 6
      3/6 + 2/6

3. The denominators are the same, so add the numerators
      (3 + 2)/6

4. Add
      5/6

Answer: 5/6 (about 0.8333333333)
```

| Input | What you get |
|---|---|
| Arithmetic | the order of operations one step at a time; fractions, decimals, percentages (`20% of 150`), powers, roots (`sqrt(72) = 6 sqrt(2)`), factorials, exact values like `sin(pi/6)` |
| Brackets, `(2x - 1)(3x + 4)` | expanded: special products by name, bracket by bracket, then like terms |
| A polynomial, `2x^2 + 5x + 3` | factored: common factor, difference of squares, cubes, perfect squares, two numbers that multiply to c and add to b, splitting the middle term, grouping, the factor theorem |
| A fraction, `(x^2 - 4)/(x^2 + x - 2)` | simplified: common denominator, factor, cancel, and the values it must not take (`x != -2`) |
| Logarithms, powers, trigonometry | simplified with the rule named at each step |
| `d/dx ...`, `int ... dx` | the derivative or integral, step by step |

Pick what to do with `--method simplify`, `--method expand` or
`--method factor`. From Python it is `mathlint.compute(text)`; answers are exact,
with a decimal alongside (`result.decimal`) when they differ.

## What it checks

- **Expression chains** — algebra, derivatives (`d/dx`), indefinite integrals
  (equal up to a constant, so `+ C` is handled), definite integrals.
- **Solving equations** — one unknown: it catches solutions you lost (dividing by
  `x`) and solutions that appeared out of nowhere (squaring both sides).
- **Systems** — write each stage of the system on one line, equations separated
  by `;`; a solution that goes missing is caught and named.
- **Row reduction** — write your matrices one per line with `~` between them, and
  mathlint works out which row operation you did and whether it is really one.
- **Input** — typed text (`2x sin x + x^2 cos x`) or LaTeX
  (`2x \sin x + x^2 \cos x`).

## Three promises

1. **It only says WRONG with proof.** First it tests your two lines with actual
   numbers; it calls a step wrong only when it finds a value where the lines
   differ, and it shows you that value. Otherwise it tries to prove the step
   exactly. Verdicts are `OK`, `WRONG`, `WARNING` or `UNSURE` — never a guess
   dressed up as a fact.
2. **It shows how it read every line.** Parsers misread math quietly, so you
   always see what it understood.
3. **Steps that are only sometimes true stay warnings.** `sqrt(x^2) = x` is
   reported as "only true for x ≥ 0", not as an error.

## Install

```bash
pip install "mathlint @ git+https://github.com/happy2rave/mathlint"
```

or install the wheel attached to the
[latest release](https://github.com/happy2rave/mathlint/releases/latest). Python
3.10 or newer; the only dependency is [SymPy](https://www.sympy.org). Nothing to
install at all: [use it in the browser](https://happy2rave.github.io/mathlint/).

## Use it

Write your solution in a text file, one step per line:

```text
d/dx [x^2 sin x]
= 2x sin x + x^2 cos x
= x(2 sin x + x cos x)
```

```bash
mathlint check solution.txt          # readable report
mathlint check - < solution.txt      # read from stdin
mathlint check solution.txt --format json
mathlint check solution.txt --format markdown
```

Exit codes: `0` nothing wrong, `1` a wrong step was found, `2` the input could
not be read. That makes it usable in a script or in CI.

From Python:

```python
import mathlint

report = mathlint.check("(x+1)^2\n= x^2 + 2x + 1")
print(report.ok)            # True
print(report.to_text())
```

## Worked solutions, step by step

```bash
mathlint steps diff      "x^2 sin x"
mathlint steps integrate "x e^x"
mathlint steps integrate "x^2" --from 0 --to 1
mathlint steps rref      "[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]"
mathlint steps det       "[[3, 8], [4, 6]]"
mathlint steps inverse   "[1 2; 3 4]"
mathlint steps eigen     "[[2, 1], [0, 2]]"
```

```console
$ mathlint steps diff "x^2 sin x"

1. Start from
      d/dx [x^2*sin(x)]
2. Product rule: (uv)' = u'v + uv', with u = x^2 and v = sin(x)
3. Power rule: d/dx x^n = n x^(n-1), with n = 2
      2*x
4. Standard derivative: d/dx sin(x) = cos(x)
      cos(x)
5. Put it together and tidy up
      x*(x*cos(x) + 2*sin(x))
```

Derivatives name the rule they use and the `u` and `v` they use it with, rather
than handing you an answer. Integrals explain the method — substitution, parts,
partial fractions — and say plainly when an integrand has no elementary
antiderivative instead of producing a special function without comment. Row
operations are written the way you would write them in the margin, and matrix
entries stay exact: `1/2`, never `0.5`. Add `--format markdown`, `--format latex`
or `--format json` to paste the work somewhere else.

Checking a row reduction you did yourself works the same way as everything else:

```text
[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [-3, -1, 2], [-2, 1, 2]]
~ [[1, 1/2, -1/2], [0, 1/2, 1/2], [0, 2, 1]]
```

```
OK  row operation checks out: R2 -> R2 + (3) R1, R3 -> R3 + (2) R1
```

mathlint solves for the coefficients that turn one matrix into the next, so it
catches a row that is not a combination of the rows above, a step that cannot be
undone, and a row that only works out through an operation nobody would write on
purpose — the fingerprint of an arithmetic slip.

## Writing your solution

| You write | Meaning |
|---|---|
| `2x sin x + x^2 cos x` | implicit multiplication, functions without brackets |
| `e^x`, `ln|x|`, `sqrt(x)`, `pi` | Euler's number, natural log, square root, π |
| `sin^2 x`, `sin^-1 x` | squared sine, arcsine |
| `d/dx expr`, `d/dx(expr)`, `d^2/dx^2 (expr)` | derivatives |
| `int f dx`, `int_0^1 f dx` | integrals (`∫` works too) |
| `x = 2 or x = 3`, `x = ±2`, `no solution` | answers when solving an equation |
| `[[1, 2], [3, 4]]`, `[1 2; 3 4]`, `pmatrix` | matrices; `~` between row reduction steps |
| `=>`, `<=>` at the start of a line | implication / equivalence |
| `# ...` | comment, ignored |

LaTeX works for the same things: `\frac{d}{dx}`, `\int_{0}^{\pi} \sin x \, dx`,
`\frac{1}{2}`, `\sqrt{x^2+1}`, `\left( \right)`, `\cdot`, `\sin^2 x`, `\pi`.
Anything mathlint doesn't support is rejected with a clear message instead of
being guessed at.

## What it does not do yet

Inequalities, several unknowns at once, multivariable calculus, and checking a
derivative or integral you worked out step by step (today it checks the result of
each line, not the rule you named).

## Contributing

Issues and pull requests are welcome. Bug reports about **misread input** are the most valuable kind — if mathlint
reads your line differently than you meant it, that's a bug. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Built on

[SymPy](https://www.sympy.org) for the math; in the browser,
[Pyodide](https://pyodide.org), [MathLive](https://mathlive.io) for the editor and
[KaTeX](https://katex.org) for the results.

## License

MIT
