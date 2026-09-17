# Contributing to mathlint

Thanks for taking a look. The most useful contribution is small and concrete:
**a line of math that mathlint read wrong.**

## The bug that matters most

mathlint's promise is that it never calls a correct step wrong. So if it:

- marks a correct step as `WRONG`, or
- reads your line as something you did not write (check the `read as:` line), or
- refuses input that is ordinary math,

please open an issue with the exact text you typed. That is a real bug, even if
the notation is unusual.

## Getting set up

```bash
git clone https://github.com/happy2rave/mathlint
cd mathlint
uv sync          # or: python -m venv .venv && pip install -e . pytest ruff
uv run pytest
uv run ruff check .
```

The web page:

```bash
uv run python scripts/build_web.py
python -m http.server -d _site 8123
```

## How the code is laid out

| Path | Job |
|---|---|
| `src/mathlint/parse/` | text (typed or LaTeX) → SymPy, and nothing silent |
| `src/mathlint/document.py` | split a solution into lines, decide chain vs equation |
| `src/mathlint/equivalence.py` | decide `OK` / `WRONG` / `WARNING` / `UNSURE` |
| `src/mathlint/hints.py` | describe the kind of slip, never the verdict |
| `src/mathlint/check/` | walk the lines and build the report |
| `src/mathlint/report.py` | text, Markdown and JSON output |
| `web/` | the browser version (Pyodide) |

## House rules

1. **Tests first.** A parser change comes with the input that broke it.
2. **Never guess.** If the parser cannot read something, raise `ParseError` with
   a message naming what it did not understand. Silent misreads are the one
   failure this project cannot afford.
3. **Evidence before verdicts.** `WRONG` needs a counterexample or a lost
   solution. If you are unsure, the verdict is `UNSURE`.
4. **Plain words.** Messages are read by students, not by compilers.
5. Keep `ruff check` clean; line length is 100.

## Adding notation

Most requests come down to "let me write it this way". That usually means:

- typed notation → `src/mathlint/parse/plain.py` or `parse/calculus.py`
- LaTeX → `src/mathlint/parse/latex.py` (add the command to the supported set)
- a unicode character people paste → `src/mathlint/parse/unicode_math.py`

Add the case to the matching test file first, watch it fail, then make it pass.
