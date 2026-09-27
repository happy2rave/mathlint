# mathlint for Android and iOS

The apps are the web page in a [Capacitor](https://capacitorjs.com) shell: the
site that `scripts/build_web.py` builds is copied into `android/` and `ios/` as
it is, the math engine and the handwriting recognizer included, so the apps work
offline from the first launch. `web/native.js` is the only part of the page that
knows it is in an app (the back button, the status bar, no service worker).

## Building

You need Node 22, `uv`, and JDK 21 with the Android SDK (Android Studio) or
Xcode on a Mac.

```bash
cd app && npm ci && cd ..
uv run python scripts/build_app.py   # build the site, check it, `cap sync`
cd app
npx cap open android                 # Android Studio: Run
npx cap open ios                     # Xcode: Run
```

`build_app.py` refuses a site that lacks anything the app needs offline, and
writes mathlint's version (`src/mathlint/_version.py`) into both projects:
version 1.2.3 is version code 10203. `--icons` redraws the icons and launch
screens from the logo (`scripts/icons.py`).

From the command line:

```bash
cd app/android && ./gradlew assembleDebug        # app/build/outputs/apk/debug/
xcodebuild -project app/ios/App/App.xcodeproj -scheme App \
  -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

CI (`.github/workflows/apps.yml`) builds both on every change and starts each
in an emulator or simulator until the page says `mathlint: engine ready`.

## What is committed

The Android and iOS projects, with their icons, launch screens, permissions and
settings. Not committed: `node_modules/`, the copied site (`public/`) and the
files `cap sync` generates; each platform's `.gitignore` lists them.

Publishing — the stores' accounts, the signing key and the review — is in
[docs/app-stores.md](../docs/app-stores.md).
