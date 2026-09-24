"""Handwritten samples of every symbol the recognizer knows.

Three sources, all usable commercially:

- Detexify (ODbL 1.0): about 210,000 math symbols drawn with a mouse or a
  finger, kept as strokes — each a list of points.
- HASYv2 (ODbL 1.0): 168,000 drawings of symbols, digits and letters, 32×32.
- Handwriting fonts (OFL, Apache 2.0): letters, digits and punctuation in 29
  hands, distorted differently every time they are drawn.

The first run reads the two datasets once into ``training/data/symbols``;
after that ``bank()`` loads in a second.
"""

from __future__ import annotations

import csv
import io
import json
import pickle
import tarfile
from collections import defaultdict
from dataclasses import dataclass
from functools import cache

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image

from .download import DATA, fetch
from .fonts import HAND_FONTS
from .vocab import COMMANDS, DIGITS, LOWER, UPPER

CACHE = DATA / "symbols"
PER_SYMBOL = 800  # samples kept per symbol from each dataset

DETEXIFY_SQL = (
    "https://archive.org/download/detexify/detexify.sql",
    "b6f335c63585868b026b406363ce49aedfbd79f5811c5473fdb67689667dc555",
)
DETEXIFY_SYMBOLS = (
    "https://archive.org/download/detexify/symbols.json",
    "13bfd78164d92f4fb73856926fcd2c272ec171b5c35110de76c4ec6c0cdfced0",
)
HASY = (
    "https://zenodo.org/records/259444/files/HASYv2.tar.bz2?download=1",
    "7c3ffe709e8c2b83f6ab7d8afc79f7b5f46421657981b1752d22a0ed0052aa2d",
)

# the recognizer's token -> the name each dataset uses for it
NAMES = {
    r"\int": r"\int",
    r"\sqrt": r"\sqrt{}",
    r"\pi": r"\pi",
    r"\infty": r"\infty",
    r"\cdot": r"\cdot",
    r"\div": r"\div",
    r"\pm": r"\pm",
    r"\le": r"\leq",
    r"\ge": r"\geq",
    r"\ne": r"\neq",
    r"\to": r"\rightarrow",
    r"\sim": r"\sim",
    r"\Rightarrow": r"\Rightarrow",
    r"\prime": r"\prime",
    r"\times": r"\times",
    r"\theta": r"\theta",
    r"\alpha": r"\alpha",
    r"\beta": r"\beta",
    r"\varphi": r"\varphi",
    r"\lambda": r"\lambda",
    r"\mu": r"\mu",
    r"\Delta": r"\Delta",
    "|": "|",
    "[": "[",
    "]": "]",
    "+": "+",
    "-": "-",
    "<": "<",
    ">": ">",
}
for _char in DIGITS + LOWER + UPPER:
    NAMES[_char] = _char

# what a handwriting font draws for a token
CHARACTERS = {
    **{c: c for c in DIGITS + LOWER + UPPER},
    **{c: c for c in "+=<>()[],;.!|"},
    "-": "-",
    "'": "'",
    r"\prime": "'",
    r"\times": "×",
    r"\div": "÷",
    r"\pm": "±",
    r"\cdot": "·",
    r"\pi": "π",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\mu": "μ",
    r"\lambda": "λ",
    r"\Delta": "Δ",
    r"\le": "≤",
    r"\ge": "≥",
    r"\ne": "≠",
    r"\infty": "∞",
    r"\to": "→",
}


@dataclass(frozen=True)
class Sample:
    """One handwritten example of a symbol."""

    kind: str  # "strokes", "bitmap" or "font"
    strokes: tuple = ()  # arrays of (x, y), in a box 0..1 tall, left at 0
    bitmap: np.ndarray | None = None  # ink is dark, cropped to the ink
    font: str = ""
    char: str = ""

    @property
    def aspect(self) -> float:
        """Width over height."""
        if self.kind == "strokes":
            points = np.concatenate(self.strokes)
            return float(np.ptp(points[:, 0]) / max(np.ptp(points[:, 1]), 1e-6))
        if self.kind == "bitmap":
            return self.bitmap.shape[1] / self.bitmap.shape[0]
        return 0.6


def _normalized(strokes: list) -> tuple | None:
    """Strokes scaled to 0..1 tall (keeping the shape), without timestamps or repeats."""
    arrays = []
    for stroke in strokes:
        points = np.asarray([point[:2] for point in stroke], dtype=np.float32)
        if len(points) == 0:
            continue
        # drop points closer than half a percent of the size to the one before
        keep = [0]
        for index in range(1, len(points)):
            if np.abs(points[index] - points[keep[-1]]).max() > 0.5:
                keep.append(index)
        arrays.append(points[keep])
    if not arrays:
        return None
    every = np.concatenate(arrays)
    low = every.min(axis=0)
    height = max(float(np.ptp(every[:, 1])), float(np.ptp(every[:, 0])) * 0.05, 1e-3)
    return tuple(((stroke - low) / height).astype(np.float16) for stroke in arrays)


def _detexify() -> dict[str, list[Sample]]:
    path = CACHE / "detexify.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    sql = fetch(*DETEXIFY_SQL, name="detexify.sql")
    symbols = json.loads(fetch(*DETEXIFY_SYMBOLS, name="detexify-symbols.json").read_text("utf-8"))
    wanted = {symbol["id"]: symbol["command"] for symbol in symbols}
    token_for = {name: token for token, name in NAMES.items()}
    found: dict[str, list[Sample]] = defaultdict(list)
    with open(sql, encoding="utf-8") as handle:
        copying = False
        for line in handle:
            if line.startswith("COPY samples"):
                copying = True
                continue
            if not copying:
                continue
            if line.startswith("\\."):
                break
            _, key, strokes = line.rstrip("\n").split("\t", 2)
            token = token_for.get(wanted.get(key, ""))
            if token is None or len(found[token]) >= PER_SYMBOL:
                continue
            normalized = _normalized(json.loads(strokes))
            if normalized is not None:
                found[token].append(Sample("strokes", strokes=normalized))
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(dict(found)))
    return dict(found)


def _hasy() -> dict[str, list[Sample]]:
    path = CACHE / "hasy.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    archive = fetch(*HASY, name="HASYv2.tar.bz2")
    token_for = {name: token for token, name in NAMES.items()}
    found: dict[str, list[Sample]] = defaultdict(list)
    with tarfile.open(archive) as tar:
        labels = csv.DictReader(io.TextIOWrapper(tar.extractfile("hasy-data-labels.csv"), "utf-8"))
        wanted = {
            row["path"]: token_for[row["latex"]] for row in labels if row["latex"] in token_for
        }
        for member in tar:
            token = wanted.get(member.name)
            if token is None or len(found[token]) >= PER_SYMBOL:
                continue
            image = np.asarray(Image.open(tar.extractfile(member)).convert("L"))
            ys, xs = np.nonzero(image < 128)
            if len(xs) == 0:
                continue
            crop = image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
            found[token].append(Sample("bitmap", bitmap=crop))
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(dict(found)))
    return dict(found)


def _fonts() -> dict[str, list[Sample]]:
    found: dict[str, list[Sample]] = defaultdict(list)
    for font in HAND_FONTS:
        path = font.path()
        cmap = TTFont(path, lazy=True).getBestCmap()
        for token, char in CHARACTERS.items():
            if ord(char) in cmap:
                found[token].append(Sample("font", font=str(path), char=char))
    return dict(found)


@cache
def bank() -> dict[str, list[Sample]]:
    """Every symbol's handwritten samples, from all three sources."""
    merged: dict[str, list[Sample]] = defaultdict(list)
    for source in (_detexify(), _hasy(), _fonts()):
        for token, samples in source.items():
            merged[token] += samples
    return dict(merged)


def symbol_tokens() -> list[str]:
    """The tokens that are drawn as a symbol of their own (not structure or words)."""
    structural = {
        "^",
        "_",
        "{",
        "}",
        "&",
        r"\\",
        r"\frac",
        r"\,",
        r"\begin{pmatrix}",
        r"\end{pmatrix}",
        r"\text{ or }",
        r"\lim",
    }
    fences = {
        r"\left(": "(",
        r"\right)": ")",
        r"\left|": "|",
        r"\right|": "|",
        r"\left[": "[",
        r"\right]": "]",
    }
    words = {
        r"\sin",
        r"\cos",
        r"\tan",
        r"\cot",
        r"\sec",
        r"\csc",
        r"\ln",
        r"\log",
        r"\exp",
        r"\arcsin",
        r"\arccos",
        r"\arctan",
        r"\sinh",
        r"\cosh",
        r"\tanh",
    }
    out = list(DIGITS + LOWER + UPPER) + list("+-=<>()[],;.!|'")
    out += [
        command
        for command in COMMANDS
        if command not in structural and command not in fences and command not in words
    ]
    return out
