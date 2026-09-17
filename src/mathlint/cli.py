"""The ``mathlint`` command."""

from __future__ import annotations

import argparse
import json
import os
import sys

from ._version import __version__
from .check import check_document
from .document import parse_document
from .errors import MathlintError

EXIT_OK = 0
EXIT_FOUND_ERROR = 1
EXIT_BAD_INPUT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathlint",
        description="Find the first wrong step in a worked solution.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="check a written solution")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.file)
    except OSError as error:
        print(f"mathlint: cannot read {args.file}: {error.strerror}", file=sys.stderr)
        return EXIT_BAD_INPUT

    try:
        report = check_document(parse_document(text))
    except MathlintError as error:
        print(f"mathlint: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif args.format == "markdown":
        print(report.to_markdown())
    else:
        print(report.to_text(color=_use_color(args.no_color)))

    return EXIT_OK if report.ok else EXIT_FOUND_ERROR


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
