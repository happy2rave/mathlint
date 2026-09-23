"""The v0.11 web app: every word in four languages, and nothing left out.

The page names its words by key (``data-i18n`` in the HTML, ``t("...")`` in the
scripts); English is the source in ``web/locales/en.json``. Every key used must
exist in English, and every other language must have exactly the same keys, the
same ``{placeholders}`` and the same markup.
"""

import hashlib
import json
import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
LOCALES = WEB / "locales"
LANGUAGES = ("ro", "ru", "es")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPTS = {path.name: path.read_text(encoding="utf-8") for path in WEB.glob("*.js")}
ENGLISH = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))


def _load(lang: str) -> dict:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


def _used_keys() -> set[str]:
    keys = set(re.findall(r'data-i18n(?:-html|-aria-label|-title|-placeholder)?="([^"]+)"', HTML))
    for text in SCRIPTS.values():
        keys |= set(re.findall(r'\bt\("([a-zA-Z][\w.]*\w)"', text))
        for line in re.findall(r"dataset\.i18n = [^;]*;", text):
            keys |= set(re.findall(r'"([a-z]+\.[\w.]+)"', line))
        keys |= set(re.findall(r'"((?:keypad|engine|history|offline)\.[\w.]+)"', text))
    for verdict in ("OK", "WRONG", "WARNING", "UNSURE"):
        keys.add(f"verdict.{verdict}")
    for part in ("rule", "example", "mistake"):
        keys.add(f"steps.{part}")
    for name in ("solve-examples.json", "examples.json"):
        for example in json.loads((WEB / name).read_text(encoding="utf-8")):
            keys.add(f"example.{example['name']}")
            if "group" in example:
                keys.add(f"example.{example['group']}")
    return keys


def _fields(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


def _tags(text: str) -> list[str]:
    return re.findall(r"</?(\w+)", text)


def test_every_key_the_page_uses_is_in_english():
    missing = sorted(key for key in _used_keys() if key not in ENGLISH)
    assert missing == []


def test_english_has_no_unused_keys():
    unused = sorted(set(ENGLISH) - _used_keys())
    assert unused == []


@pytest.mark.parametrize("lang", LANGUAGES)
def test_every_language_has_the_same_keys(lang):
    assert sorted(_load(lang)) == sorted(ENGLISH)


@pytest.mark.parametrize("lang", LANGUAGES)
def test_a_translation_keeps_placeholders_and_markup(lang):
    for key, value in _load(lang).items():
        assert value.strip(), key
        assert _fields(value) == _fields(ENGLISH[key]), key
        assert sorted(_tags(value)) == sorted(_tags(ENGLISH[key])), key


def test_the_language_is_chosen_before_the_first_paint():
    assert 'localStorage.getItem("mathlint:lang")' in HTML
    assert 'name="language"' in HTML
    for lang in ("en", *LANGUAGES):
        assert f'value="{lang}"' in HTML


def test_every_request_carries_the_language():
    assert "lang: language()" in SCRIPTS["engine.js"]


def test_the_page_tests_are_not_published():
    build = (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
    assert 'ignore_patterns("tests")' in build


def test_history_is_kept_on_the_device_and_only_for_what_the_reader_asked():
    assert 'id="history-sheet"' in HTML
    assert 'id="open-history"' in HTML
    app = SCRIPTS["app.js"]
    assert app.count("historyStore.add(") == 3  # solve, check and work out
    # runs made on the reader's behalf stay out of it
    assert "check({ record: false })" in app
    assert "solve({ record: false })" in app
    assert "showSteps({ record: false })" in app
    assert '"history.js"' in (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")


def _scripts_module(name: str):
    import importlib.util
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module  # dataclasses look their module up
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))


def test_the_page_loads_nothing_from_other_sites():
    # links a person follows are fine; anything the page itself fetches is not
    loaded = re.findall(r'<(?:script|link)\b[^>]*(?:src|href)="(https?://[^"]+)"', HTML)
    assert loaded == []
    for name, text in SCRIPTS.items():
        assert not re.search(r'(?:import|from|fetch\()\s*\(?\s*["\']https?://', text), name
        assert "cdn.jsdelivr" not in text and "googleapis" not in text, name


def test_every_vendored_path_the_page_names_is_vendored():
    vendor = _scripts_module("vendor")
    folders = {folder for tarball in vendor.TARBALLS for folder in tarball.files.values()}
    named = re.findall(r"vendor/([\w.-]+)/", HTML + "".join(SCRIPTS.values()))
    assert named
    for folder in named:
        assert folder in folders or folder == "fonts", folder


def test_the_app_can_be_installed():
    manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert '<link rel="manifest" href="manifest.webmanifest">' in HTML
    build = _scripts_module("build_web")
    drawn = {name for name, _, _ in build.ICONS}
    for icon in manifest["icons"]:
        assert icon["src"].removeprefix("icons/") in drawn
    assert {icon["purpose"] for icon in manifest["icons"]} == {"any", "maskable"}
    assert "apple-touch-icon.png" in drawn and 'href="icons/apple-touch-icon.png"' in HTML


def test_an_icon_is_a_png_of_the_right_size():
    icons = _scripts_module("icons")
    data = icons.draw_icon(48, maskable=True)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (48, 48)


def test_a_download_that_does_not_match_its_pin_is_refused():
    vendor = _scripts_module("vendor")
    with pytest.raises(SystemExit):
        vendor._verify("x", b"data", integrity="sha512-AAAA", sha256="")
    with pytest.raises(SystemExit):
        vendor._verify("x", b"data", integrity="", sha256="00")
    vendor._verify("x", b"data", integrity="", sha256=hashlib.sha256(b"data").hexdigest())


def test_the_service_worker_keeps_every_file_of_this_build(tmp_path):
    build = _scripts_module("build_web")
    (tmp_path / "sw.js").write_text((WEB / "sw.js").read_text(encoding="utf-8"), encoding="utf-8")
    for name in (
        "index.html",
        "app.js",
        "vendor/pyodide/python_stdlib.zip",
        "vendor/katex/LICENSE",
        "vendor/pyodide/pyodide.mjs.map",
    ):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x", encoding="utf-8")
    files = build.write_service_worker(tmp_path, "abc123")
    assert files == ["./", "app.js", "index.html", "vendor/pyodide/python_stdlib.zip"]
    worker = (tmp_path / "sw.js").read_text(encoding="utf-8")
    assert 'const VERSION = "abc123";' in worker
    assert '"vendor/pyodide/python_stdlib.zip"' in worker
    assert "__PRECACHE__" not in worker


def test_a_new_version_waits_for_the_reader():
    app = SCRIPTS["app.js"]
    assert 'navigator.serviceWorker\n    .register("sw.js")' in app
    assert 'postMessage("skip-waiting")' in app
    # the worker's own URL never changes, so the browser can see a new build
    build = (ROOT / "scripts" / "build_web.py").read_text(encoding="utf-8")
    assert '"sw.js"' not in build.split("_LOCAL_FILES = (")[1].split(")")[0]
    assert "self.skipWaiting()" in SCRIPTS["sw.js"]
    # a new build must not precache the last build's files from the HTTP cache
    assert 'cache: "reload"' in SCRIPTS["sw.js"]


def test_the_budgets_count_what_blocks_the_first_paint():
    budget = _scripts_module("budget")
    assert budget.blocking_stylesheets(HTML) <= budget.BLOCKING_STYLESHEETS
    page = '<head><link rel="stylesheet" href="a.css"><link rel="icon" href="x"></head>'
    assert budget.blocking_stylesheets(page + '<body><link rel="stylesheet" href="b"></body>') == 1
    assert budget.Measure("x", 2, 1, " s").line().startswith("OVER")
