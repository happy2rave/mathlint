"""Performance budgets for the built site. CI fails when one is broken.

    python scripts/build_web.py && python scripts/budget.py

A budget is a line that a change has to argue its way past, not a target: when
one is broken on purpose, raise it in the same commit and say why.
"""

from __future__ import annotations

import gzip
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"

#: the page's own code, gzipped as a server sends it (vendored files excluded)
OWN_CODE_KB = 75
#: stylesheets the browser must load before it can paint anything
BLOCKING_STYLESHEETS = 3
#: everything a visit downloads once, for offline use
SITE_MB = 25
#: importing the engine in CPython (the browser's is slower, but moves with it)
IMPORT_SECONDS = 2.0


@dataclass
class Measure:
    name: str
    value: float
    budget: float
    unit: str

    @property
    def ok(self) -> bool:
        return self.value <= self.budget

    def line(self) -> str:
        mark = "ok  " if self.ok else "OVER"
        value = f"{self.value:.2f}" if self.unit else f"{self.value:.0f}"
        return f"{mark} {self.name}: {value}{self.unit} (budget {self.budget}{self.unit})"


def own_code_kb(site: Path) -> float:
    files = [path for path in site.iterdir() if path.is_file() and path.suffix in _OWN]
    files += sorted((site / "locales").glob("*.json"))[:1]  # one language is loaded
    return sum(len(gzip.compress(path.read_bytes(), 9)) for path in files) / 1024


_OWN = {".html", ".js", ".css", ".json", ".webmanifest"}


def blocking_stylesheets(html: str) -> int:
    head = html.split("</head>", 1)[0]
    return len(re.findall(r'<link\b[^>]*rel="stylesheet"', head))


def site_mb(site: Path) -> float:
    return sum(path.stat().st_size for path in site.rglob("*") if path.is_file()) / 1e6


def import_seconds() -> float:
    """The best of three fresh imports: the others are the machine being busy."""
    best = float("inf")
    for _ in range(3):
        started = time.perf_counter()
        subprocess.run([sys.executable, "-c", "import mathlint.web_api"], check=True)
        best = min(best, time.perf_counter() - started)
    return best


def measures(site: Path = SITE) -> list[Measure]:
    html = (site / "index.html").read_text(encoding="utf-8")
    return [
        Measure("page code (gzip)", own_code_kb(site), OWN_CODE_KB, " KB"),
        Measure(
            "stylesheets before first paint", blocking_stylesheets(html), BLOCKING_STYLESHEETS, ""
        ),
        Measure("whole site", site_mb(site), SITE_MB, " MB"),
        Measure("engine import", import_seconds(), IMPORT_SECONDS, " s"),
    ]


def main() -> int:
    if not (SITE / "index.html").exists():
        print("build the site first: python scripts/build_web.py")
        return 2
    results = measures()
    for measure in results:
        print(measure.line())
    return 0 if all(measure.ok for measure in results) else 1


if __name__ == "__main__":
    sys.exit(main())
