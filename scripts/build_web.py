"""Build the static site in ``_site``: the web page plus a mathlint wheel.

    python scripts/build_web.py
    python -m http.server -d _site 8123

The page installs that wheel into Pyodide with micropip, so the browser runs
exactly the code that is in this repository.
"""

from __future__ import annotations

import hashlib
import json
import re
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


#: The page's own files, as they are referenced from index.html and the scripts.
_LOCAL_FILES = (
    "style.css",
    "app.js",
    "editor.js",
    "keypad.js",
    "numberline.js",
    "graph.js",
    "engine.js",
    "worker.js",
    "examples.json",
    "solve-examples.json",
    "textbook-problems.json",
    "wheel.json",
)


def stamp_references(site: Path, stamp: str) -> None:
    """Add ``?v=<stamp>`` to every reference to the page's own files.

    Browsers (and GitHub Pages, for ten minutes) keep serving a cached script
    after a release; a new query string makes each release load fresh.
    """
    pattern = re.compile(r"""(["'`])(\./)?(""" + "|".join(map(re.escape, _LOCAL_FILES)) + r")\1")
    for page in [site / "index.html", *site.glob("*.js")]:
        text = page.read_text(encoding="utf-8")
        text = pattern.sub(lambda m: f"{m[1]}{m[2] or ''}{m[3]}?v={stamp}{m[1]}", text)
        page.write_text(text, encoding="utf-8")


def main() -> None:
    wheel = build_wheel()
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(WEB, SITE)
    shutil.copy2(wheel, SITE / wheel.name)
    (SITE / "wheel.json").write_text(json.dumps({"wheel": wheel.name}), encoding="utf-8")

    digest = hashlib.sha256(wheel.read_bytes())
    for source in sorted(WEB.rglob("*")):
        if source.is_file():
            digest.update(source.read_bytes())
    stamp_references(SITE, digest.hexdigest()[:10])
    print(f"built {SITE} with {wheel.name}")


if __name__ == "__main__":
    main()
