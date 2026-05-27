[app]

title = AyoOS Launcher
package.name = ayooslauncher
package.domain = org.ayoos
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
requirements = python3,kivy,plyer,pyjnius,android
version = 1.0
versioncode = 1
orientation = portrait
android.permissions = QUERY_ALL_PACKAGES, EXPAND_STATUS_BAR, INTERNET
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31
android.add_activity = org.kivy.android.PythonActivity
android.activity_launch_mode = singleTask
android.intent_filters = <intent-filter> <action android:name="android.intent.action.MAIN"/> <category android:name="android.intent.category.HOME"/> <category android:name="android.intent.category.DEFAULT"/> </intent-filter>
fullscreen = 0
android.presplash_color = #1a1a1a
logcat_filters = *:S python:D