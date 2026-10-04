# Android Gradle Declarative Plugin Migration & Build Configuration

## Overview
This document records the migration of the Android project configuration for **AI-Powered Personal Nutrition & Energy Balance Coach** (`com.bmsce.aai.nutritioncoach`) to Flutter's current declarative Gradle Plugin DSL in compliance with Flutter 3.47.5+.

---

## 1. Problem Statement
When building Android APK with Flutter 3.47.5+, the build failed with:
```
You are applying Flutter's app_plugin_loader Gradle plugin imperatively using the apply script method, which is not possible anymore.
```
This was caused by the deprecated `apply from: "$flutterSdkPath/packages/flutter_tools/gradle/app_plugin_loader.gradle"` in `android/settings.gradle`.

---

## 2. Declarative Plugin DSL Migration

### A. `android/settings.gradle`
Migrated from imperative script application to declarative `pluginManagement` and `plugins` blocks:
- **`pluginManagement`**: Includes Flutter tools Gradle build:
  ```groovy
  pluginManagement {
      def flutterSdkPath = {
          def properties = new Properties()
          file("local.properties").withInputStream { properties.load(it) }
          def flutterSdkPath = properties.getProperty("flutter.sdk")
          assert flutterSdkPath != null : "flutter.sdk not set in local.properties"
          return flutterSdkPath
      }()

      includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

      repositories {
          google()
          mavenCentral()
          gradlePluginPortal()
      }
  }
  ```
- **Declarative `plugins`**:
  ```groovy
  plugins {
      id "dev.flutter.flutter-plugin-loader" version "1.0.0"
      id "com.android.application" version "9.1.0" apply false
      id "org.jetbrains.kotlin.android" version "2.4.0" apply false
  }
  ```
- Removed the legacy `app_plugin_loader.gradle` line.

### B. `android/app/build.gradle`
- Applied modern declarative plugins:
  ```groovy
  plugins {
      id "com.android.application"
      id "kotlin-android"
      id "dev.flutter.flutter-gradle-plugin"
  }
  ```
- Retained full application properties and dependencies:
  - `namespace`: `com.bmsce.aai.nutritioncoach`
  - `applicationId`: `com.bmsce.aai.nutritioncoach`
  - `minSdkVersion`: `26` (required for Health Connect)
  - `targetSdkVersion`: `34`
  - `compileSdkVersion`: `36` (satisfying latest Android SDK and transitive plugin requirements)
  - Java 17 compatibility with desugaring enabled
  - Retained `androidx.health.connect:connect-client:1.1.0-alpha07`

### C. `android/gradle.properties`
- Added `kotlin.incremental=false` to avoid Windows cross-drive file lock and incremental caching issues between workspace (`E:`) and pub cache (`C:`).

---

## 3. Preserved Features and Hardware Integrations
- **Android Health Connect**:
  - Permissions: `READ_STEPS`, `READ_TOTAL_CALORIES_BURNED`, `READ_ACTIVE_CALORIES_BURNED`, `READ_EXERCISE`, `READ_HEART_RATE`, `READ_DISTANCE`.
  - Package query: `com.google.android.apps.healthdata`.
  - Intent filters: `androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE`.
- **Speech-to-Text (STT)**:
  - Permission: `android.permission.RECORD_AUDIO`.
- **Local Notifications & WorkManager**:
  - Permissions: `POST_NOTIFICATIONS`, `RECEIVE_BOOT_COMPLETED`, `WAKE_LOCK`.

---

## 4. Native Toolchain (NDK & CMake)
- Transitive packages (`jni-1.0.3`) require Android NDK (`build/cmake/android.toolchain.cmake`) for native compilation.
- Installed Android SDK platforms (34, 36), build-tools (34.0.0), and NDK `28.2.13676358` to ensure reproducible native compilation.
