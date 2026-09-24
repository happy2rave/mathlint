"""The shape of every image the recognizer sees: grayscale, 96 px tall.

A formula is cropped to its ink with a little margin and scaled to the height;
one wider than the widest input is scaled down to fit it and centred on the
height instead.

``prepare`` is what the browser does to a photo or to the pad before the model
reads it, step for step (``web/recognizer/prepare.js`` is its twin, and a test
holds them together): even out the light, stretch the contrast, find the ink
while ignoring ruled lines and stray specks at the edges, crop and scale. Every
training image goes through it too, so the model learns from exactly what it
will be shown.
"""

from __future__ import annotations

import random

import numpy as np
from PIL import Image

HEIGHT = 96
MAX_WIDTH = 768
MIN_WIDTH = 32


def ink_bounds(image: Image.Image, threshold: int = 200) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) of everything darker than ``threshold``."""
    pixels = np.asarray(image.convert("L"))
    ys, xs = np.nonzero(pixels < threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def finish(
    image: Image.Image, rng: random.Random | None = None, margin: float = 0.08
) -> Image.Image:
    """Crop to the ink (plus a margin of ``margin`` of the height) and scale to 96 px tall."""
    image = image.convert("L")
    box = ink_bounds(image)
    if box is None:
        return Image.new("L", (MIN_WIDTH, HEIGHT), 255)
    left, top, right, bottom = box
    pad = (bottom - top) * (margin if rng is None else rng.uniform(margin * 0.5, margin * 2))
    pad = int(max(pad, 2))
    # white beyond the edges, so a margin past them is paper, not black
    padded = Image.new("L", (image.width + 2 * pad, image.height + 2 * pad), 255)
    padded.paste(image, (pad, pad))
    crop = padded.crop((left, top, right + 2 * pad, bottom + 2 * pad))
    return fit(crop)


def fit(image: Image.Image) -> Image.Image:
    """Scale to 96 px tall; too wide, scale to 768 px wide and pad the height."""
    width, height = image.size
    scale = HEIGHT / height
    if width * scale > MAX_WIDTH:
        scale = MAX_WIDTH / width
    new = (max(MIN_WIDTH, round(width * scale)), max(1, round(height * scale)))
    resized = image.resize(new, Image.Resampling.LANCZOS)
    if resized.height == HEIGHT:
        return resized
    canvas = Image.new("L", (resized.width, HEIGHT), 255)
    canvas.paste(resized, (0, (HEIGHT - resized.height) // 2))
    return canvas


# -- the browser's preparation, mirrored ---------------------------------------------

WORKING_HEIGHT = 384  # photos are shrunk to at most this before anything else
PAPER = 250  # after evening the light, this and lighter is paper
DARK = 128  # darker than this is ink
TRIM = 0.003  # the share of ink ignored at each edge: specks, a neighbour's line
RULED = 0.5  # a row (or column) darker than this share across is a ruled line
MARGIN = 0.08  # paper kept around the ink, as a share of its height


def resize(pixels: np.ndarray, width: int, height: int) -> np.ndarray:
    """Linear resampling that averages when shrinking (PIL's BILINEAR, spelled out)."""
    out = pixels.astype(np.float64)
    out = _resample(out, height, axis=0)
    out = _resample(out, width, axis=1)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def _taps(size_in: int, size_out: int) -> tuple[np.ndarray, np.ndarray]:
    """For each output pixel, the input pixels it reads and their weights (a triangle)."""
    scale = size_in / size_out
    support = max(scale, 1.0)
    centres = (np.arange(size_out) + 0.5) * scale
    first = np.floor(centres - support).astype(np.int64)
    count = int(np.ceil(2 * support)) + 2
    index = first[:, None] + np.arange(count)[None, :]
    weights = np.maximum(0.0, 1.0 - np.abs(index + 0.5 - centres[:, None]) / support)
    weights[(index < 0) | (index >= size_in)] = 0.0
    weights /= weights.sum(axis=1, keepdims=True)
    return np.clip(index, 0, size_in - 1), weights


def _resample(pixels: np.ndarray, size: int, axis: int) -> np.ndarray:
    if pixels.shape[axis] == size:
        return pixels
    index, weights = _taps(pixels.shape[axis], size)
    if axis == 0:
        return np.einsum("otw,ot->ow", pixels[index], weights)
    return np.einsum("hot,ot->ho", pixels[:, index], weights)


def _max_filter(pixels: np.ndarray, radius: int, pick=np.maximum) -> np.ndarray:
    """The largest value within ``radius`` (a square), edges repeated."""
    out = pixels
    for axis in (0, 1):
        padded = np.pad(out, [(radius, radius) if a == axis else (0, 0) for a in (0, 1)], "edge")
        length = out.shape[axis]
        best = np.take(padded, range(0, length), axis=axis)
        for shift in range(1, 2 * radius + 1):
            best = pick(best, np.take(padded, range(shift, shift + length), axis=axis))
        out = best
    return out


def _box_blur(pixels: np.ndarray, radius: int) -> np.ndarray:
    """The mean within ``radius`` (a square), edges repeated."""
    out = pixels.astype(np.float64)
    for axis in (0, 1):
        padded = np.pad(
            out, [(radius + 1, radius) if a == axis else (0, 0) for a in (0, 1)], "edge"
        )
        sums = np.cumsum(padded, axis=axis)
        length = out.shape[axis]
        high = np.take(sums, range(2 * radius + 1, 2 * radius + 1 + length), axis=axis)
        low = np.take(sums, range(0, length), axis=axis)
        out = (high - low) / (2 * radius + 1)
    return out


def _ink_span(counts: np.ndarray, trim: float) -> tuple[int, int] | None:
    total = counts.sum()
    if total == 0:
        return None
    cumulative = np.cumsum(counts)
    skip = total * trim
    start = int(np.searchsorted(cumulative, skip, side="right"))
    end = int(np.searchsorted(cumulative, total - skip, side="left")) + 1
    return start, max(end, start + 1)


def prepare(image: Image.Image) -> Image.Image:
    """A photo (or the pad) turned into what the model reads, as the browser does it."""
    pixels = np.asarray(image.convert("L"), dtype=np.uint8)
    # 1. shrink by a whole factor, averaging blocks, to at most WORKING_HEIGHT tall
    factor = -(-pixels.shape[0] // WORKING_HEIGHT)
    if factor > 1:
        h, w = pixels.shape[0] // factor, pixels.shape[1] // factor
        blocks = pixels[: h * factor, : w * factor].reshape(h, factor, w, factor)
        pixels = np.rint(blocks.mean(axis=(1, 3))).astype(np.uint8)
    height = pixels.shape[0]
    # 2. even out the light: the paper's brightness, found by wiping out the ink
    #    (a closing: the largest nearby value, then the smallest of those, which
    #    removes strokes but keeps the edge of a shadow where it is), smoothed
    radius = max(1, height // 16)
    closed = _max_filter(_max_filter(pixels, radius), radius, pick=np.minimum)
    paper = _box_blur(closed, max(1, radius // 2))
    even = np.clip(np.rint(pixels * 255.0 / np.maximum(paper, 1.0)), 0, 255).astype(np.uint8)
    # 3. stretch the contrast: the darkest 1% becomes black, paper white
    histogram = np.bincount(even.ravel(), minlength=256)
    darkest = int(np.searchsorted(np.cumsum(histogram), even.size * 0.01, side="left"))
    if darkest < PAPER:
        stretched = (even.astype(np.float64) - darkest) * 255.0 / (PAPER - darkest)
        even = np.clip(np.rint(stretched), 0, 255).astype(np.uint8)
    # 4. find the ink, ignoring ruled lines and a trace of specks at each edge
    ink = even < DARK
    ink[ink.mean(axis=1) > RULED, :] = False
    ink[:, ink.mean(axis=0) > RULED] = False
    rows = _ink_span(ink.sum(axis=1), TRIM)
    columns = _ink_span(ink.sum(axis=0), TRIM)
    if rows is None or columns is None:
        return Image.new("L", (MIN_WIDTH, HEIGHT), 255)
    (top, bottom), (left, right) = rows, columns
    # 5. crop with a margin of paper, and scale to the model's height
    pad = max(2, round((bottom - top) * MARGIN))
    padded = np.pad(even, pad, constant_values=255)
    crop = padded[top : bottom + 2 * pad, left : right + 2 * pad]
    return Image.fromarray(_fitted(crop))


def _fitted(crop: np.ndarray) -> np.ndarray:
    height, width = crop.shape
    scale = HEIGHT / height
    if width * scale > MAX_WIDTH:
        scale = MAX_WIDTH / width
    new_width = max(MIN_WIDTH, round(width * scale))
    new_height = max(1, min(HEIGHT, round(height * scale)))
    resized = resize(crop, new_width, new_height)
    if new_height == HEIGHT:
        return resized
    out = np.full((HEIGHT, new_width), 255, dtype=np.uint8)
    top = (HEIGHT - new_height) // 2
    out[top : top + new_height] = resized
    return out
