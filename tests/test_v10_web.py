"""The v1.0 web page inside the Android and iOS apps.

The apps run this same page; ``web/native.js`` is the only script that knows
about them (its own behaviour is tested in ``web/tests/native.test.mjs``).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
APP = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "style.css").read_text(encoding="utf-8")

#: the line the app builds' smoke tests wait for in the device log
READY_LINE = "mathlint: engine ready "


def test_only_native_js_knows_about_the_apps():
    for script in WEB.rglob("*.js"):
        if "tests" in script.parts or script.name == "native.js":
            continue
        assert "Capacitor" not in script.read_text(encoding="utf-8"), script.name


def test_the_apps_register_no_service_worker():
    offline = APP.split("function setUpOffline()")[1].split("\nfunction ")[0]
    in_app = offline.index('if (nativePlatform()) return say("offline.app")')
    assert in_app < offline.index('.register("sw.js")')


def test_the_apps_show_no_payment_link():
    assert "[data-app] .support-link { display: none; }" in STYLE
    assert 'free.dataset.i18n = "about.freeApp";' in APP


def test_the_back_button_is_answered_in_the_app():
    assert "onBackButton(goBack)" in APP
    assert "backStep({" in APP


def test_safe_areas_come_from_capacitor_when_it_gives_them():
    for side in ("top", "bottom", "left", "right"):
        fallback = f"env(safe-area-inset-{side}, 0px)"
        assert f"--safe-{side}: var(--safe-area-inset-{side}, {fallback});" in STYLE
    # every inset the page uses goes through those variables
    assert not re.search(r"env\(safe-area-inset-\w+\)", STYLE)


def test_the_page_says_when_the_engine_is_ready():
    assert "console.info(`" + READY_LINE + "${version}`)" in APP


def test_native_js_is_stamped_like_the_other_scripts():
    build = (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
    assert '"native.js"' in build.split("_LOCAL_FILES = (")[1].split(")")[0]


def test_the_practice_row_does_not_widen_the_page():
    # the spoken words beside each problem are placed absolutely; without a
    # containing block inside the scrolling row they widened a phone's page,
    # which then panned sideways (in the apps too)
    row = STYLE.split(".practice-list {", 1)[1].split("}", 1)[0]
    assert "position: relative;" in row
    assert "overflow-x: auto;" in row
