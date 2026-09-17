# mathlint

[![CI](https://github.com/happy2rave/mathlint/actions/workflows/ci.yml/badge.svg)](https://github.com/happy2rave/mathlint/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mathlint.svg)](https://pypi.org/project/mathlint/)
[![Python](https://img.shields.io/pypi/pyversions/mathlint.svg)](https://pypi.org/project/mathlint/)

**A linter for your math.** You write out a solution by hand, mathlint tells you
which step is wrong — and proves it with a counterexample.

Other tools show you *their* solution. mathlint checks *yours*.

**[Try it in your browser](https://happy2rave.github.io/mathlint/)** — nothing to
install, and nothing you type leaves the page.

```console
$ mathlint check solution.txt

  1  d/dx [x^2 sin x]
     read as: Derivative(x^2*sin(x), x)
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

## What it checks

- **Expression chains** — algebra, derivatives (`d/dx`), indefinite integrals
  (equal up to a constant, so `+ C` is handled), definite integrals.
- **Solving equations** — one unknown: it catches solutions you lost (dividing by
  `x`) and solutions that appeared out of nowhere (squaring both sides).
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
pip install mathlint
```

Python 3.10 or newer. The only dependency is [SymPy](https://www.sympy.org).

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

## Linear algebra, step by step

```bash
mathlint steps rref    "[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]"
mathlint steps det     "[[3, 8], [4, 6]]"
mathlint steps inverse "[1 2; 3 4]"
mathlint steps eigen   "[[2, 1], [0, 2]]"
```

Every row operation is written the way you would write it in the margin, and the
entries stay exact — `1/2`, never `0.5`. Add `--format markdown`, `--format latex`
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

Inequalities, several unknowns at once, and multivariable calculus. Step-by-step
derivatives and integrals are coming in v0.3.

## Contributing

Issues and pull requests are welcome. Bug reports about **misread input** are the most valuable kind — if mathlint
reads your line differently than you meant it, that's a bug. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
