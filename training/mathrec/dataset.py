"""What the recognizer learns from, and the fixed sets it is measured on.

Four kinds of image, all made on the fly and all passed through
``image.prepare`` as the browser does:

- printed: typeset on white (a screenshot, a clean scan);
- handwritten: written on white (the pad);
- printed-photo and handwritten-photo: the same, photographed on paper.

``stream`` makes them endlessly and ``batches`` groups them into batches of
images of about the same width, so little of a batch is padding. The held-out
sets are made once from fixed seeds and written to
``training/data/eval/<kind>/``: the same images on every machine and every
run, never trained on.

Nothing here imports PyTorch, so the processes that make training data stay
small (``feed.py``); ``tensors.py`` turns their batches into tensors.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

import numpy as np
from PIL import Image

from . import formulas, photo, render_hand, render_printed, vocab
from .download import DATA
from .image import prepare

KINDS = ("printed", "handwritten", "printed-photo", "handwritten-photo")
WEIGHTS = (0.15, 0.25, 0.25, 0.35)
MAX_TOKENS = 120  # with <s> and </s>; the longest sampled formula has about 100
EVAL = DATA / "eval"


def example(kind: str, latex: str, rng: random.Random) -> np.ndarray:
    """``latex`` as an image of ``kind``: uint8, 96 px tall, ink dark."""
    renderer = render_printed if kind.startswith("printed") else render_hand
    canvas, size = renderer.draw_formula(latex, rng)
    if kind.endswith("photo"):
        canvas = photo.photograph(canvas, size, rng)
    return np.asarray(prepare(canvas))


def stream(seed: int):
    """Endless (image, token ids) pairs of every kind, mixed by ``WEIGHTS``."""
    rng = random.Random(seed)
    while True:
        latex = formulas.sample(rng)
        ids = vocab.encode(vocab.tokenize(latex))
        if len(ids) > MAX_TOKENS:
            continue
        kind = rng.choices(KINDS, weights=WEIGHTS)[0]
        yield example(kind, latex, rng), ids


def batches(seed: int, size: int, pool: int = 16) -> list[list[tuple[np.ndarray, list[int]]]]:
    """``pool`` batches of ``size``, each of images of about the same width, shuffled."""
    examples = stream(seed)
    everything = sorted(
        (next(examples) for _ in range(size * pool)), key=lambda example: example[0].shape[1]
    )
    groups = [everything[i : i + size] for i in range(0, len(everything), size)]
    random.Random(seed).shuffle(groups)
    return groups


def make_eval(kind: str, count: int, root: Path = EVAL) -> Path:
    """Write the held-out set of ``kind``: ``count`` images and ``labels.tsv``."""
    folder = root / kind
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(f"eval-{kind}")
    rows = []
    for index in range(count):
        latex = formulas.sample(rng)
        name = f"{index:05d}.png"
        Image.fromarray(example(kind, latex, rng)).save(folder / name)
        rows.append((name, latex))
    with open(folder / "labels.tsv", "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, delimiter="\t", lineterminator="\n").writerows(rows)
    return folder


def load_eval(kind: str, root: Path = EVAL) -> list[tuple[np.ndarray, str]]:
    """The held-out set of ``kind`` as (image, LaTeX) pairs."""
    folder = root / kind
    with open(folder / "labels.tsv", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))
    return [(np.asarray(Image.open(folder / name).convert("L")), latex) for name, latex in rows]


if __name__ == "__main__":
    import sys

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    for kind in KINDS:
        print(make_eval(kind, count))
