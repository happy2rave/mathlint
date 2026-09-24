"""Reading a line: greedy decoding for quick checks, beam search for the real thing.

Beam search keeps the ``width`` likeliest partial readings at every step and
returns every finished one, best first, each token with its probability (a
symbol under ``UNSURE`` is one the notebook points out). ``best`` then takes
the first reading the notebook can actually read, so a slip that makes nonsense
gives way to the next likeliest reading.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import torch

from . import vocab
from .dataset import MAX_TOKENS
from .model import Recognizer
from .tensors import to_tensor

UNSURE = 0.6


@dataclass
class Reading:
    ids: list[int]  # without <s> and </s>
    probs: list[float]  # each token's probability
    score: float

    @property
    def latex(self) -> str:
        return vocab.decode(self.ids)


@torch.no_grad()
def greedy(
    model: Recognizer, images: torch.Tensor, widths: torch.Tensor | None, limit: int = MAX_TOKENS
) -> list[list[int]]:
    """The likeliest token at every step, for a whole batch at once."""
    memory, mask = model.encode(images, widths)
    batch = images.shape[0]
    tokens = torch.full((batch, 1), vocab.START, dtype=torch.long, device=images.device)
    done = torch.zeros(batch, dtype=torch.bool, device=images.device)
    for _ in range(limit - 1):
        following = model.decode(memory, tokens, mask)[:, -1].argmax(-1)
        following[done] = vocab.PAD
        tokens = torch.cat([tokens, following[:, None]], dim=1)
        done |= following == vocab.END
        if done.all():
            break
    out = []
    for row in tokens[:, 1:].tolist():
        out.append(row[: row.index(vocab.END)] if vocab.END in row else row)
    return out


def _penalty(length: int) -> float:
    return ((5 + length) / 6) ** 0.6  # longer readings are not punished for being long


@torch.no_grad()
def search(
    model: Recognizer, image: np.ndarray, width: int = 4, limit: int = MAX_TOKENS
) -> list[Reading]:
    """Every finished reading of one prepared image (uint8, 96 tall), best first."""
    device = next(model.parameters()).device
    batch = to_tensor([image]).to(device)
    memory, _ = model.encode(batch)
    alive = [([vocab.START], [], 0.0)]  # (tokens, probabilities, log probability)
    finished: list[Reading] = []
    for _ in range(limit - 1):
        tokens = torch.tensor([ids for ids, _, _ in alive], device=device)
        logits = model.decode(memory.expand(len(alive), -1, -1), tokens)[:, -1].float()
        log_probs = torch.log_softmax(logits, dim=-1)
        top = log_probs.topk(width, dim=-1)
        candidates = []
        for row, (ids, probs, total) in enumerate(alive):
            for value, index in zip(
                top.values[row].tolist(), top.indices[row].tolist(), strict=True
            ):
                candidates.append((ids + [index], probs + [float(np.exp(value))], total + value))
        candidates.sort(key=lambda c: c[2] / _penalty(len(c[0]) - 1), reverse=True)
        alive = []
        for ids, probs, total in candidates:
            if ids[-1] == vocab.END:
                finished.append(Reading(ids[1:-1], probs[:-1], total / _penalty(len(ids) - 1)))
            else:
                alive.append((ids, probs, total))
            if len(alive) == width:
                break
        best_alive = max((t / _penalty(len(i) - 1) for i, _, t in alive), default=-np.inf)
        if len(finished) >= width and max(r.score for r in finished) >= best_alive:
            break
        if not alive:
            break
    finished.sort(key=lambda reading: reading.score, reverse=True)
    return finished


def best(readings: list[Reading], valid: Callable[[str], bool] | None = None) -> Reading | None:
    """The likeliest reading the notebook can read (or simply the likeliest)."""
    if valid is not None:
        for reading in readings:
            if valid(reading.latex):
                return reading
    return readings[0] if readings else None
