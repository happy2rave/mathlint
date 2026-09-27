# v1.0 "App stores" — design

Date: 2026-09-27
Status: planned

## Goal

mathlint on Google Play and the App Store, built from the same code as the web
page, and a stable Python package on PyPI. The app is the page: everything it
needs, the math engine and the handwriting recognizer included, is inside it, so
it works offline from the first launch and never downloads anything.

## Decisions

- **Capacitor** wraps the built site. The page is not forked or rebuilt for the
  app: `_site` is copied into the Android and iOS projects as it is, and the
  same JavaScript notices it is inside an app and behaves like one.
- The app lives in `app/`, its own npm project with its own lock file (like
  `training/`), with the generated `android/` and `ios/` projects committed so
  that their settings, icons and permissions are reviewed like any other code.
- App id `io.github.happy2rave.mathlint`, name **mathlint**. Android 7.0 (API 24)
  and newer, iOS 15 and newer, phones and tablets.
- One permission to ask for: the camera, the first time the camera button is
  used. No accounts, no analytics, no ads, and nothing sent over the network.
- Free, with nothing to buy. The Buy Me a Coffee link is not shown inside the
  store apps: both stores require their own payment systems for payments made
  from an app, and mathlint charges for nothing.

## 1. The page, inside an app

`web/native.js` is the only place that knows about the app. On the web every one
of its functions does nothing.

- **Detecting the app.** Capacitor puts a `Capacitor` object on the page before
  it runs; `isNativePlatform()` and `getPlatform()` say which app it is, and
  `<html data-app="android">` (or `"ios"`) lets the stylesheet know.
- **No downloads, no service worker.** The files are already on the device, so
  the service worker is not registered, and About says that everything is inside
  the app. The recognizer (about 4 MB) ships in the app, so the camera and the
  pen work offline the first time they are opened.
- **Android's back button** does what it does in any app: it closes the camera,
  an open sheet or the pad (the same as Escape on a computer), then hides the
  keypad, then goes back to Solve, and only then leaves the app. Capacitor's App
  plugin reports the button; the choice is a small pure function with its own
  tests.
- **System bars.** The page draws edge to edge. Capacitor passes the size of the
  status bar, notch and gesture bar as CSS variables (`--safe-area-inset-*`);
  the stylesheet uses them when they are there and `env(safe-area-inset-*)`
  otherwise. The status bar's icons follow the chosen theme (light, dark or the
  system's).
- **Links** to the source, OpenStax and the licenses open in the phone's
  browser; Capacitor does that for every address outside the app.
- **Plugins without a bundler.** The page has no build step for JavaScript, so
  `native.js` talks to Capacitor's bridge directly (`nativePromise` and
  `nativeCallback`, which Capacitor's own `registerPlugin` uses), and only for
  plugins the bridge says are installed.

## 2. The native projects

- `app/capacitor.config.json` points Capacitor at `../_site`.
  `scripts/build_app.py` builds the site with its vendored engine, checks that
  the engine, the recognizer and the wheel are all in it, and runs `cap sync`.
- **Version.** The app's version is mathlint's version, from
  `src/mathlint/_version.py`: `versionName` and `MARKETING_VERSION` are
  `1.0.0`; `versionCode` and `CURRENT_PROJECT_VERSION` are
  `major·10000 + minor·100 + patch`. `build_app.py` writes them, and a test
  fails when they drift apart.
- **Icons,** drawn by `scripts/icons.py` from the same logo as the web icons:
  an Android adaptive icon (vector foreground on paper, and a monochrome layer
  for themed icons), PNG launcher icons for Android 7, and a 1024 px iOS icon
  with no transparency (App Store Connect refuses one with an alpha channel).
- **Launch screen.** The logo on paper, or on the dark background in the dark
  theme, instead of Capacitor's placeholder: a layer list on Android and a
  storyboard with a named colour on iOS.
- **Camera.** Android declares `CAMERA`, with the camera hardware optional so
  that tablets without one can still install the app. iOS gives the reason for
  the camera in each of the four languages (`InfoPlist.strings`), and declares
  those languages, which also makes the web view report the reader's language.
- **Languages.** The stores and the systems learn that the app speaks English,
  Romanian, Russian and Spanish (`CFBundleLocalizations` on iOS, a locale
  config on Android 13 and newer).

## 3. Building and testing

- **CI** (`.github/workflows/apps.yml`), on every change to the app or the page:
  - Android: a debug APK built with Gradle, then started in an emulator; the
    job waits for the page to say, in the device log, that the engine is ready.
  - iOS: a simulator build with Xcode, installed and started in the simulator,
    waiting for the same line.
  - The APK and the simulator app are kept as build artifacts.
- The page writes `mathlint: engine ready <version>` to the console once the
  engine has loaded. That one line proves the whole chain inside a web view:
  Pyodide, WebAssembly, SymPy and mathlint's wheel loaded from the app's files.
- **Releases** (`release.yml`, on a version tag):
  - Android: a signed App Bundle for Google Play and a signed APK attached to
    the GitHub release, when the signing key is in the repository's secrets.
    Upload to Google Play's internal testing track when `PLAY_PUBLISH` is `true`.
  - iOS: an archive signed through App Store Connect's API and uploaded to
    TestFlight when `APPSTORE_PUBLISH` is `true`.
  - Like PyPI today, each is switched off until the maintainer sets it up once.

## 4. The store listings

- `app/fastlane/metadata/` holds each store's listing in English, Romanian,
  Russian and Spanish, in the layout fastlane (and most store tools) read: name,
  short description, full description, keywords and release notes. A test holds
  each field to its store's limit.
- **Privacy policy.** Both stores ask for one. `web/privacy.html`, on the site
  in the four languages, says what the app does: nothing is collected, nothing
  leaves the device, photos are not kept, history stays in the app's own storage.
  About links to it.
- **Privacy answers.** Google Play's data safety form: no data collected or
  shared. App Store privacy: Data Not Collected. Both follow from the design
  and are recorded in `docs/app-stores.md` with the other one-time steps
  (developer accounts, the signing key, content ratings, screenshots).
- **Screenshots** of the real page at phone and tablet sizes, made by
  `scripts/screenshots.py` in a browser, in each language.

## 5. A stable Python package

- 1.0.0 is the first release on PyPI (`pip install mathlint`), published by the
  existing trusted-publishing job.
- The public API is what `mathlint.__all__` names — `check`, `solve`,
  `compute`, `analyze`, `compare`, their result types and errors — and the
  command line. A test holds the names and the signatures, so a change to them
  is a deliberate one, and from 1.0 on semantic versioning applies to them.
- `py.typed`, so type checkers read mathlint's annotations.
- Classifiers: "Production/Stable". The license is given only as the SPDX
  expression; a `License ::` classifier next to it is refused by PyPI's newer
  metadata rules.

## Out of scope

In-app purchases, accounts and sync, notifications, widgets, a layout of its
own for tablets, and F-Droid (which needs an open-source license). Sending the
apps to review is the maintainer's, from the stores' own consoles.
