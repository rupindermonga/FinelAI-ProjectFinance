# Finel AI Projects — Mobile App Setup Guide

The web app is already a full PWA (installable, offline-capable). This guide explains how to
wrap it into native iOS and Android apps using Capacitor.

## Prerequisites

- **Node.js 18+** (https://nodejs.org)
- **Apple Developer Account** ($99/year) — for iOS
- **Xcode 15+** on macOS — for iOS builds
- **Google Play Developer Account** ($25 one-time) — for Android
- **Android Studio** — for Android builds

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Add native platforms
npx cap add ios
npx cap add android

# 3. Sync web assets to native projects
npx cap sync

# 4. Open in native IDE
npx cap open ios      # Opens Xcode
npx cap open android  # Opens Android Studio
```

## iOS Distribution

1. Open Xcode after `npx cap open ios`
2. Set your Team (Apple Developer Account) in Signing & Capabilities
3. Set Bundle Identifier: `ai.finel.projects`
4. Archive → Distribute App → App Store Connect

## Android Distribution

1. Open Android Studio after `npx cap open android`
2. Generate a signed APK/AAB: Build → Generate Signed Bundle/APK
3. Upload to Google Play Console

## Live Server Mode (Development)

For development, point Capacitor to your local server instead of static files:

Edit `capacitor.config.json`, add:
```json
"server": {
  "url": "http://YOUR_SERVER_IP:8002",
  "cleartext": true
}
```

## Features available in native app

- ✅ GPS location on timecards and daily logs
- ✅ Native camera capture for site photos
- ✅ Push notifications (connected to backend notification system)
- ✅ Offline mode with background sync
- ✅ Biometric authentication (Face ID / Fingerprint)
- ✅ Haptic feedback on actions
- ✅ Native share sheet for reports/PDFs
- ✅ File download to device

## Minimum OS Requirements

- iOS 14+
- Android 7.0 (API 24)+
