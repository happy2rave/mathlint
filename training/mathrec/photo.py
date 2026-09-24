"""A formula on white turned into a phone's photo of a page.

The line sits inside the camera's frame with paper around it, maybe a bit of
the line above or below. The paper is plain, ruled or squared (the squared
notebooks of Romania, Moldova and much of Europe), and grey, cream or
bright. The ink is pen or faded pencil. The light is uneven, sometimes with a
shadow. The page is seen a little askew, a little out of focus, grainy and
JPEG-compressed.
"""

from __future__ import annotations

import io
import math
import random

import numpy as np
from PIL import Image, ImageFilter

from .image import ink_bounds


def photograph(canvas: Image.Image, size: float, rng: random.Random) -> Image.Image:
    """``canvas`` (a formula on white, written at ``size`` px per em) as a photo."""
    noise = np.random.default_rng(rng.getrandbits(32))
    box = ink_bounds(canvas)
    if box is None:
        return canvas.convert("L")
    left, top, right, bottom = box
    ink = np.asarray(canvas.convert("L"), dtype=np.float32)[top:bottom, left:right] / 255
    ink = 1 - (1 - ink) * rng.uniform(0.55, 1.0)  # pen, or pencil
    ink_h, ink_w = ink.shape

    # the camera's frame: the line with paper around it, never cut off
    frame_h = round(ink_h * rng.uniform(1.3, 2.4))
    frame_w = round(max(ink_w * rng.uniform(1.25, 1.7), frame_h * 1.5))
    x = rng.randint(round(frame_w * 0.1), frame_w - ink_w - round(frame_w * 0.1))
    y = rng.randint(round(frame_h * 0.1), frame_h - ink_h - round(frame_h * 0.1))
    layer = np.ones((frame_h, frame_w), dtype=np.float32)
    layer[y : y + ink_h, x : x + ink_w] = ink
    if rng.random() < 0.25:
        _neighbour(layer, ink, y, rng)

    page = _paper(frame_h, frame_w, size, rng, noise) * layer * _light(frame_h, frame_w, rng)
    image = Image.fromarray(np.clip(page, 0, 255).astype(np.uint8))
    image = _askew(image, rng)
    blur = rng.uniform(0, size * 0.03)
    if blur > 0.3:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    grain = noise.normal(0, rng.uniform(0, 6), (image.height, image.width))
    image = Image.fromarray(np.clip(np.asarray(image) + grain, 0, 255).astype(np.uint8))
    shrink = rng.uniform(0.45, 1.0)  # a phone further away
    image = image.resize(
        (max(8, round(image.width * shrink)), max(8, round(image.height * shrink))),
        Image.Resampling.BILINEAR,
    )
    return _jpeg(image, rng.randint(25, 95))


def _neighbour(layer: np.ndarray, ink: np.ndarray, y: int, rng: random.Random) -> None:
    """The bottom of the line above, or the top of the line below, at the frame's edge."""
    other = ink[:, ::-1]  # another line: this one, mirrored
    show = round(other.shape[0] * rng.uniform(0.1, 0.3))
    width = min(other.shape[1], layer.shape[1])
    start = rng.randint(0, layer.shape[1] - width)
    if rng.random() < 0.5 and y > show + 2:
        layer[:show, start : start + width] *= other[-show:, :width]
    elif layer.shape[0] - (y + ink.shape[0]) > show + 2:
        layer[-show:, start : start + width] *= other[:show, :width]


def _paper(
    height: int, width: int, size: float, rng: random.Random, noise: np.random.Generator
) -> np.ndarray:
    level = rng.uniform(170, 250)
    coarse = noise.normal(0, 1, (rng.randint(3, 8), rng.randint(3, 12))).astype(np.float32)
    texture = np.asarray(
        Image.fromarray(coarse, mode="F").resize((width, height), Image.Resampling.BICUBIC)
    )
    paper = (
        level + texture * rng.uniform(0, 8) + noise.normal(0, rng.uniform(0, 3), (height, width))
    )
    thick = max(1, round(size * rng.uniform(0.015, 0.045)))
    darkness = rng.uniform(10, 55)
    ruling = rng.choices(["plain", "lines", "grid"], weights=[0.3, 0.3, 0.4])[0]
    if ruling == "lines":
        _rule(paper, size * rng.uniform(1.1, 1.8), thick, darkness, rng, axis=0)
    elif ruling == "grid":
        spacing = size * rng.uniform(0.45, 0.75)
        _rule(paper, spacing, thick, darkness, rng, axis=0)
        _rule(paper, spacing, thick, darkness, rng, axis=1)
    if rng.random() < 0.15:  # the red margin, grey in grayscale
        at = rng.randint(0, width - 1)
        paper[:, at : at + thick + 1] -= rng.uniform(30, 80)
    return paper


def _rule(
    paper: np.ndarray, spacing: float, thick: int, darkness: float, rng: random.Random, axis: int
) -> None:
    position = rng.uniform(0, spacing)
    while position < paper.shape[axis]:
        at = int(position)
        if axis == 0:
            paper[at : at + thick, :] -= darkness
        else:
            paper[:, at : at + thick] -= darkness
        position += spacing


def _light(height: int, width: int, rng: random.Random) -> np.ndarray:
    """Brighter on one side than the other, and maybe a phone's shadow across the page."""
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    ys /= max(height - 1, 1)
    xs /= max(width - 1, 1)
    angle = rng.uniform(0, 2 * math.pi)
    ramp = xs * math.cos(angle) + ys * math.sin(angle)
    ramp = (ramp - ramp.min()) / max(float(np.ptp(ramp)), 1e-6)
    light = 1 - rng.uniform(0, 0.35) * ramp
    if rng.random() < 0.3:
        angle = rng.uniform(0, 2 * math.pi)
        across = (xs - rng.uniform(0, 1)) * width * math.cos(angle)
        across += (ys - rng.uniform(0, 1)) * height * math.sin(angle)
        soft = 1 / (1 + np.exp(-across / (height * rng.uniform(0.05, 0.4))))
        light *= 1 - rng.uniform(0.2, 0.45) * soft
    return light


def _askew(image: Image.Image, rng: random.Random) -> Image.Image:
    """The page seen from a little off to the side: each corner moved by up to 4%.

    The edges, where the tilted page would show what is beside it, are cut off.
    """
    width, height = image.size
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    seen = [
        (x + rng.uniform(-0.04, 0.04) * width, y + rng.uniform(-0.04, 0.04) * height)
        for x, y in corners
    ]
    rows = []
    targets = []
    for (x, y), (u, v) in zip(corners, seen, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        targets += [u, v]
    coefficients = np.linalg.solve(np.array(rows, dtype=np.float64), np.array(targets))
    tilted = image.transform(
        image.size, Image.Transform.PERSPECTIVE, tuple(coefficients), Image.Resampling.BILINEAR
    )
    cut_x, cut_y = math.ceil(width * 0.045), math.ceil(height * 0.045)
    return tilted.crop((cut_x, cut_y, width - cut_x, height - cut_y))


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("L")
