"""The app's icons, drawn as PNGs without any imaging library.

The logo is a notebook page: paper with a pen-blue border, the red margin line,
and a tick. Shapes are signed distance functions, so every pixel is sampled once
and its edge is antialiased from its distance to the shape.

A "maskable" icon fills the whole square with paper and keeps the drawing in
the middle 60%, because a phone crops it to a circle or a squircle.

The Android and iOS apps get the same logo: Android's adaptive icon as a vector
drawable (``android_vector``), its older launcher icons and iOS's icon as PNGs.
"""

from __future__ import annotations

import math
import struct
import zlib

PAPER = (255, 253, 247)
PEN = (45, 70, 200)
MARGIN = (234, 165, 156)


def draw_icon(
    size: int,
    maskable: bool = False,
    *,
    circle: bool = False,
    content: float = 0.6,
    opaque: bool = False,
) -> bytes:
    """A ``size`` x ``size`` PNG of the logo.

    ``maskable`` fills the square with paper, ``circle`` a circle (Android's
    round launcher icon); either way the logo takes the middle ``content`` of
    it. ``opaque`` writes no alpha channel, which the App Store requires of an
    app's icon.
    """
    # the logo's own coordinates run 0..32, as in the SVG favicon
    if maskable or circle:
        scale, offset = size * content / 32, size * (1 - content) / 2
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
            elif circle:
                edge = math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2) - size / 2
                color = _over(color, PAPER, _fill(edge, 1.0))
            page = _rounded_rect(u, v, 3, 2, 29, 30, 6)
            color = _over(color, PAPER, _fill(page, pixel))
            # the margin line, only inside the page
            margin = _stroke(_segment(u, v, 10, 2, 10, 30), 1.0, pixel)
            color = _over(color, MARGIN, _fill(page + 1, pixel) * margin)
            color = _over(color, PEN, _stroke(abs(page), 1.0, pixel))
            tick = min(_segment(u, v, 14, 16, 17, 19), _segment(u, v, 17, 19, 24, 12))
            color = _over(color, PEN, _stroke(tick, 1.5, pixel))
            if opaque:
                color = _over((*PAPER, 255.0), color[:3], color[3] / 255)[:3]
            row += bytes(round(channel) for channel in color)
        rows.append(bytes(row))
    return _png(size, size, b"".join(rows), alpha=not opaque)


#: the logo as paths in its 0..32 coordinates, for vector drawables
_PAGE_PATH = "M9,2H23A6,6 0 0 1 29,8V24A6,6 0 0 1 23,30H9A6,6 0 0 1 3,24V8A6,6 0 0 1 9,2Z"
_MARGIN_PATH = "M10,3V29"  # inside the page's border, as draw_icon clips it
_TICK_PATH = "M14,16L17,19L24,12"


def android_vector(*, content: float, monochrome: bool = False) -> str:
    """One layer of Android's adaptive icon: a 108 dp vector drawable.

    The system masks the layer to a circle, a squircle or a rounded square and
    only promises the middle 66 dp, so the logo takes the middle ``content``.
    The monochrome layer (Android 13's themed icons) is the lines alone: the
    system tints whatever is drawn, so a filled page would hide the tick.
    """
    scale = 108 * content / 32
    offset = 108 * (1 - content) / 2

    def color(rgb):
        return "#FF000000" if monochrome else "#{:02X}{:02X}{:02X}".format(*rgb)

    paths = []
    if not monochrome:
        paths.append(f'<path android:fillColor="{color(PAPER)}" android:pathData="{_PAGE_PATH}"/>')
    paths += [
        f'<path android:strokeColor="{color(MARGIN)}" android:strokeWidth="2"'
        f' android:pathData="{_MARGIN_PATH}"/>',
        f'<path android:strokeColor="{color(PEN)}" android:strokeWidth="2"'
        f' android:pathData="{_PAGE_PATH}"/>',
        f'<path android:strokeColor="{color(PEN)}" android:strokeWidth="3"'
        ' android:strokeLineCap="round" android:strokeLineJoin="round"'
        f' android:pathData="{_TICK_PATH}"/>',
    ]
    body = "\n".join("        " + path for path in paths)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!-- drawn by scripts/icons.py: python scripts/build_app.py --icons -->\n"
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="108dp" android:height="108dp"\n'
        '    android:viewportWidth="108" android:viewportHeight="108">\n'
        f'    <group android:translateX="{offset:g}" android:translateY="{offset:g}"'
        f' android:scaleX="{scale:g}" android:scaleY="{scale:g}">\n'
        f"{body}\n"
        "    </group>\n"
        "</vector>\n"
    )


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


def _png(width: int, height: int, raw: bytes, alpha: bool = True) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    # 8-bit RGBA, or RGB
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
