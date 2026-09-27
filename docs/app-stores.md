# Publishing the apps

The Android and iOS apps are built from `app/` (see [app/README.md](../app/README.md)).
Everything the stores need that can live in the repository is here: the
listings in four languages, the privacy policy, screenshots made from the real
page, and release jobs that sign and upload. What only the maintainer can do —
the accounts, the keys and the review — is below, once, and then per release.

## Before the first release

### Google Play

1. **Developer account** at [play.google.com/console](https://play.google.com/console)
   (a one-time fee, and identity verification).
2. **Create the app:** *mathlint: Solve & Check Math*, default language English
   (United States), an app, free.
3. **The upload key.** Google Play keeps the key that signs the app for users
   (Play App Signing); you keep an *upload key*:

   ```bash
   keytool -genkeypair -v -keystore upload.jks -alias upload \
     -keyalg RSA -keysize 4096 -validity 10000
   ```

   Keep `upload.jks` and its passwords somewhere safe and backed up, never in
   the repository. If it is lost, Google Play can register a new one.
4. **Repository secrets** (Settings → Secrets and variables → Actions):
   `ANDROID_UPLOAD_KEYSTORE` (the output of `base64 -w0 upload.jks`),
   `ANDROID_UPLOAD_KEYSTORE_PASSWORD`, `ANDROID_UPLOAD_KEY_ALIAS` (`upload`) and
   `ANDROID_UPLOAD_KEY_PASSWORD`; and the **variable** `ANDROID_RELEASE` = `true`.
   From then on, every version tag builds a signed App Bundle and APK and
   attaches both to the GitHub release.
5. **The first bundle by hand.** Google Play's API cannot publish an app's
   first bundle: upload `mathlint-vX.Y.Z.aab` from the GitHub release in Testing →
   Internal testing.
6. **Uploads from CI (optional).** In Google Cloud, create a service account and
   enable the Google Play Android Developer API; invite the service account in
   the Play Console (Users and permissions) with permission to release. Add its
   JSON key as the secret `PLAY_SERVICE_ACCOUNT_JSON` and set the variable
   `PLAY_PUBLISH` = `true`: each tag then sends the bundle to internal testing.
7. **The store listing.** Main store listing, then a translation for Romanian,
   Russian, Spanish (Spain) and Spanish (Latin America). The texts are in
   `app/fastlane/metadata/android/<locale>/` (`title.txt`,
   `short_description.txt`, `full_description.txt`); `npm run screenshots` in
   `app/` makes the phone and tablet screenshots, the 512 px icon and the
   feature graphic in each locale's `images/` folder.
8. **App content.**
   - Privacy policy: `https://happy2rave.github.io/mathlint/privacy.html`
   - Ads: no. App access: everything, without logging in.
   - Data safety: no data collected, no data shared. (Photos are read on the
     device and not kept; nothing is sent anywhere.)
   - Content rating questionnaire: a reference and education app with none of
     the listed content: rated for everyone.
   - Target audience: 13 and over is the simple choice. Including younger
     children brings in the Families policy; mathlint would meet it (no ads, no
     data), but it asks for more declarations.
9. **Release:** promote the internal testing release to production and send it
   for review.

### App Store

1. **Apple Developer Program** membership (yearly fee).
2. **The bundle id:** Certificates, Identifiers & Profiles → Identifiers →
   `io.github.happy2rave.mathlint` (no extra capabilities).
3. **Create the app** in App Store Connect: iOS, *mathlint: Solve & Check Math*,
   primary language English (U.S.), that bundle id, SKU `mathlint`.
4. **An API key for CI:** Users and Access → Integrations → App Store Connect
   API → a team key with the Admin role (Xcode uses it to create the signing
   certificate and profile). Add the secrets `APPSTORE_API_KEY` (the whole
   `.p8` file), `APPSTORE_API_KEY_ID` and `APPSTORE_API_ISSUER_ID`, and the
   variables `APPLE_TEAM_ID` and `APPSTORE_PUBLISH` = `true`. Each tag then
   archives the app and sends it to TestFlight. Without CI: `npx cap open ios`,
   choose the team, Product → Archive → Distribute App.
5. **App information:** category Education (secondary: Reference). Content
   rights: the app shows third-party content with the rights to use it
   (OpenStax exercises, CC BY 4.0). Age rating: none of the listed content (4+).
6. **App Privacy:** Data Not Collected. Privacy policy URL as above.
7. **Pricing:** free, in every country and region.
8. **The version page:** the texts are in `app/fastlane/metadata/ios/<locale>/`
   (name, subtitle, description, keywords, promotional text, what's new, and
   the support and marketing URLs); the 6.9" iPhone and 13" iPad screenshots are
   in `app/fastlane/screenshots/<locale>/` after `npm run screenshots`. Choose
   the TestFlight build. Export compliance is already answered: the app uses no
   encryption (`ITSAppUsesNonExemptEncryption` in `Info.plist`).
9. **Review notes:** "mathlint works offline and needs no account. To try the
   camera, photograph a line of math such as x² − 5x + 6 = 0; the pen button
   reads handwriting." Then submit for review.

Both stores' texts can also be uploaded with fastlane (`fastlane supply` and
`fastlane deliver`, pointed at `app/fastlane/metadata/android` and
`app/fastlane/metadata/ios`).

## Every release

1. The version, as in [CONTRIBUTING.md](../CONTRIBUTING.md#releasing-maintainers):
   the apps take theirs from `src/mathlint/_version.py`, and version 1.2.3 is
   version code 10203.
2. What is new, in each language:
   `app/fastlane/metadata/android/<locale>/changelogs/<version code>.txt` (at most
   500 characters) and `app/fastlane/metadata/ios/<locale>/release_notes.txt`.
   The store tests check both.
3. Screenshots again when the page looks different: `npm run screenshots`.
4. Tag. The Release workflow publishes the GitHub release and, as far as each is
   switched on, PyPI, the Android bundle and APK, and TestFlight.
5. In the consoles: promote the Play release to production, and submit the
   TestFlight build for review.

## Good to know

- The app id `io.github.happy2rave.mathlint` can never change once published.
- The APK on GitHub is signed with the upload key and the Play Store's copy
  with Google's app signing key, so neither updates the other; switching means
  uninstalling first.
- The store apps show no Buy Me a Coffee link: both stores take payments only
  through their own systems, and mathlint sells nothing.
- Capacitor is updated all at once: every `@capacitor/*` in `app/package.json`
  to the same version, `npm install`, `npx cap sync`, then the Apps workflow.
