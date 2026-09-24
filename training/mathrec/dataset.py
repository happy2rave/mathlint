"""What the recognizer learns from, and the fixed sets it is measured on.

Four kinds of image, all made on the fly and all passed through
``image.prepare`` as the browser does:

- printed: typeset on white (a screenshot, a clean scan);
- handwritten: written on white (the pad);
- printed-photo and handwritten-photo: the same, photographed on paper.

``Stream`` is an endless PyTorch dataset of them. The held-out sets are made
once from fixed seeds and written to ``training/data/eval/<kind>/``: the same
images on every machine and every run, never trained on.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import IterableDataset, get_worker_info

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


class Stream(IterableDataset):
    """Endless (image, token ids) pairs; each worker draws its own."""

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def __iter__(self):
        worker = get_worker_info()
        rng = random.Random(self.seed * 1000 + (worker.id if worker else 0))
        while True:
            latex = formulas.sample(rng)
            ids = vocab.encode(vocab.tokenize(latex))
            if len(ids) > MAX_TOKENS:
                continue
            kind = rng.choices(KINDS, weights=WEIGHTS)[0]
            yield example(kind, latex, rng), ids


def to_tensor(pixels: list[np.ndarray]) -> torch.Tensor:
    """Images as one batch, ink 1 and paper 0, padded with paper on the right."""
    width = max(image.shape[1] for image in pixels)
    width = -(-width // 16) * 16  # the encoder downsamples by 16
    batch = torch.zeros(len(pixels), 1, pixels[0].shape[0], width)
    for index, image in enumerate(pixels):
        ink = 1.0 - torch.from_numpy(image.astype(np.float32)) / 255.0
        batch[index, 0, :, : image.shape[1]] = ink
    return batch


def collate(batch: list[tuple[np.ndarray, list[int]]]) -> tuple[torch.Tensor, torch.Tensor]:
    images = to_tensor([image for image, _ in batch])
    length = max(len(ids) for _, ids in batch)
    tokens = torch.full((len(batch), length), vocab.PAD, dtype=torch.long)
    for index, (_, ids) in enumerate(batch):
        tokens[index, : len(ids)] = torch.tensor(ids)
    return images, tokens


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
