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


# Handwriting-style fonts (OFL or Apache 2.0): letters, digits and punctuation
# written by many different hands, each glyph distorted when it is drawn.
HAND_FONTS = (
    Font(
        "hands/caveat.ttf",
        _GOOGLE + "ofl/caveat/Caveat%5Bwght%5D.ttf",
        "0bdb6b660482d31531b3945849fba5916b3ef8695da7024a9e6b9ee3c4157988",
        False,
    ),
    Font(
        "hands/kalam.ttf",
        _GOOGLE + "ofl/kalam/Kalam-Regular.ttf",
        "57cecb63d4608019371954274ae1d8c397764debd5b19d4a33c1efa4dc923c0b",
        False,
    ),
    Font(
        "hands/patrickhand.ttf",
        _GOOGLE + "ofl/patrickhand/PatrickHand-Regular.ttf",
        "0f173b3e6cb6d1af25babf7f0057c5ac4ee11f9992b0469bb817e967ef4ad0fc",
        False,
    ),
    Font(
        "hands/indieflower.ttf",
        _GOOGLE + "ofl/indieflower/IndieFlower-Regular.ttf",
        "ccc94b22b156e9c5dfe50fd051f01b097600b252c24473e624bb43a143140a94",
        False,
    ),
    Font(
        "hands/shadowsintolight.ttf",
        _GOOGLE + "ofl/shadowsintolight/ShadowsIntoLight.ttf",
        "1347863151acdc00fa281daaba1a3543dbce5870b55f9cf7479a15bb84007681",
        False,
    ),
    Font(
        "hands/gochihand.ttf",
        _GOOGLE + "ofl/gochihand/GochiHand-Regular.ttf",
        "c46b029ab4846b2935e301af0b2cf85a1d74d2858e6a33636a3e64cf3cc4696b",
        False,
    ),
    Font(
        "hands/architectsdaughter.ttf",
        _GOOGLE + "ofl/architectsdaughter/ArchitectsDaughter-Regular.ttf",
        "6159718a08898e34bc1cb7354086141a5f9a70b73e54dbec27ead0d59a697359",
        False,
    ),
    Font(
        "hands/handlee.ttf",
        _GOOGLE + "ofl/handlee/Handlee-Regular.ttf",
        "7b99c0f291b5d52e06c66498a1d0dd6dff45a32e32d13be089c60d2d8dc00445",
        False,
    ),
    Font(
        "hands/schoolbell.ttf",
        _GOOGLE + "apache/schoolbell/Schoolbell-Regular.ttf",
        "00ff6655a5eb1eb70d32f2b7351d1bcf3f45f3f9ca40fd5c0d25da79f7f82a50",
        False,
    ),
    Font(
        "hands/comingsoon.ttf",
        _GOOGLE + "apache/comingsoon/ComingSoon-Regular.ttf",
        "cf81388f587ff6122de1a705d1070b8f00abccdba66108509908b5d10715068c",
        False,
    ),
    Font(
        "hands/gloriahallelujah.ttf",
        _GOOGLE + "ofl/gloriahallelujah/GloriaHallelujah.ttf",
        "eb59f2762ce8785a292bebb2af3b3e6aa21454913d791f5f25441d1d57ead9fc",
        False,
    ),
    Font(
        "hands/neucha.ttf",
        _GOOGLE + "ofl/neucha/Neucha.ttf",
        "7927bd6ce090fa032857dcbc3ad0e8b765c462d0a72a8779068132496b4e087d",
        False,
    ),
    Font(
        "hands/shortstack.ttf",
        _GOOGLE + "ofl/shortstack/ShortStack-Regular.ttf",
        "9f0e16e8683b2dce66edd7c3340362b554326739fbac594cabc1e9442cf5e8cc",
        False,
    ),
    Font(
        "hands/reeniebeanie.ttf",
        _GOOGLE + "ofl/reeniebeanie/ReenieBeanie.ttf",
        "0ea608aa325bf9e11c9590cc0b63dcf7cd215e270784f1ebbe6fad4927b31ff8",
        False,
    ),
    Font(
        "hands/coveredbyyourgrace.ttf",
        _GOOGLE + "ofl/coveredbyyourgrace/CoveredByYourGrace.ttf",
        "8a7e5687a4f9aad95243eb28cdc624009a335e0de5175113bc5f1348a4d67fd7",
        False,
    ),
    Font(
        "hands/justanotherhand.ttf",
        _GOOGLE + "apache/justanotherhand/JustAnotherHand-Regular.ttf",
        "f1cd102ebacdb6388c879c9d481d63908ee0d5939a301415a78cdfdc752f79ea",
        False,
    ),
    Font(
        "hands/nanumpenscript.ttf",
        _GOOGLE + "ofl/nanumpenscript/NanumPenScript-Regular.ttf",
        "6f0d1ab29c7894010dc88831fb7a0a51edb79136e450344183de5b1a8b52bd43",
        False,
    ),
    Font(
        "hands/delius.ttf",
        _GOOGLE + "ofl/delius/Delius-Regular.ttf",
        "c0fd66626926b637d64eb13de013b3318dbd72cdf92c33e41a29a03828bab6f6",
        False,
    ),
    Font(
        "hands/sriracha.ttf",
        _GOOGLE + "ofl/sriracha/Sriracha-Regular.ttf",
        "c3128c30cb21e8724b792586c87059d1b5eceae10d9957ba2ab26c80bbed3669",
        False,
    ),
    Font(
        "hands/itim.ttf",
        _GOOGLE + "ofl/itim/Itim-Regular.ttf",
        "9164d7eb92ca717b53b07193e3445c96782222d24215151b8d2851b576b17645",
        False,
    ),
    Font(
        "hands/mali.ttf",
        _GOOGLE + "ofl/mali/Mali-Regular.ttf",
        "e3212f0f9be130743d32a4f174b7d79628daa5db0d72ca4c63c799ae465597bb",
        False,
    ),
    Font(
        "hands/sueellenfrancisco.ttf",
        _GOOGLE + "ofl/sueellenfrancisco/SueEllenFrancisco-Regular.ttf",
        "d6d72e046e8e92f659eacfb7457cf7e1f2142c112c3d8c43c0b5a3904a5c8621",
        False,
    ),
    Font(
        "hands/dekko.ttf",
        _GOOGLE + "ofl/dekko/Dekko-Regular.ttf",
        "e6b151a5bdc521833ceb9a4f8010195515259e9416abfe055cfd16adb2e1af42",
        False,
    ),
    Font(
        "hands/waitingforthesunrise.ttf",
        _GOOGLE + "ofl/waitingforthesunrise/WaitingfortheSunrise.ttf",
        "ac74e70390f5b1be6927c1e079bd6143821a362550b264c5eb7edde34f0899f4",
        False,
    ),
    Font(
        "hands/nothingyoucoulddo.ttf",
        _GOOGLE + "ofl/nothingyoucoulddo/NothingYouCouldDo.ttf",
        "1daf8cf79076bf59c5a9117b5efd6ecea35e57a05ef127fe4f95b072b8a5245d",
        False,
    ),
    Font(
        "hands/zeyada.ttf",
        _GOOGLE + "ofl/zeyada/Zeyada.ttf",
        "09f23d0d78b6e166ddb8480793bb550ab4c2aaf6602eda47a394fee93d2a9667",
        False,
    ),
    Font(
        "hands/kristi.ttf",
        _GOOGLE + "ofl/kristi/Kristi-Regular.ttf",
        "6725b7a28d9bd8761e2834a6ab380babe073678c6f42017fe576116b9d6fd2a0",
        False,
    ),
    Font(
        "hands/swankyandmoomoo.ttf",
        _GOOGLE + "ofl/swankyandmoomoo/SwankyandMooMoo.ttf",
        "a745effa8961790717966f7c69d96756a7abe2d334a08be333a656b7c54b627f",
        False,
    ),
    Font(
        "hands/shantellsans.ttf",
        _GOOGLE + "ofl/shantellsans/ShantellSans%5BBNCE,INFM,SPAC,wght%5D.ttf",
        "d98a7913853f78d71aa0b86daf66b5eddb5a3266c07bfd51ef70632b88c41084",
        False,
    ),
)
