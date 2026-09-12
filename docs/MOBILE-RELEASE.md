# void --news Mobile Release Runbook

Practical steps to sign and ship the Capacitor iOS and Android apps to their
store test tracks. This is the operational counterpart to `APP-BUILD-GUIDE.md`
(which covers the general Capacitor build). Read that first for background;
this doc covers signing, CI, and distribution to real testers.

Related docs: `docs/APP-BUILD-GUIDE.md` (build basics), `docs/LAUNCH-PLAN.md`
Workstream D (release plan), `codemagic.yaml` (the CI config this doc drives).

The CEO develops on Windows and cannot run Xcode. iOS therefore builds on a
cloud Mac via Codemagic. Android is buildable locally on Windows, but the same
Codemagic workflow builds it too for a consistent, reproducible pipeline.

---

## 1. One-time accounts (manual, do these first)

These cost money and take time to approve, so start early.

- **Apple Developer Program**: 99 USD per year. Enroll at
  https://developer.apple.com/programs/. Approval can take 24 to 48 hours.
  Required for TestFlight and the App Store.
- **Google Play Developer**: 25 USD one time. Register at
  https://play.google.com/console/signup. Required for the Play Store and its
  internal testing track.

You do not need a paid Codemagic plan to start: the free tier includes monthly
build minutes that comfortably cover a solo dev's release cadence.

---

## 2. Android signing keystore (generate once, back up forever)

The keystore signs every Android release. If you lose it, you can never update
the app under the same listing again. Treat it like a master password.

Generate it locally (JDK 17 installed):

```
keytool -genkey -v -keystore void-release.keystore \
  -alias void -keyalg RSA -keysize 2048 -validity 10000
```

You will be prompted for a store password, a key password, and your name and
organization. Record all of it in a password manager.

**CRITICAL BACKUP WARNING.** Copy `void-release.keystore` and its passwords to
at least two offline, private locations (an encrypted USB drive and a password
manager vault, for example). Do NOT commit the keystore to git. Do NOT rely on
a single laptop. Losing this file means you can never push an update: you would
have to publish a brand new app listing and every existing install would be
orphaned.

### Local Gradle wiring (optional, for building on Windows)

The release signing config in `frontend/android/app/build.gradle` reads the
keystore from environment variables OR from a git-ignored
`frontend/android/keystore.properties` file. To build a signed AAB locally,
create `frontend/android/keystore.properties` (never commit it):

```
storeFile=../void-release.keystore
storePassword=YOUR_STORE_PASSWORD
keyAlias=void
keyPassword=YOUR_KEY_PASSWORD
```

Then `cd frontend/android && ./gradlew bundleRelease`. If neither the env vars
nor this file are present, the release build stays unsigned and debug builds
still work (the config is guarded so a missing keystore never breaks the build).

---

## 3. Codemagic setup

Codemagic reads `codemagic.yaml` at the repo root. It has two workflows:
`ios-capacitor` (cloud Mac to TestFlight) and `android-capacitor` (signed AAB to
the Play internal track).

### 3.1 Connect the repo

1. Sign in at https://codemagic.io with the GitHub account that owns this repo.
2. Add this repository as an app. Codemagic auto-detects `codemagic.yaml`.

### 3.2 App Store Connect API key (for iOS)

1. In App Store Connect: Users and Access, Integrations, App Store Connect API,
   create a key with the App Manager role. Download the `.p8` file (one download
   only). Note the Issuer ID and the Key ID.
2. In Codemagic: Team or user settings, Integrations, App Store Connect. Add the
   key. Name the integration exactly `app_store_connect` to match
   `codemagic.yaml`.
3. Create your app record in App Store Connect with the reverse-DNS bundle id
   (see section 5). Codemagic's automatic signing will create the certificate
   and provisioning profile for that bundle id on each build.

### 3.3 Variable group `appstore_credentials` (for iOS)

In Codemagic, app settings, Environment variables, create a group named
`appstore_credentials` containing:

- `BUNDLE_ID`: the reverse-DNS bundle id, recommended `com.void.news` (section 5).

### 3.4 Android keystore (for Android)

1. In Codemagic: app settings, Code signing identities, Android keystores.
   Upload `void-release.keystore`, enter the store password, key alias, and key
   password. Give the reference the name `android_keystore` to match
   `codemagic.yaml`.
2. Codemagic exposes the uploaded keystore to the build as `CM_KEYSTORE_PATH`,
   `CM_KEYSTORE_PASSWORD`, `CM_KEY_ALIAS`, and `CM_KEY_PASSWORD`. The
   `android-capacitor` workflow re-exports these under the `VOID_*` names that
   `build.gradle` reads. If you name things differently, adjust the "Write
   keystore properties for Gradle" step in `codemagic.yaml`.

### 3.5 Google Play service account (for Android publishing)

1. In the Google Play Console: Setup, API access. Link a Google Cloud project
   and create a service account with the Release Manager permission.
2. Download the service-account JSON.
3. In Codemagic, create a variable group named `google_play_credentials` with:
   - `GCLOUD_SERVICE_ACCOUNT_CREDENTIALS`: paste the full JSON (mark it secure).
   - `PACKAGE_NAME`: the Android applicationId, recommended `com.void.news`.

Note: Google Play requires the very first build of a new app to be uploaded
manually through the Play Console once. After that first manual upload,
Codemagic can publish to the internal track automatically.

---

## 4. The build-and-sync loop (after any web change)

The native apps wrap the static export in `frontend/out`. Any change to the web
frontend must be rebuilt and synced into the native projects before a release:

```
cd frontend
npm run build          # regenerates frontend/out
npx cap sync ios       # copies out/ into ios/, installs pods
npx cap sync android   # copies out/ into android/
```

In CI this happens automatically: each Codemagic workflow runs `npm run build`
then `npx cap sync <platform>` before building. You do not run these by hand for
a release; you run them locally only when testing on a simulator or device.

---

## 5. Bundle id / app id decision (surface before first submission)

`frontend/capacitor.config.ts` and both native projects currently use
`appId: 'void.news'`. That is not a reverse-DNS identifier, and both Apple and
Google expect reverse-DNS (for example `com.void.news`). App Store Connect will
likely reject `void.news`.

**Recommended action before the first store submission:**

1. Change `appId` in `frontend/capacitor.config.ts` to `com.void.news`.
2. Run `npx cap sync` so the native projects pick it up.
3. Update the iOS bundle id (`PRODUCT_BUNDLE_IDENTIFIER` in
   `frontend/ios/App/App.xcodeproj/project.pbxproj`) and the Android
   `applicationId` and `namespace` in `frontend/android/app/build.gradle` to
   `com.void.news`.
4. Set `BUNDLE_ID` (iOS group) and `PACKAGE_NAME` (Android group) in Codemagic
   to the same value.

This is a real decision item: changing the id later, after any store listing
exists, means a new listing. Decide now. This runbook keeps the id as a
variable so nothing is hard-coded to the wrong value in CI.

---

## 6. Versioning

- **Android** (`frontend/android/app/build.gradle`): bump `versionCode` (integer,
  must strictly increase on every Play upload) and `versionName` (user-facing
  string) before each release. Play rejects a duplicate `versionCode`.
- **iOS**: `MARKETING_VERSION` (user-facing) lives in the Xcode project. The
  build number is bumped automatically in CI using Codemagic's monotonic
  `BUILD_NUMBER` counter, so every TestFlight upload is unique without manual
  edits. Change `MARKETING_VERSION` in Xcode (or `project.pbxproj`) when you cut
  a new user-facing version.

Keep the two platforms' user-facing versions in step for sanity, but they are
independent numbers to the stores.

---

## 7. Distributing to friends (the test phase)

You do NOT need public store approval to put the app on friends' phones.

- **iOS TestFlight**: after `ios-capacitor` uploads a build, add testers in App
  Store Connect, TestFlight tab. Create an internal or external test group and
  invite by email. Internal testers (up to 100, must be on your team) get builds
  with no Apple review. External groups (up to 10,000) need a light Beta App
  Review, which is faster and separate from full App Store review.
- **Android internal testing**: after `android-capacitor` uploads the AAB to the
  internal track, add tester emails in the Play Console, Internal testing tab,
  and share the opt-in link. No public review; installs are available within
  minutes.
- **Fast Android sideload (optional)**: for an even faster path, build a signed
  APK locally (`./gradlew assembleRelease`) and send the `.apk` directly. Testers
  enable "install unknown apps" once. This bypasses the Play Console entirely for
  the earliest friends phase.

---

## 8. App Store Guideline 4.2 (minimum functionality) risk and rebuttal

A Capacitor app is a web view wrapper, and Apple can reject wrappers under
Guideline 4.2 as "not enough native functionality" or "just a website." This
does NOT affect TestFlight, so the friends phase is safe regardless. It only
gates full public App Store release.

Reduce the risk:

- Ship the native feel: launch/splash screen, home-screen icon, offline fallback
  (the existing `offline.html` and `sw.js` service worker), and portrait lock.
- Lean on real, app-like value in the review notes.

Rebuttal to have ready if rejected, framed around genuine functionality:

- **Daily brief**: an original, editorially generated daily read, not a
  reformatted website feed.
- **Audio (void --onair)**: a spoken daily brief with a native audio player and
  background playback, a real device capability.
- **Offline reading**: previously viewed content and the brief are cached and
  readable with no connection, via the service worker.
- **Share target and home-screen presence**: the app behaves as a first-class
  installed app, not a bookmark.

If rejected, reply in Resolution Center citing these four points and request a
re-review. Meanwhile TestFlight keeps the app in testers' hands.

---

## 9. Quick reference: what the user must do manually

- Buy the Apple (99 USD/yr) and Google (25 USD once) developer accounts.
- Generate the Android keystore and back it up offline in two places.
- Create the App Store Connect API key and the Google Play service account.
- Create the Codemagic integrations and variable groups named in section 3.
- Create the app records in App Store Connect and Play Console; do the first
  manual Play upload once.
- Decide the reverse-DNS bundle id (section 5) before first submission.
- Invite testers by email in TestFlight and Play internal testing.
- Bump versions before each release (section 6).
