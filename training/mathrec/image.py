"""The shape of every image the recognizer sees: grayscale, 96 px tall.

A formula is cropped to its ink with a little margin and scaled to the height;
one wider than the widest input is scaled down to fit it and centred on the
height instead. The browser does exactly the same to a photo or to the pad.
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
