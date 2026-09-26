"""Generate standard Flutter native runners, then apply development permissions."""
from pathlib import Path
import plistlib
import shutil
import subprocess

root = Path(__file__).resolve().parent
flutter = shutil.which("flutter")
if not flutter:
    raise SystemExit("Install Flutter and add flutter/bin to PATH, then rerun this script.")
subprocess.run([flutter, "create", "--platforms=android,ios", "--project-name=onion_quality_analyzer", "."], cwd=root, check=True)
manifest = root / "android/app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")
if 'android.permission.INTERNET' not in text:
    text = text.replace('<application', '<uses-permission android:name="android.permission.INTERNET"/>\n    <application', 1)
manifest.write_text(text, encoding="utf-8")
# HTTP access is permitted only for Android debug builds.
debug = root / "android/app/src/debug/AndroidManifest.xml"
debug.parent.mkdir(parents=True, exist_ok=True)
debug.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><uses-permission android:name="android.permission.INTERNET"/><application android:usesCleartextTraffic="true"/></manifest>', encoding="utf-8")
plist = root / "ios/Runner/Info.plist"
with plist.open("rb") as handle:
    data = plistlib.load(handle)
data.update(NSCameraUsageDescription="Photograph onions for quality assessment.",
            NSPhotoLibraryUsageDescription="Select an onion photo for quality assessment.",
            NSLocalNetworkUsageDescription="Connect to the onion analysis backend on your local network.")
# iOS physical devices should use an HTTPS backend. No global ATS exception.
with plist.open("wb") as handle:
    plistlib.dump(data, handle)
print("Native runners generated. Run flutter pub get, flutter analyze, and flutter run.")
