# Security

## Reporting

Report a vulnerability through GitHub's private advisory form:
**Security → Report a vulnerability** on this repository. Please do not open a
public issue for anything exploitable.

## What mathlint does with your input

mathlint parses math with SymPy's `parse_expr`, which evaluates Python code.
That is only safe because the input is filtered first, in
`src/mathlint/parse/plain.py`:

- a character whitelist (no quotes, no colons, no brackets beyond `()`),
- no `__`, and no attribute access (a dot followed by a letter),
- 2000 characters per line,
- names resolve in a fixed dictionary of SymPy functions, with `__builtins__`
  emptied,
- literal powers above 10 000 and factorials above 1000 are refused, so a line
  cannot lock up the process with a number no one asked for.

Treat this as defence in depth, not a sandbox. If you run mathlint on input
from strangers — a web service, a bot — run it in a separate process with a
time limit, and keep your SymPy up to date.

The web page runs entirely in the visitor's browser through Pyodide. Nothing
that is typed leaves the page: there is no server, no analytics and no logging.
The solution is kept in the page's URL fragment so a link can be shared, and
fragments are not sent to the host.
