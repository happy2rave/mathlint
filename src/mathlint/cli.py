"""The ``mathlint`` command."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys

from ._version import __version__
from .check import check_document
from .document import parse_document
from .errors import MathlintError, UnsupportedError, error_text
from .i18n import LANGUAGES, localize, localized_copy

EXIT_OK = 0
EXIT_FOUND_ERROR = 1
EXIT_BAD_INPUT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathlint",
        description="Find the first wrong step in a worked solution.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    language = argparse.ArgumentParser(add_help=False)
    language.add_argument(
        "--lang",
        choices=LANGUAGES,
        default="en",
        help="the language mathlint explains the math in (default: en)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="check a written solution", parents=[language])
    check.add_argument(
        "file",
        nargs="?",
        default="-",
        help="the solution file, or - to read from standard input",
    )
    check.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="how to print the result (default: text)",
    )
    check.add_argument("--no-color", action="store_true", help="never colour the output")

    steps = subcommands.add_parser(
        "steps", help="show a worked solution, step by step", parents=[language]
    )
    steps.add_argument(
        "operation",
        choices=["rref", "det", "inverse", "eigen", "diff", "integrate"],
        help=("rref, det, inverse or eigen for a matrix; diff or integrate for an expression"),
    )
    steps.add_argument(
        "target",
        help=(
            'the matrix ("[[1,2],[3,4]]", "[1 2; 3 4]", a LaTeX pmatrix) '
            'or the expression ("x^2 sin x")'
        ),
    )
    steps.add_argument(
        "--var",
        help="the variable to work with (default: the one in the expression, else x)",
    )
    steps.add_argument("--from", dest="lower", help="lower limit of a definite integral")
    steps.add_argument("--to", dest="upper", help="upper limit of a definite integral")
    steps.add_argument(
        "--format",
        choices=["text", "markdown", "latex", "json"],
        default="text",
        help="how to print the solution (default: text)",
    )

    solve = subcommands.add_parser(
        "solve",
        help="solve an equation, or work out anything else, step by step",
        parents=[language],
    )
    solve.add_argument(
        "equation",
        help='an equation such as "x^2 - 5x + 6 = 0", or something to work out: '
        '"1/2 + 1/3", "(x + 2)^2", "x^2 - 9", "d/dx x^2 sin x"',
    )
    solve.add_argument(
        "--for",
        dest="variable",
        help="the letter to solve for, when the equation has several (default: x)",
    )
    solve.add_argument(
        "--method",
        help="how to solve it, when there is a choice (for a quadratic: factoring, "
        "formula, completing-square, square-root; for an expression: simplify, expand, "
        "factor)",
    )
    solve.add_argument(
        "--format",
        choices=["text", "markdown", "latex", "json"],
        default="text",
        help="how to print the solution (default: text)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _use_utf8()

    if args.command == "solve":
        return _run_solve(args)
    if args.command == "steps":
        return _run_steps(args)
    return _run_check(args)


def _run_steps(args) -> int:
    try:
        solution = _build_solution(args)
    except MathlintError as error:
        print(f"mathlint: {localize(error_text(error), args.lang)}", file=sys.stderr)
        return EXIT_BAD_INPUT

    _print_solution(solution, args.format, args.lang)
    return EXIT_OK


def _run_solve(args) -> int:
    from .solve import solve

    try:
        solution = solve(args.equation, method=args.method, variable=args.variable)
    except MathlintError as error:
        print(f"mathlint: {localize(error_text(error), args.lang)}", file=sys.stderr)
        return EXIT_BAD_INPUT
    _print_solution(solution, args.format, args.lang)
    return EXIT_OK


def _print_solution(solution, output_format: str, lang: str = "en") -> None:
    if output_format == "json":
        print(json.dumps(localize(solution.to_dict(), lang), indent=2))
        return
    solution = localized_copy(solution, lang)
    if output_format == "markdown":
        print(solution.to_markdown())
    elif output_format == "latex":
        print(solution.to_latex())
    else:
        print(solution.to_text())


def _build_solution(args):

    from .parse.plain import parse_expression
    from .steps import (
        differentiate_solution,
        integrate_solution,
        parse_matrix,
        solve_linalg,
    )

    if args.operation not in ("diff", "integrate"):
        return solve_linalg(args.operation, parse_matrix(args.target))

    expression = parse_expression(args.target).expr
    variable = _pick_variable(expression, args.var)
    if args.operation == "diff":
        return differentiate_solution(expression, variable)

    if (args.lower is None) != (args.upper is None):
        raise UnsupportedError("a definite integral needs both --from and --to")
    lower = parse_expression(args.lower).expr if args.lower else None
    upper = parse_expression(args.upper).expr if args.upper else None
    return integrate_solution(expression, variable, lower=lower, upper=upper)


def _pick_variable(expression, chosen: str | None):
    import sympy as sp

    if chosen:
        return sp.Symbol(chosen)
    symbols = sorted(expression.free_symbols, key=lambda symbol: symbol.name)
    if len(symbols) == 1:
        return symbols[0]
    return sp.Symbol("x")


def _run_check(args) -> int:
    try:
        text = _read_input(args.file)
    except OSError as error:
        print(f"mathlint: cannot read {args.file}: {error.strerror}", file=sys.stderr)
        return EXIT_BAD_INPUT

    try:
        report = check_document(parse_document(text))
    except MathlintError as error:
        print(f"mathlint: {localize(error_text(error), args.lang)}", file=sys.stderr)
        return EXIT_BAD_INPUT

    if args.format == "json":
        print(json.dumps(localize(report.to_dict(), args.lang), indent=2))
    elif args.format == "markdown":
        print(localized_copy(report, args.lang).to_markdown())
    else:
        print(localized_copy(report, args.lang).to_text(color=_use_color(args.no_color)))

    return EXIT_OK if report.ok else EXIT_FOUND_ERROR


def _use_utf8() -> None:
    """Reports contain dashes and arrows; a legacy console would choke on them."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            # depends on the terminal, and a failure here changes nothing important
            with contextlib.suppress(ValueError, OSError):
                stream.reconfigure(encoding="utf-8", errors="replace")


def _read_input(name: str) -> str:
    if name == "-":
        return sys.stdin.read()
    with open(name, encoding="utf-8") as handle:
        return handle.read()


def _use_color(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
