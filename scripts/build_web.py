"""Build the static site in ``_site``: the web page plus a mathlint wheel.

    python scripts/build_web.py
    python -m http.server -d _site 8123

The page installs that wheel into Pyodide with micropip, so the browser runs
exactly the code that is in this repository.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
WEB = ROOT / "web"
DIST = ROOT / "dist"


def build_wheel() -> Path:
    for stale in DIST.glob("*.whl"):
        stale.unlink()
    command = ["uv", "build", "--wheel"] if shutil.which("uv") else [
        sys.executable,
        "-m",
        "build",
        "--wheel",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    wheels = sorted(DIST.glob("*.whl"))
    if not wheels:
        raise SystemExit("no wheel was produced in dist/")
    return wheels[-1]


def main() -> None:
    wheel = build_wheel()
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(WEB, SITE)
    shutil.copy2(wheel, SITE / wheel.name)
    (SITE / "wheel.json").write_text(json.dumps({"wheel": wheel.name}), encoding="utf-8")
    print(f"built {SITE} with {wheel.name}")


if __name__ == "__main__":
    main()
