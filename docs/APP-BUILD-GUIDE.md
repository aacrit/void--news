# void --news App Build Guide

Three distribution methods: PWA, iOS App Store, and Android Play Store/APK.

## 1. PWA (Progressive Web App) — Instant Deploy

### For Users:
1. Visit `https://void--news.pages.dev` (or your Cloudflare Pages URL)
2. iOS Safari → Share → Add to Home Screen
3. Android Chrome → ⋮ → Install app
4. App installs instantly, works offline via service worker

### For Developers:
Deploy to Cloudflare Pages. PWA manifest and service worker are already configured.

```bash
npm run build
# Deployed automatically by CI/CD
```

**Offline Features:**
- Service worker caches static assets (JS, CSS, fonts)
- API responses cached with network-first strategy
- Pages cached with network-first strategy
- Works offline for previously-visited articles

---

## 2. iOS App — App Store Distribution

### Prerequisites:
- macOS with Xcode 14+
- Apple Developer Account ($99/year)
- iOS 15+ target

### Build Steps:

```bash
cd frontend

# 1. Build Next.js static export
npm run build

# 2. Open iOS project in Xcode
npx cap open ios

# 3. In Xcode:
#    - Select "App" target (left sidebar)
#    - Go to "Signing & Capabilities"
#    - Select your Team (Apple Dev account)
#    - Update Bundle Identifier (e.g., com.void.news)
#    - Build: Cmd+B

# 4. Run on simulator or device
# 5. Archive and submit to App Store
```

### Configuration:
- **App ID:** `void.news` (in capacitor.config.ts)
- **Bundle Identifier:** Configure in Xcode (e.g., `com.yourcompany.void`)
- **Icons:** Auto-generated from icon-512.png
- **LaunchScreen:** Customizable in ios/App/App/Base.lproj/LaunchScreen.storyboard

### App Store Submission:
1. Create app in [App Store Connect](https://appstoreconnect.apple.com)
2. In Xcode: Product → Archive
3. Distribute via App Store Connect
4. Review typically takes 24-48 hours

---

## 3. Android App — Play Store + APK

### Prerequisites:
- Android Studio (latest)
- JDK 11+
- Android SDK 31+
- Google Play Developer Account ($25 one-time)

### Build Steps:

```bash
cd frontend

# 1. Build Next.js static export
npm run build

# 2. Open Android project in Android Studio
npx cap open android

# 3. In Android Studio:
#    - Build → Generate Signed Bundle/APK
#    - Create/select keystore (keep secure!)
#    - Choose "APK" for direct download or "Bundle" for Play Store
#    - Build

# 4. For Play Store: upload AAB (Android App Bundle)
# 5. For direct users: distribute APK from build/outputs/apk/
```

### Configuration:
- **App ID:** `void.news` (in capacitor.config.ts)
- **Package Name:** `void.news` (auto-generated from appId)
- **Icons:** Auto-generated from icon-512.png
- **Keystore:** Keep it safe! Used for all future updates.

### Play Store Submission:
1. Create app in [Google Play Console](https://play.google.com/console)
2. Upload signed AAB (from Android Studio build)
3. Review typically takes 2-4 hours

### Direct APK Distribution:
```bash
# Build APK
npx cap build android --release

# APK location: android/app/build/outputs/apk/release/app-release.apk
# Users: Download directly and install (Settings → Unknown Sources → Allow)
```

---

## 4. Syncing Web Updates to Native Apps

After updating web code:

```bash
npm run build
npx cap sync  # Copies updated web assets to ios/ and android/
npx cap open ios   # Xcode: archive + submit
npx cap open android  # Android Studio: build bundle
```

---

## 5. Build Automation (CI/CD)

### GitHub Actions Example:

```yaml
name: Build Native Apps
on:
  push:
    branches: [main]
    paths: [frontend/**]

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Build web
        run: cd frontend && npm install && npm run build
      
      - name: Sync iOS
        run: npx cap sync ios
      
      - name: Sync Android
        run: npx cap sync android
      
      - name: Build iOS (requires signing)
        run: |
          cd frontend/ios/App
          xcodebuild build -scheme App -configuration Release
```

---

## 6. Troubleshooting

### iOS Issues:
- **"Package.swift not found"**: Run `npx cap update ios`
- **"Bundle Identifier mismatch"**: Ensure it matches in Xcode and capacitor.config.ts
- **"Provisioning profile error"**: Check Apple Dev account has active profiles

### Android Issues:
- **"gradle not found"**: Set `ANDROID_HOME` environment variable
- **"Keystore password incorrect"**: Triple-check keystore creation
- **"APK unsigned"**: Use Android Studio "Generate Signed Bundle/APK" wizard

### General:
- Clear caches: `npm run build && npx cap sync`
- Check native logs: Xcode Console or Android Logcat
- Update Capacitor: `npm install @capacitor/core@latest`

---

## 7. Version Management

When releasing a new version:

1. Update `package.json` version
2. Update iOS version in Xcode (Build Settings)
3. Update Android versionCode/versionName in `android/app/build.gradle`
4. Rebuild and submit to stores
5. Tag release: `git tag -a v1.0.0`

---

## 8. Monitoring & Analytics

### In-App Analytics:
- Capacitor provides native hooks for Segment, Mixpanel, Firebase
- Add to `capacitor.config.ts` plugins section

### Crash Reporting:
- iOS: Xcode Organizer (automatic)
- Android: Google Play Console → Crashes & ANRs

---

## 9. Capabilities & Permissions

Currently enabled:
- Network (required)
- Local cache (via service worker)

Can add via Capacitor plugins:
- Camera (photo capture)
- Geolocation (location services)
- Push notifications
- Share sheet

---

## Useful Links

- [Capacitor Docs](https://capacitorjs.com)
- [Capacitor iOS Guide](https://capacitorjs.com/docs/ios)
- [Capacitor Android Guide](https://capacitorjs.com/docs/android)
- [App Store Connect](https://appstoreconnect.apple.com)
- [Google Play Console](https://play.google.com/console)

---

**Last Updated:** 2026-05-03
**Status:** iOS & Android projects initialized; awaiting manual signing + submission
