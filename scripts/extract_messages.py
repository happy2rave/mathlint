"""Keep the translation catalogs in step with the code.

    python scripts/extract_messages.py          # add new templates, drop stale ones
    python scripts/extract_messages.py --check  # exit 1 if a catalog is out of step

Every ``msg("...")`` template in ``src/mathlint`` becomes a key in
``src/mathlint/locales/<lang>.json``. A new key starts as ``null``, which means
"not translated yet"; existing translations are kept.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "mathlint"
LOCALES = PACKAGE / "locales"
LANGUAGES = ("ro", "ru", "es")


def templates() -> tuple[list[str], list[str]]:
    """Every template in the order it appears, and every call that has no literal one."""
    found: dict[str, None] = {}
    problems: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _called(node) == "msg"):
                continue
            first = node.args[0] if node.args else None
            context = next((k.value for k in node.keywords if k.arg == "context"), None)
            if context is not None and not isinstance(context, ast.Constant):
                where = path.relative_to(ROOT).as_posix()
                problems.append(f"{where}:{node.lineno}: msg() needs a literal context")
            elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                prefix = f"{context.value}|" if context is not None else ""
                found.setdefault(prefix + first.value)
            else:
                where = path.relative_to(ROOT).as_posix()
                problems.append(f"{where}:{node.lineno}: msg() needs a literal template")
    return list(found), problems


def _called(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def load(lang: str) -> dict:
    path = LOCALES / f"{lang}.json"
    if not path.exists():
        return {"messages": {}, "latex": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def updated(catalog: dict, keys: list[str]) -> dict:
    old = catalog.get("messages", {})
    return {"messages": {key: old.get(key) for key in keys}, "latex": catalog.get("latex", {})}


def dump(catalog: dict) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    keys, problems = templates()
    for problem in problems:
        print(problem)
    stale = bool(problems)
    for lang in LANGUAGES:
        path = LOCALES / f"{lang}.json"
        text = dump(updated(load(lang), keys))
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if text == current:
            continue
        if check:
            print(f"{path.relative_to(ROOT).as_posix()} is out of step with the code")
            stale = True
        else:
            path.write_text(text, encoding="utf-8")
            print(f"updated {path.relative_to(ROOT).as_posix()}")
    missing = {lang: sum(v is None for v in load(lang)["messages"].values()) for lang in LANGUAGES}
    print(f"{len(keys)} templates; untranslated: {missing}")
    return 1 if check and stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
