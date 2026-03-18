# Build Guide — MikroTik Auto Login

## 🐧 Linux — Standalone Binary

```bash
cd /home/parmanand/Desktop/login_automation/mikrotik_auto_login
source venv/bin/activate
pip install pyinstaller
pyinstaller mikrotik.spec
```
**Output:** `dist/MikroTikAutoLogin` (single executable, no Python needed)

---

## 🪟 Windows — .exe

> **Run on a Windows machine** (copy project folder to Windows first)

```batch
cd mikrotik_auto_login
pip install pyinstaller kivy requests beautifulsoup4 cryptography
pyinstaller mikrotik.spec
```
**Output:** `dist\MikroTikAutoLogin.exe`

> **Note:** If icon error → convert `data/icon.png` to `data/icon.ico` using any online converter, then update `mikrotik.spec` icon path.

---

## 🤖 Android — APK

> **Run on Linux host only**

### One-time system setup (Ubuntu/Debian):
```bash
sudo apt install -y git zip unzip python3-pip autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo5 cmake libffi-dev libssl-dev
pip install buildozer cython
```

### Build APK:
```bash
cd /home/parmanand/Desktop/login_automation/mikrotik_auto_login
source venv/bin/activate
buildozer android debug
```
**Output:** `bin/mikrotikautologin-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`

> ⚠️ First build downloads Android SDK/NDK (~3GB) and takes **20-40 minutes**.

### Deploy to phone (USB + USB Debugging enabled):
```bash
buildozer android deploy run
```

### Or install manually:
```bash
adb install bin/*.apk
```

---

## Release APK (signed, for Play Store / distribution)

```bash
buildozer android release
# Then sign with jarsigner or apksigner
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `kivy` import error on PyInstaller | Run `pip install kivy[base]` |
| Android build: `sdk not found` | Run `buildozer android debug` again (auto-downloads) |
| Android build: NDK error | Set `android.ndk = 25b` in buildozer.spec (already done) |
| App crashes on phone | Run `buildozer android logcat` to see error |
