[app]
title = RPS 3D
package.name = rpsgame
package.domain = org.rps
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,wav,mp3,ttf,ogg
version = 1.0
requirements = python3,kivy,pillow,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET,VIBRATE
android.api = 33
android.minapi = 21
android.sdk_path = /data/data/com.termux/files/home/android-sdk
android.ndk_path = /data/data/com.termux/files/home/android-sdk/ndk/30.0.16248370
android.build_tools_version = 34.0.4
android.archs = arm64-v8a
android.accept_sdk_license = True
android.skip_update = True
android.wakelock = True
android.allow_backup = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
