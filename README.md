# MikroTik Hotspot Auto Login

Cross-platform automatic login app for MikroTik captive portals.
Supports **Windows**, **Linux**, and **Android** from a single Python codebase using **Kivy**.

---

## Features
- Requests-based direct POST login (no browser required)
- Optional Selenium headless fallback (desktop only)
- Cross-platform internet check (HTTP 204 + socket)
- Auto-reconnect with exponential backoff
- Fernet-encrypted credential storage
- Real-time log viewer
- Connection status, last login time, retry counter

---

## Project Structure

```
mikrotik_auto_login/
├── main.py             # Entry point
├── app_ui.py           # Kivy UI
├── login_engine.py     # Login logic (requests + Selenium fallback)
├── monitor.py          # Background thread monitor
├── config_manager.py   # Encrypted config persistence
├── logger.py           # Thread-safe log queue
├── utils.py            # Internet & portal detection
├── data/
│   └── config.json     # Auto-generated on first run
├── buildozer.spec      # Android build config
└── requirements.txt
```

---

## Installation

```bash
pip install -r requirements.txt
```

To enable Selenium (desktop only):
```bash
pip install selenium webdriver-manager
```

---

## Run

```bash
cd mikrotik_auto_login
python main.py
```

---

## Build

### Windows (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole \
  --name MikroTikAutoLogin \
  --add-data "data;data" \
  main.py
```
Output: `dist/MikroTikAutoLogin.exe`

---

### Linux (standalone binary)

```bash
pip install pyinstaller
pyinstaller --onefile \
  --name mikrotik_login \
  --add-data "data:data" \
  main.py
```
Output: `dist/mikrotik_login`

---

### Android (APK)

**Prerequisites:**
```bash
pip install buildozer
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip
```

**Build:**
```bash
cd mikrotik_auto_login
buildozer android debug
```
APK will be in `bin/mikrotikautologin-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`

**Deploy to connected device:**
```bash
buildozer android deploy run
```

---

## Configuration

All settings are saved automatically to `data/config.json`.
Credentials are encrypted with **Fernet** symmetric encryption.
The encryption key is stored in `data/.secret.key` — keep this file safe.

---

## Notes

- On Android, Selenium is automatically disabled.
- Headless mode toggle is hidden on Android (not applicable).
- The app uses `https://clients3.google.com/generate_204` for internet checks — no OS commands like `ping` are used.
# login_automation_sit
