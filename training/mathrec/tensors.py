"""Prepared images and token ids as PyTorch batches."""

from __future__ import annotations

import numpy as np
import torch

from . import vocab
from .model import STRIDE


def to_tensor(pixels: list[np.ndarray]) -> torch.Tensor:
    """Images as one batch, ink 1 and paper 0, padded with paper on the right.

    Every width is rounded up to a whole number of the encoder's cells, as the
    browser does to its one image.
    """
    width = max(image.shape[1] for image in pixels)
    width = -(-width // STRIDE) * STRIDE
    batch = torch.zeros(len(pixels), 1, pixels[0].shape[0], width)
    for index, image in enumerate(pixels):
        ink = 1.0 - torch.from_numpy(image.astype(np.float32)) / 255.0
        batch[index, 0, :, : image.shape[1]] = ink
    return batch


def collate(batch: list[tuple[np.ndarray, list[int]]]):
    """(images, tokens padded with <pad>, each image's own width)."""
    images = to_tensor([image for image, _ in batch])
    length = max(len(ids) for _, ids in batch)
    tokens = torch.full((len(batch), length), vocab.PAD, dtype=torch.long)
    for index, (_, ids) in enumerate(batch):
        tokens[index, : len(ids)] = torch.tensor(ids)
    widths = torch.tensor([image.shape[1] for image, _ in batch])
    return images, tokens, widths
