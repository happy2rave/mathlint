"""The v1.0 Android and iOS apps (``app/``): the web page in a Capacitor shell.

The native projects are committed, so their settings are checked here like any
other code: one app id everywhere, mathlint's own version, the icons that
``scripts/icons.py`` draws, and the camera permission explained in every
language the page speaks.
"""

import importlib.util
import json
import plistlib
import re
import struct
import sys
import time
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
ANDROID = APP / "android" / "app"
MANIFEST = (ANDROID / "src/main/AndroidManifest.xml").read_text(encoding="utf-8")
GRADLE = (ANDROID / "build.gradle").read_text(encoding="utf-8")
IOS = APP / "ios" / "App"
PROJECT = (IOS / "App.xcodeproj/project.pbxproj").read_text(encoding="utf-8")
INFO = plistlib.loads((IOS / "App/Info.plist").read_bytes())
CONFIG = json.loads((APP / "capacitor.config.json").read_text(encoding="utf-8"))
LANGUAGES = sorted(path.stem for path in (ROOT / "web/locales").glob("*.json"))


def _script(name: str):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))


build_app = _script("build_app")
wait_for_log = _script("wait_for_log")


def test_one_app_id_everywhere():
    app_id = CONFIG["appId"]
    assert app_id == "io.github.happy2rave.mathlint"
    assert f'applicationId "{app_id}"' in GRADLE
    assert f'namespace = "{app_id}"' in GRADLE
    assert set(re.findall(r"PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);", PROJECT)) == {app_id}
    activity = ANDROID / "src/main/java" / Path(*app_id.split(".")) / "MainActivity.java"
    assert f"package {app_id};" in activity.read_text(encoding="utf-8")


def test_the_apps_run_the_built_site():
    assert CONFIG["webDir"] == "../_site"
    required = " ".join(build_app.REQUIRED)
    for needed in ("pyodide.asm.wasm", "mathlint-*.whl", "sympy-", "recognizer.bin"):
        assert needed in required


def test_a_site_without_the_engine_is_refused(tmp_path):
    (tmp_path / "index.html").write_text("x", encoding="utf-8")
    missing = build_app.missing_from(tmp_path)
    assert "vendor/pyodide-*/pyodide.asm.wasm" in missing
    assert "recognizer/recognizer.bin" in missing
    assert "index.html" not in missing


def test_the_apps_carry_mathlints_version():
    version = build_app.mathlint_version()
    code = build_app.version_code(version)
    assert f'versionName "{version}"' in GRADLE
    assert f"versionCode {code}" in GRADLE
    assert set(re.findall(r"MARKETING_VERSION = ([^;]+);", PROJECT)) == {version}
    assert set(re.findall(r"CURRENT_PROJECT_VERSION = ([^;]+);", PROJECT)) == {str(code)}


def test_every_release_has_a_higher_version_code():
    assert build_app.version_code("0.12.0") == 1200
    assert build_app.version_code("1.0.0") == 10000
    assert build_app.version_code("1.2.3") == 10203
    assert build_app.version_code("1.0.0") > build_app.version_code("0.99.99")
    for bad in ("1.0", "1.0.0rc1", "1.100.0"):
        with pytest.raises(SystemExit):
            build_app.version_code(bad)


def test_versions_are_written_into_both_projects(tmp_path):
    for relative in (build_app.ANDROID_GRADLE, build_app.IOS_PROJECT):
        target = tmp_path / relative
        target.parent.mkdir(parents=True)
        target.write_text((APP / relative).read_text(encoding="utf-8"), encoding="utf-8")
    build_app.write_versions(tmp_path, "2.3.4")
    gradle = (tmp_path / build_app.ANDROID_GRADLE).read_text(encoding="utf-8")
    project = (tmp_path / build_app.IOS_PROJECT).read_text(encoding="utf-8")
    assert 'versionName "2.3.4"' in gradle and "versionCode 20304" in gradle
    assert "MARKETING_VERSION = 2.3.4;" in project
    assert "CURRENT_PROJECT_VERSION = 20304;" in project
    assert "MARKETING_VERSION = 1.0;" not in project


def _png_header(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, _depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type


#: cheap enough to draw again in a test; the others are checked by size
_REDRAWN = ("drawable/", "mipmap-mdpi/", "mipmap-hdpi/", "splash@1x")


def test_the_icons_are_the_ones_icons_py_draws():
    for path, draw in build_app.icon_files().items():
        committed = APP / path
        assert committed.exists(), path
        if not any(part in str(path) for part in _REDRAWN):
            continue
        content = draw()
        if isinstance(content, str):
            assert committed.read_text(encoding="utf-8") == content, path
        else:
            assert committed.read_bytes() == content, path


def test_every_native_xml_file_parses():
    files = [
        *(APP / "android").rglob("*.xml"),
        IOS / "App/Base.lproj/LaunchScreen.storyboard",
        IOS / "App/Base.lproj/Main.storyboard",
    ]
    for path in files:
        if "build" in path.relative_to(APP).parts:
            continue
        ElementTree.parse(path)  # raises on what aapt or Xcode would refuse, "--" in a comment


def test_the_icons_have_the_sizes_their_stores_ask_for():
    res = ANDROID / "src/main/res"
    for density, scale in build_app.DENSITIES.items():
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            size = round(48 * scale)
            assert _png_header(res / f"mipmap-{density}" / name)[:2] == (size, size)
    # App Store Connect refuses an icon with an alpha channel (colour type 6)
    icon = IOS / "App/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
    assert _png_header(icon) == (1024, 1024, 2)
    assets = json.loads(icon.with_name("Contents.json").read_text(encoding="utf-8"))
    assert [image["filename"] for image in assets["images"]] == ["AppIcon-1024.png"]


def test_the_adaptive_icon_has_every_layer():
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        icon = (ANDROID / "src/main/res/mipmap-anydpi-v26" / name).read_text(encoding="utf-8")
        assert '<foreground android:drawable="@drawable/ic_launcher_foreground"/>' in icon
        assert '<monochrome android:drawable="@drawable/ic_launcher_monochrome"/>' in icon
    background = (ANDROID / "src/main/res/values/ic_launcher_background.xml").read_text(
        encoding="utf-8"
    )
    assert "#FFFDF7" in background  # the logo's paper


def test_no_placeholder_from_the_capacitor_templates_is_left():
    committed = [
        path
        for path in [*(APP / "android").rglob("*"), *(APP / "ios").rglob("*")]
        if path.is_file() and "public" not in path.parts and "build" not in path.parts
    ]
    names = {path.name for path in committed}
    assert not any(name.startswith("splash-2732x2732") for name in names)
    assert "AppIcon-512@2x.png" not in names
    assert "ic_launcher_foreground.png" not in names
    assert "splash.png" not in names
    for path in committed:
        if path.suffix in {".java", ".kt", ".gradle", ".xml", ".swift", ".pbxproj"}:
            assert "com.getcapacitor.myapp" not in path.read_text(encoding="utf-8"), path


def test_the_launch_screens_follow_the_theme():
    night = (ANDROID / "src/main/res/values-night/colors.xml").read_text(encoding="utf-8")
    day = (ANDROID / "src/main/res/values/colors.xml").read_text(encoding="utf-8")
    style = (ROOT / "web/style.css").read_text(encoding="utf-8")
    assert "#F4F3EF" in day and "#f4f3ef" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "#0E1014" in night and "#0e1014" in style
    styles = (ANDROID / "src/main/res/values/styles.xml").read_text(encoding="utf-8")
    assert "@color/splash_background" in styles
    storyboard = (IOS / "App/Base.lproj/LaunchScreen.storyboard").read_text(encoding="utf-8")
    assert '<color key="backgroundColor" name="SplashBackground"/>' in storyboard
    assert 'contentMode="center"' in storyboard
    colors = json.loads(
        (IOS / "App/Assets.xcassets/SplashBackground.colorset/Contents.json").read_text(
            encoding="utf-8"
        )
    )
    assert any(color.get("appearances") for color in colors["colors"])


def test_the_camera_is_the_only_permission_asked_for():
    permissions = re.findall(r'uses-permission android:name="([^"]+)"', MANIFEST)
    assert permissions == ["android.permission.INTERNET", "android.permission.CAMERA"]
    # tablets without a camera can still install mathlint
    for feature in ("android.hardware.camera", "android.hardware.camera.autofocus"):
        assert f'<uses-feature android:name="{feature}" android:required="false" />' in MANIFEST
    reasons = [key for key in INFO if key.endswith("UsageDescription")]
    assert reasons == ["NSCameraUsageDescription"]


@pytest.mark.parametrize("lang", LANGUAGES)
def test_the_camera_is_explained_in_every_language(lang):
    strings = (IOS / "App" / f"{lang}.lproj" / "InfoPlist.strings").read_text(encoding="utf-8")
    reason = re.fullmatch(r'(?s)/\*.*?\*/\n"NSCameraUsageDescription" = "([^"]+)";\n', strings)
    assert reason, lang
    if lang == "en":
        assert reason[1] == INFO["NSCameraUsageDescription"]
    assert f"{lang}.lproj/InfoPlist.strings" in PROJECT


def test_the_apps_declare_the_languages_the_page_speaks():
    assert sorted(INFO["CFBundleLocalizations"]) == LANGUAGES
    regions = re.search(r"knownRegions = \(([^)]*)\);", PROJECT)[1]
    assert {lang for lang in LANGUAGES} <= {region.strip(" \n\t,") for region in regions.split()}
    config = (ANDROID / "src/main/res/xml/locales_config.xml").read_text(encoding="utf-8")
    assert sorted(re.findall(r'<locale android:name="(\w+)"/>', config)) == LANGUAGES
    assert 'android:localeConfig="@xml/locales_config"' in MANIFEST


def test_the_ios_app_tracks_nothing_and_collects_nothing():
    privacy = plistlib.loads((IOS / "App/PrivacyInfo.xcprivacy").read_bytes())
    assert privacy["NSPrivacyTracking"] is False
    assert privacy["NSPrivacyTrackingDomains"] == []
    assert privacy["NSPrivacyCollectedDataTypes"] == []
    assert "PrivacyInfo.xcprivacy in Resources" in PROJECT
    # no export-compliance question on every upload: the app encrypts nothing
    assert INFO["ITSAppUsesNonExemptEncryption"] is False
    assert INFO["UIRequiredDeviceCapabilities"] == ["arm64"]


def test_capacitor_is_pinned_to_one_version():
    package = json.loads((APP / "package.json").read_text(encoding="utf-8"))
    pinned = {**package["dependencies"], **package["devDependencies"]}
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", version) for version in pinned.values())
    core = pinned["@capacitor/core"]
    for name in ("@capacitor/android", "@capacitor/ios", "@capacitor/cli"):
        assert pinned[name] == core
    swift = (IOS / "CapApp-SPM/Package.swift").read_text(encoding="utf-8")
    assert f'capacitor-swift-pm.git", exact: "{core}"' in swift
    lock = json.loads((APP / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/@capacitor/core"]["version"] == core


def test_the_app_packages_stay_out_of_git():
    assert "app/node_modules/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_ci_waits_for_the_line_the_page_writes():
    workflow = (ROOT / ".github/workflows/apps.yml").read_text(encoding="utf-8")
    page = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'READY: "mathlint: engine ready"' in workflow
    assert "console.info(`mathlint: engine ready ${version}`)" in page
    assert f"APP_ID: {CONFIG['appId']}" in workflow


def test_waiting_for_a_line_in_a_log():
    ready = "mathlint: engine ready"
    says_it = "print('booting'); print('I/Capacitor/Console: mathlint: engine ready 1.0.0')"
    assert wait_for_log.wait_for([sys.executable, "-c", says_it], ready, timeout=60)
    assert not wait_for_log.wait_for([sys.executable, "-c", "print('booting')"], ready, 60)
    started = time.monotonic()
    silent = [sys.executable, "-c", "import time; time.sleep(60)"]
    assert not wait_for_log.wait_for(silent, ready, timeout=1)
    assert time.monotonic() - started < 30
