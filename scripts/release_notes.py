"""Print the changelog section for one version.

    python scripts/release_notes.py v0.1.0
"""

from __future__ import annotations

import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def notes_for(version: str) -> str:
    wanted = f"## [{version.lstrip('v')}]"
    collected: list[str] = []
    inside = False
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        if line.startswith(wanted):
            inside = True
            continue
        if inside and line.startswith("## ["):
            break
        if inside:
            collected.append(line)
    text = "\n".join(collected).strip()
    return text or f"Release {version}."


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # notes contain dashes and quotes
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        raise SystemExit("usage: release_notes.py <version>")
    print(notes_for(sys.argv[1]))
