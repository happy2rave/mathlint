"""Downloads the training data needs, each pinned by its SHA-256.

A file is fetched once into ``training/data/downloads`` and checked every time
it is used, so what the model learns from cannot change underneath it.
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DOWNLOADS = DATA / "downloads"


def fetch(url: str, sha256: str, name: str | None = None) -> Path:
    """The file at ``url``, downloaded once and checked against ``sha256``."""
    path = DOWNLOADS / (name or url.rsplit("/", 1)[-1])
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "mathlint-training"})
        with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 - pinned
            data = response.read()
        partial = path.with_suffix(path.suffix + ".part")
        partial.write_bytes(data)
        partial.replace(path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != sha256:
        raise RuntimeError(f"{path.name} does not match its pinned hash ({actual})")
    return path
