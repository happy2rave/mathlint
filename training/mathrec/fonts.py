"""The open fonts printed formulas are typeset in.

Four math fonts (every symbol the recognizer knows) and two text fonts (the
digits and letters of a worksheet typed without a math editor). All under the
SIL Open Font License, except Latin Modern Math (GUST Font License); both allow
this use.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .download import fetch

_GOOGLE = "https://raw.githubusercontent.com/google/fonts/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/"


@dataclass(frozen=True)
class Font:
    name: str
    url: str
    sha256: str
    math: bool  # has every math symbol and the math italic letters

    def path(self) -> Path:
        return fetch(self.url, self.sha256, name=self.name)


FONTS = (
    Font(
        "STIXTwoMath-Regular.ttf",
        _GOOGLE + "ofl/stixtwomath/STIXTwoMath-Regular.ttf",
        "562551b15b836e6e01d1b7350909baf3c8c8d83260c1190fbf4544333e6936de",
        True,
    ),
    Font(
        "NotoSansMath-Regular.ttf",
        _GOOGLE + "ofl/notosansmath/NotoSansMath-Regular.ttf",
        "3f495fe933c06786e4d5f6d86b8ee70b6753a68ee3b9d87528726de0f6e2c47d",
        True,
    ),
    Font(
        "LibertinusMath-Regular.ttf",
        _GOOGLE + "ofl/libertinusmath/LibertinusMath-Regular.ttf",
        "6eaebb1260c45328a49299a614eb20cee6d0b5c2fbb0d48314def159e0715318",
        True,
    ),
    Font(
        "latinmodern-math.otf",
        "https://mirrors.ctan.org/fonts/lm-math/opentype/latinmodern-math.otf",
        "6075562b771f8b82f0c179e363389684f2dd09de30038269e2628e504bd7be0f",
        True,
    ),
    Font(
        "NotoSerif.ttf",
        _GOOGLE + "ofl/notoserif/NotoSerif%5Bwdth,wght%5D.ttf",
        "4d8e6761424656867019081a1a01336f3cb086982682698714054fc33f782713",
        False,
    ),
    Font(
        "NotoSans.ttf",
        _GOOGLE + "ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf",
        "bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d",
        False,
    ),
)

MATH_FONTS = [font for font in FONTS if font.math]
TEXT_FONTS = [font for font in FONTS if not font.math]
