"""Build the static site in ``_site``: the web page plus a mathlint wheel.

    python scripts/build_web.py              # everything, for the real site
    python scripts/build_web.py --no-vendor  # skip the downloads (tests)
    python -m http.server -d _site 8123

The page unpacks that wheel into Pyodide, so the browser runs exactly the code
that is in this repository. Pyodide, KaTeX, MathLive and the fonts are copied
into ``_site/vendor`` (see vendor.py), and the app icons are drawn (icons.py),
so the site needs nothing from anywhere else.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from icons import draw_icon
from vendor import vendor

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
WEB = ROOT / "web"
DIST = ROOT / "dist"


def build_wheel() -> Path:
    for stale in DIST.glob("*.whl"):
        stale.unlink()
    command = (
        ["uv", "build", "--wheel"]
        if shutil.which("uv")
        else [
            sys.executable,
            "-m",
            "build",
            "--wheel",
        ]
    )
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
    "i18n.js",
    "history.js",
    "speech.js",
    "camera.js",
    "pad.js",
    "reading.js",
    "writing.js",
    "examples.json",
    "solve-examples.json",
    "textbook-problems.json",
    "wheel.json",
    "fonts.css",
    "manifest.webmanifest",
)

#: (file name, size, maskable) for every icon the manifest and index.html name
ICONS = (
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("icon-maskable-512.png", 512, True),
    ("apple-touch-icon.png", 180, True),
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


def write_service_worker(site: Path, version: str) -> list[str]:
    """Fill in sw.js: its version, and every file of the site to keep offline."""
    files = ["./"]
    for path in sorted(site.rglob("*")):
        name = path.relative_to(site).as_posix()
        if path.is_file() and name != "sw.js" and not _NOT_CACHED.search(name):
            files.append(name)
    worker = site / "sw.js"
    text = worker.read_text(encoding="utf-8")
    text = text.replace('"__VERSION__"', json.dumps(version))
    text = text.replace("__PRECACHE__", json.dumps(files, indent=2))
    worker.write_text(text, encoding="utf-8")
    return files


#: files kept out of the install-time cache: licenses and source maps (never
#: loaded), and the recognizer (kept by sw.js the first time it is used)
_NOT_CACHED = re.compile(r"(^|/)(LICENSE[^/]*|[^/]+\.map)$|^recognizer/")


def write_icons(site: Path) -> None:
    folder = site / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    for name, size, maskable in ICONS:
        (folder / name).write_bytes(draw_icon(size, maskable))


def main(argv: list[str]) -> None:
    wheel = build_wheel()
    if SITE.exists():
        shutil.rmtree(SITE)
    # the page's own tests stay behind
    shutil.copytree(WEB, SITE, ignore=shutil.ignore_patterns("tests"))
    shutil.copy2(wheel, SITE / wheel.name)
    (SITE / "wheel.json").write_text(json.dumps({"wheel": wheel.name}), encoding="utf-8")
    write_icons(SITE)
    if "--no-vendor" not in argv:
        vendor(SITE, ROOT / ".cache" / "vendor")

    digest = hashlib.sha256(wheel.read_bytes())
    # the page, and the scripts that draw its icons and fetch its vendored files
    sources = [
        *sorted(WEB.rglob("*")),
        *(ROOT / "scripts" / name for name in ("icons.py", "vendor.py")),
    ]
    for source in sources:
        if source.is_file() and "tests" not in source.relative_to(ROOT).parts:
            digest.update(source.read_bytes())
    stamp = digest.hexdigest()[:10]
    stamp_references(SITE, stamp)
    write_service_worker(SITE, stamp)
    print(f"built {SITE} with {wheel.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
