"""Put everything the page loads from other sites into ``_site/vendor``.

The page then makes no third-party requests: nothing a student types or opens
tells a CDN anything, the whole app can be cached for offline use, and the
Android and iOS builds get the same files.

Every download is pinned: an npm tarball by the integrity hash npm publishes,
and each Pyodide package by the SHA-256 in Pyodide's own lock file (which
comes from the pinned Pyodide tarball). Downloads are kept in ``.cache/vendor``
so a rebuild does not fetch them again.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PYODIDE_VERSION = "314.0.7"
PYODIDE_PACKAGES = ("sympy",)  # and whatever they depend on
PYODIDE_CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"


@dataclass(frozen=True)
class Tarball:
    url: str
    integrity: str  # npm's "sha512-<base64>"
    # member pattern -> folder under vendor/ (a pattern with * keeps the file name)
    files: dict[str, str]


TARBALLS = (
    Tarball(
        f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz",
        "sha512-0YvXxEhfEdpLfb/XkM2BFAeMROq0iMUX2bzzH9pOttyMcWkwq+HbE5uyuGD82LN7y2q+SNvi/6V5JEsOlD2R1A==",
        {
            "package/pyodide.mjs": f"pyodide-{PYODIDE_VERSION}",
            "package/pyodide.asm.mjs": f"pyodide-{PYODIDE_VERSION}",
            "package/pyodide.asm.wasm": f"pyodide-{PYODIDE_VERSION}",
            "package/python_stdlib.zip": f"pyodide-{PYODIDE_VERSION}",
            "package/pyodide-lock.json": f"pyodide-{PYODIDE_VERSION}",
        },
    ),
    Tarball(
        "https://registry.npmjs.org/katex/-/katex-0.16.11.tgz",
        "sha512-RQrI8rlHY92OLf3rho/Ts8i/XvjgguEjOkO1BEXcU3N8BqPpSzBNwV/G0Ukr+P/l3ivvJUE/Fa/CwbS6HesGNQ==",
        {
            "package/dist/katex.min.js": "katex-0.16.11",
            "package/dist/katex.min.css": "katex-0.16.11",
            "package/dist/fonts/*.woff2": "katex-0.16.11/fonts",
            "package/LICENSE": "katex-0.16.11",
        },
    ),
    Tarball(
        "https://registry.npmjs.org/mathlive/-/mathlive-0.110.0.tgz",
        "sha512-UOpJsQ6h1eeN0xZULGTl1MwUB/lZLCDuzKeHvKEh7Zra8U/rtgDNrssj5PZdJtBTIV48AfEhtv6rv47AeMOxJA==",
        {
            "package/mathlive.min.js": "mathlive-0.110.0",
            "package/fonts/*.woff2": "mathlive-0.110.0/fonts",
            "package/LICENSE.txt": "mathlive-0.110.0",
        },
    ),
    Tarball(
        "https://registry.npmjs.org/@fontsource-variable/figtree/-/figtree-5.3.0.tgz",
        "sha512-VRVodD7OiG7apQwE8/2fMjaqpY/a0qRJqL5HtYj8CKIVps+9amaFcdfKmDIf7iqYQx6iPLlArVXAfKeIZmVcNQ==",
        {
            "package/files/figtree-latin-wght-normal.woff2": "fonts",
            "package/files/figtree-latin-ext-wght-normal.woff2": "fonts",
            "package/LICENSE": "fonts/figtree",
        },
    ),
    Tarball(
        "https://registry.npmjs.org/@fontsource/spline-sans-mono/-/spline-sans-mono-5.3.0.tgz",
        "sha512-9MJxL52KuuVskwM3LbCwEP/L3ClsHsCd18gwmm5df/ZFh/TIg3LE9DT4pLyB5ptKCvEEi7JwclAe8HhCfzlBWg==",
        {
            "package/files/spline-sans-mono-latin-400-normal.woff2": "fonts",
            "package/files/spline-sans-mono-latin-600-normal.woff2": "fonts",
            "package/LICENSE": "fonts/spline-sans-mono",
        },
    ),
)


def vendor(site: Path, cache: Path) -> list[Path]:
    """Write every vendored file under ``site / "vendor"``; return their paths."""
    target = site / "vendor"
    written: list[Path] = []
    for tarball in TARBALLS:
        data = _download(tarball.url, cache, integrity=tarball.integrity)
        written += _unpack(data, tarball.files, target)
    pyodide = target / f"pyodide-{PYODIDE_VERSION}"
    lock = json.loads((pyodide / "pyodide-lock.json").read_text(encoding="utf-8"))
    for name in _with_dependencies(lock, PYODIDE_PACKAGES):
        package = lock["packages"][name]
        data = _download(PYODIDE_CDN + package["file_name"], cache, sha256=package["sha256"])
        path = pyodide / package["file_name"]
        path.write_bytes(data)
        written.append(path)
    return written


def _with_dependencies(lock: dict, names) -> list[str]:
    found: list[str] = []
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in found:
            continue
        found.append(name)
        pending += lock["packages"][name].get("depends", [])
    return sorted(found)


def _download(url: str, cache: Path, *, integrity: str = "", sha256: str = "") -> bytes:
    cache.mkdir(parents=True, exist_ok=True)
    stored = cache / hashlib.sha256(url.encode()).hexdigest()[:16] / url.rsplit("/", 1)[-1]
    if stored.exists():
        data = stored.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - pinned URLs
            data = response.read()
    _verify(url, data, integrity=integrity, sha256=sha256)
    if not stored.exists():
        stored.parent.mkdir(parents=True, exist_ok=True)
        stored.write_bytes(data)
    return data


def _verify(url: str, data: bytes, *, integrity: str, sha256: str) -> None:
    if integrity:
        algorithm, _, expected = integrity.partition("-")
        actual = base64.b64encode(hashlib.new(algorithm, data).digest()).decode()
    else:
        expected, actual = sha256, hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise SystemExit(f"{url} does not match its pinned hash — refusing to use it")


def _unpack(data: bytes, files: dict[str, str], target: Path) -> list[Path]:
    written = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        for pattern, folder in files.items():
            matched = [member for member in members if fnmatch.fnmatch(member.name, pattern)]
            if not matched:
                raise SystemExit(f"nothing in the tarball matches {pattern}")
            for member in matched:
                path = target / folder / Path(member.name).name
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, open(path, "wb") as sink:
                    shutil.copyfileobj(source, sink)
                written.append(path)
    return written
