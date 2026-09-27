"""Put the web page into the Android and iOS apps.

    python scripts/build_app.py            # build the site, then `npx cap sync`
    python scripts/build_app.py --icons    # and redraw the apps' icons first
    cd app && npx cap open android         # or ios: build and run from there

The apps run the site exactly as the web serves it (build_web.py): Capacitor
copies ``_site`` into ``app/android`` and ``app/ios``. Before that, this checks
that everything the app needs offline is in the site — the engine, mathlint's
wheel and the handwriting recognizer — and writes mathlint's version into both
projects, so a store build always says which mathlint it is.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from icons import android_vector, draw_icon

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SITE = ROOT / "_site"
VERSION_FILE = ROOT / "src" / "mathlint" / "_version.py"

ANDROID_RES = Path("android/app/src/main/res")
ANDROID_GRADLE = Path("android/app/build.gradle")
IOS_PROJECT = Path("ios/App/App.xcodeproj/project.pbxproj")
IOS_ASSETS = Path("ios/App/App/Assets.xcassets")

#: Android's screen densities, as multiples of one dp
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
#: how much of each icon the logo takes (Android promises the middle 66 of 108 dp)
ADAPTIVE_CONTENT = 0.56
IOS_CONTENT = 0.68
#: the logo on the launch screen, in points
SPLASH_POINTS = 96

#: what the app cannot work without, offline (globs, relative to the site)
REQUIRED = (
    "index.html",
    "wheel.json",
    "mathlint-*.whl",
    "vendor/pyodide-*/pyodide.asm.wasm",
    "vendor/pyodide-*/sympy-*.whl",
    "vendor/katex-*/katex.min.js",
    "vendor/mathlive-*/mathlive.min.js",
    "recognizer/recognizer.bin",
)


def mathlint_version() -> str:
    match = re.search(r'__version__ = "([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    return match[1]


def version_code(version: str) -> int:
    """The number the stores compare: 1.2.3 is 10203, and every release is higher."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise SystemExit(f"the apps need a plain X.Y.Z version, not {version!r}")
    major, minor, patch = map(int, match.groups())
    if minor > 99 or patch > 99:
        raise SystemExit(f"{version}: minor and patch must stay below 100 for the version code")
    return major * 10000 + minor * 100 + patch


def write_versions(app: Path, version: str) -> None:
    code = version_code(version)
    gradle = app / ANDROID_GRADLE
    text = gradle.read_text(encoding="utf-8")
    text = re.sub(r"versionCode \d+", f"versionCode {code}", text)
    text = re.sub(r'versionName "[^"]*"', f'versionName "{version}"', text)
    gradle.write_text(text, encoding="utf-8")

    project = app / IOS_PROJECT
    text = project.read_text(encoding="utf-8")
    text = re.sub(r"MARKETING_VERSION = [^;]+;", f"MARKETING_VERSION = {version};", text)
    text = re.sub(r"CURRENT_PROJECT_VERSION = [^;]+;", f"CURRENT_PROJECT_VERSION = {code};", text)
    project.write_text(text, encoding="utf-8")


def missing_from(site: Path) -> list[str]:
    return [pattern for pattern in REQUIRED if not any(site.glob(pattern))]


def icon_files() -> dict[Path, Callable[[], bytes | str]]:
    """How to draw every icon and launch-screen image of both apps, by path
    under app/ (the drawing is slow in pure Python, so each is drawn on call)."""
    files: dict[Path, Callable[[], bytes | str]] = {
        ANDROID_RES / "drawable/ic_launcher_foreground.xml": partial(
            android_vector, content=ADAPTIVE_CONTENT
        ),
        ANDROID_RES / "drawable/ic_launcher_monochrome.xml": partial(
            android_vector, content=ADAPTIVE_CONTENT, monochrome=True
        ),
    }
    # the launcher icons of Android 7 and 7.1, which have no adaptive icons
    for density, scale in DENSITIES.items():
        size = round(48 * scale)
        files[ANDROID_RES / f"mipmap-{density}/ic_launcher.png"] = partial(draw_icon, size)
        files[ANDROID_RES / f"mipmap-{density}/ic_launcher_round.png"] = partial(
            draw_icon, size, circle=True
        )
    files[IOS_ASSETS / "AppIcon.appiconset/AppIcon-1024.png"] = partial(
        draw_icon, 1024, True, content=IOS_CONTENT, opaque=True
    )
    for scale in (1, 2, 3):
        files[IOS_ASSETS / f"Splash.imageset/splash@{scale}x.png"] = partial(
            draw_icon, SPLASH_POINTS * scale
        )
    return files


def write_icons(app: Path) -> None:
    for path, draw in icon_files().items():
        target = app / path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = draw()
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)


def main(argv: list[str]) -> None:
    import build_web

    if "--icons" in argv:
        write_icons(APP)
    build_web.main([])
    missing = missing_from(SITE)
    if missing:
        raise SystemExit("the site is missing what the app needs offline: " + ", ".join(missing))
    write_versions(APP, mathlint_version())
    if "--no-sync" in argv:
        return
    if not (APP / "node_modules").exists():
        raise SystemExit("run `npm ci` in app/ first")
    npx = shutil.which("npx") or "npx"
    subprocess.run([npx, "cap", "sync"], cwd=APP, check=True)
    print(f"synced {SITE} into {APP / 'android'} and {APP / 'ios'}")


if __name__ == "__main__":
    main(sys.argv[1:])
