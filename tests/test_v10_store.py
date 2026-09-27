"""The v1.0 store listings and privacy policy.

The listings live in ``app/fastlane/metadata`` in the layout fastlane reads:
``android/<locale>/`` for Google Play and ``ios/<locale>/`` for the App Store.
Each store refuses a field over its limit, so the limits are held here.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
METADATA = ROOT / "app" / "fastlane" / "metadata"
PRIVACY_URL = "https://happy2rave.github.io/mathlint/privacy.html"

#: every language the page speaks, and the store locales that show it
PLAY = {"en": ["en-US"], "ro": ["ro"], "ru": ["ru-RU"], "es": ["es-ES", "es-419"]}
APPLE = {"en": ["en-US"], "ro": ["ro"], "ru": ["ru"], "es": ["es-ES", "es-MX"]}

#: Google Play's limits, in characters
PLAY_LIMITS = {"title.txt": 30, "short_description.txt": 80, "full_description.txt": 4000}
#: the App Store's limits, in characters
APPLE_LIMITS = {
    "name.txt": 30,
    "subtitle.txt": 30,
    "keywords.txt": 100,
    "promotional_text.txt": 170,
    "description.txt": 4000,
    "release_notes.txt": 4000,
}


def _text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n") and not text.endswith("\n\n"), path
    return text.rstrip("\n")


def _locales(stores: dict) -> list[str]:
    return [locale for locales in stores.values() for locale in locales]


def test_every_language_of_the_page_has_a_listing_in_both_stores():
    languages = sorted(path.stem for path in (ROOT / "web" / "locales").glob("*.json"))
    assert sorted(PLAY) == languages and sorted(APPLE) == languages
    assert sorted(path.name for path in (METADATA / "android").iterdir()) == sorted(_locales(PLAY))
    folders = {path.name for path in (METADATA / "ios").iterdir() if path.is_dir()}
    assert folders == set(_locales(APPLE))


@pytest.mark.parametrize("locale", _locales(PLAY))
def test_the_play_listing_fits(locale):
    folder = METADATA / "android" / locale
    for name, limit in PLAY_LIMITS.items():
        text = _text(folder / name)
        assert 0 < len(text) <= limit, (locale, name, len(text))
    notes = list((folder / "changelogs").glob("*.txt"))
    assert notes
    for path in notes:
        assert path.stem.isdigit(), path  # named by version code
        assert 0 < len(_text(path)) <= 500, path


@pytest.mark.parametrize("locale", _locales(APPLE))
def test_the_app_store_listing_fits(locale):
    folder = METADATA / "ios" / locale
    for name, limit in APPLE_LIMITS.items():
        text = _text(folder / name)
        assert 0 < len(text) <= limit, (locale, name, len(text))
    keywords = _text(folder / "keywords.txt").split(",")
    # a space after a comma wastes one of the hundred characters
    assert all(word == word.strip() and word for word in keywords), locale
    assert _text(folder / "privacy_url.txt") == PRIVACY_URL
    for name in ("support_url.txt", "marketing_url.txt"):
        assert _text(folder / name).startswith("https://"), (locale, name)


def test_the_app_store_categories():
    assert _text(METADATA / "ios" / "primary_category.txt") == "EDUCATION"
    assert _text(METADATA / "ios" / "copyright.txt").endswith("happy2rave")


def test_a_language_says_the_same_in_both_stores():
    for lang in PLAY:
        play = METADATA / "android" / PLAY[lang][0]
        apple = METADATA / "ios" / APPLE[lang][0]
        assert _text(play / "title.txt") == _text(apple / "name.txt")
        assert _text(play / "full_description.txt") == _text(apple / "description.txt")


def test_the_listings_sell_nothing():
    for path in METADATA.rglob("*.txt"):
        text = _text(path).lower()
        assert "coffee" not in text and "buymeacoffee" not in text, path
        assert not re.search(r"\b(premium|subscription|in-app purchase)\b", text), path


def test_the_privacy_policy_is_on_the_site_in_every_language():
    page = (ROOT / "web" / "privacy.html").read_text(encoding="utf-8")
    for lang in PLAY:
        assert f'<section id="{lang}" lang="{lang}">' in page
        assert f'href="#{lang}"' in page
    # it loads nothing from anywhere
    assert not re.search(r'<(?:script|link|img)\b[^>]*(?:src|href)="https?://', page)
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="privacy-link" href="privacy.html"' in index
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert f'const PRIVACY_URL = "{PRIVACY_URL}";' in app


def test_the_privacy_page_is_not_counted_as_the_apps_code():
    budget = (ROOT / "scripts" / "budget.py").read_text(encoding="utf-8")
    assert '_NOT_THE_PAGE = {"privacy.html"}' in budget


def test_store_screenshots_stay_out_of_git():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "app/fastlane/metadata/android/*/images/" in ignored
    assert "app/fastlane/screenshots/" in ignored


def test_the_release_jobs_stay_off_until_their_secrets_exist():
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "if: vars.ANDROID_RELEASE == 'true'" in release
    assert "if: vars.PLAY_PUBLISH == 'true'" in release
    assert "if: vars.APPSTORE_PUBLISH == 'true'" in release
    gradle = (ROOT / "app" / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    assert 'System.getenv("MATHLINT_UPLOAD_KEYSTORE")' in gradle
    assert "upload.jks" not in gradle  # the key is never in the repository


def test_this_release_says_what_is_new_in_every_store_and_language():
    version = re.search(r'"([\d.]+)"', (ROOT / "src/mathlint/_version.py").read_text("utf-8"))[1]
    major, minor, patch = map(int, version.split("."))
    code = major * 10000 + minor * 100 + patch  # scripts/build_app.py's version code
    for locale in _locales(PLAY):
        assert (METADATA / "android" / locale / "changelogs" / f"{code}.txt").exists(), locale
    for locale in _locales(APPLE):
        assert _text(METADATA / "ios" / locale / "release_notes.txt"), locale
