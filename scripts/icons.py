"""The app's icons, drawn as PNGs without any imaging library.

The logo is a notebook page: paper with a pen-blue border, the red margin line,
and a tick. Shapes are signed distance functions, so every pixel is sampled once
and its edge is antialiased from its distance to the shape.

A "maskable" icon fills the whole square with paper and keeps the drawing in
the middle 60%, because a phone crops it to a circle or a squircle.
"""

from __future__ import annotations

import math
import struct
import zlib

PAPER = (255, 253, 247)
PEN = (45, 70, 200)
MARGIN = (234, 165, 156)


def draw_icon(size: int, maskable: bool = False) -> bytes:
    """A ``size`` x ``size`` PNG of the logo."""
    # the logo's own coordinates run 0..32, as in the SVG favicon
    if maskable:
        scale, offset = size * 0.6 / 32, size * 0.2
    else:
        scale, offset = size / 32, 0.0
    pixel = 1 / scale  # one pixel, in logo units

    rows = []
    for y in range(size):
        row = bytearray([0])  # PNG filter: none
        for x in range(size):
            u = (x + 0.5 - offset) / scale
            v = (y + 0.5 - offset) / scale
            color = (0.0, 0.0, 0.0, 0.0)
            if maskable:
                color = _over(color, PAPER, 1.0)
            page = _rounded_rect(u, v, 3, 2, 29, 30, 6)
            color = _over(color, PAPER, _fill(page, pixel))
            # the margin line, only inside the page
            margin = _stroke(_segment(u, v, 10, 2, 10, 30), 1.0, pixel)
            color = _over(color, MARGIN, _fill(page + 1, pixel) * margin)
            color = _over(color, PEN, _stroke(abs(page), 1.0, pixel))
            tick = min(_segment(u, v, 14, 16, 17, 19), _segment(u, v, 17, 19, 24, 12))
            color = _over(color, PEN, _stroke(tick, 1.5, pixel))
            row += bytes(round(channel) for channel in color)
        rows.append(bytes(row))
    return _png(size, size, b"".join(rows))


def _fill(distance: float, pixel: float) -> float:
    return min(1.0, max(0.0, 0.5 - distance / pixel))


def _stroke(distance: float, half_width: float, pixel: float) -> float:
    return _fill(distance - half_width, pixel)


def _rounded_rect(u, v, left, top, right, bottom, radius) -> float:
    cx, cy = (left + right) / 2, (top + bottom) / 2
    hx, hy = (right - left) / 2 - radius, (bottom - top) / 2 - radius
    dx, dy = abs(u - cx) - hx, abs(v - cy) - hy
    outside = math.hypot(max(dx, 0), max(dy, 0))
    return outside + min(max(dx, dy), 0) - radius


def _segment(u, v, x1, y1, x2, y2) -> float:
    px, py, ex, ey = u - x1, v - y1, x2 - x1, y2 - y1
    t = max(0.0, min(1.0, (px * ex + py * ey) / (ex * ex + ey * ey)))
    return math.hypot(px - ex * t, py - ey * t)


def _over(below, rgb, alpha):
    """``rgb`` at ``alpha`` painted over a premultiplied-free RGBA colour."""
    if alpha <= 0:
        return below
    r, g, b, a = below
    base = a / 255
    out = alpha + base * (1 - alpha)
    if out == 0:
        return (0.0, 0.0, 0.0, 0.0)
    mix = [(c * alpha + d * base * (1 - alpha)) / out for c, d in zip(rgb, (r, g, b), strict=True)]
    return (*mix, out * 255)


def _png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
