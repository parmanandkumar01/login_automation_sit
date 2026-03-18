# MikroTik Auto Login — User Manual

**Developed by:** Parmanand Kumar | CSE Department | Batch 2022
**Application:** MikroTik Hotspot Auto Login
**Version:** 1.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation & First Run](#2-installation--first-run)
3. [Application UI Overview](#3-application-ui-overview)
4. [Settings Section](#4-settings-section)
5. [Automation Toggles](#5-automation-toggles)
6. [Advanced Settings](#6-advanced-settings)
7. [Connection Status Panel](#7-connection-status-panel)
8. [Action Buttons](#8-action-buttons)
9. [Live Log Viewer](#9-live-log-viewer)
10. [Status Indicators Explained](#10-status-indicators-explained)
11. [How Auto Login Works](#11-how-auto-login-works)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Introduction

**MikroTik Auto Login** is a desktop/Android application that automatically logs you into your MikroTik Hotspot (captive portal) without requiring you to open a browser every time.

### Key Features
| Feature | Description |
|---|---|
| Auto Login | Detects captive portal and logs in automatically |
| Auto Reconnect | Re-logs in if connection drops |
| Wrong WiFi Detection | Shows warning if you are not on MikroTik network |
| Live Log | Real-time log of all connection events |
| Credential Encryption | Password is stored securely on disk |
| Cross-Platform | Works on Linux, Windows, Android |

---

## 2. Installation & First Run

### Requirements
- Python 3.10+
- MikroTik WiFi network access
- A registered hotspot username and password

### Run the Application

```bash
# 1. Navigate to the project folder
cd /path/to/mikrotik_auto_login

# 2. Activate the virtual environment
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Start the app
python3 main.py
```

---

## 3. Application UI Overview

```
┌─────────────────────────────────────────────────────────┐
│  [Icon] MikroTik Auto Login          ● Status           │  ← Header Bar
│         Hotspot Connection Manager                       │
├────────┬────────┬────────┬────────────────────────────── │
│  NET   │  RTY   │  TIME  │  IP                          │  ← Quick Stats
├─────────────────────────────────────────────────────────┤
│  Settings                                               │  ← Settings Card
│   Router IP | Username | Password | Interval            │
│   Automation: Auto-Login | Auto-Reconnect               │
│   Advanced: Headless | Selenium | Start on Boot         │
├─────────────────────────────────────────────────────────┤
│  Connection Status                                      │  ← Status Card
│   Connection | Last Login | Retries                     │
├─────────────────────────────────────────────────────────┤
│   > Login Now       │   x Stop                         │  ← Action Buttons
│         * Save Settings                                  │
├─────────────────────────────────────────────────────────┤
│  Live Log                                               │  ← Log Viewer
│   [OK]   Internet check: OK (204)                       │
│   [WARN] MikroTik router not reachable                  │
├─────────────────────────────────────────────────────────┤
│  [Photo] Developed by                                   │  ← Developer Card
│          Parmanand Kumar | CSE | Batch 2022             │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Settings Section

These are the core connection settings. Fill them in before clicking **Login Now**.

### 4.1 Router IP
- **What it is:** The IP address of your MikroTik hotspot router.
- **Default:** `10.50.0.1` (check with your network admin if unsure)
- **Example:** `10.50.0.1` or `192.168.88.1`

> **Tip:** Open a browser and try visiting `http://10.50.0.1` when connected to the WiFi. If a login page appears, that's your Router IP.

---

### 4.2 Username
- **What it is:** Your hotspot login username (given by your ISP/college/admin).
- **Example:** `23105127904` (student ID or assigned username)

---

### 4.3 Password
- **What it is:** Your hotspot login password.
- The password is hidden by default (shown as `••••••••••`).
- Click **Show** to reveal the password.
- Click **Hide** to hide it again.

---

### 4.4 Check Interval (s)
- **What it is:** How often (in seconds) the app checks if you are still connected.
- **Minimum:** 5 seconds
- **Recommended:** 10–30 seconds
- **Example:** `10` = check every 10 seconds

> **Note:** Lower values = faster reconnect detection, but more network requests. Recommended: `10` for active use.

---

## 5. Automation Toggles

### 5.1 Auto-Login
| State | Behaviour |
|---|---|
| **ON** | App automatically attempts login when captive portal is detected |
| **OFF** | App only monitors — you must click "Login Now" manually |

**Recommended:** ON

---

### 5.2 Auto-Reconnect
| State | Behaviour |
|---|---|
| **ON** | If connection drops, auto-login retries automatically |
| **OFF** | Connection drop is only reported in the status, no retry |

**Recommended:** ON

---

## 6. Advanced Settings

> These settings are only visible on Desktop (Linux/Windows). On Android, they are hidden automatically.

### 6.1 Headless Mode
| State | Behaviour |
|---|---|
| **ON** | If Selenium fallback is used, the Chrome browser runs invisibly in background |
| **OFF** | Chrome browser window opens visibly (useful for debugging) |

**Recommended:** ON (no browser window popup)

---

### 6.2 Selenium Fallback
| State | Behaviour |
|---|---|
| **ON** | If the direct HTTP login fails, tries again using a real Chrome browser |
| **OFF** | Only uses direct HTTP login (faster, no Chrome needed) |

**Recommended:** OFF unless direct login is failing

> **Requirement:** Google Chrome must be installed for this to work.

---

### 6.3 Start on Boot
| State | Behaviour |
|---|---|
| **ON** | App starts automatically when your computer boots |
| **OFF** | You must start the app manually each time |

**Recommended:** ON if you want fully automatic operation

---

## 7. Connection Status Panel

Shows current connection state with color coding.

| Status Text | Color | Meaning |
|---|---|---|
| **Connected** | 🟢 Green | Internet is confirmed working |
| **Captive Portal Detected** | 🟡 Yellow | WiFi connected but login required |
| **Logging in...** | 🔵 Blue | Currently attempting login |
| **Not on MikroTik WiFi** | 🟠 Orange | Connected to a different WiFi — not your hotspot |
| **Offline — No Network** | 🔴 Red | No WiFi/network connection at all |
| **Login failed** | 🔴 Red | Login attempt failed (wrong password or portal error) |
| **Stopped** | ⚪ Grey | Monitoring was manually stopped |
| **Checking...** | 🟡 Yellow | Currently running a connection check |

### Status Panel Fields
- **Connection:** Current connection state
- **Last Login:** Date and time of the last successful login
- **Retries:** How many login attempts have been made in the current session

---

## 8. Action Buttons

### 8.1 `> Login Now`
- **What it does:** Immediately triggers a connection check and login attempt.
- **When to use:** When you just connected to the WiFi and want to log in right away (without waiting for the auto-check interval).
- **Also does:** Saves your current settings automatically before starting.

---

### 8.2 `x Stop`
- **What it does:** Stops the background monitoring thread entirely.
- **When to use:** When you want to pause the app from auto-logging in (e.g., switching networks).
- **After stopping:** Click "Login Now" again to resume monitoring.

---

### 8.3 `* Save Settings`
- **What it does:** Saves all current settings (IP, username, password, toggles) to disk.
- **When to use:** After making any changes to settings.
- **Note:** Settings are saved to `data/config.json` (password is encrypted).

> **Important:** Always click **Save Settings** after changing Router IP, Username, or Password, otherwise the changes are lost when you close the app.

---

## 9. Live Log Viewer

The **Live Log** panel at the bottom shows real-time events. Each line is color-coded:

| Color | Tag | Meaning |
|---|---|---|
| 🟢 Green | `[OK]` | Successful action (login OK, internet confirmed) |
| 🔴 Red | `[ERROR]` | Something went wrong |
| 🟠 Orange | `[WARN]` | Warning / non-critical issue |
| ⚪ Grey | `[INFO]` | Informational message |

### Sample Log Messages
```
[OK]   Internet check: OK (204)                 → Internet confirmed working
[OK]   Login successful via requests!            → Login succeeded
[WARN] Router 10.50.0.1 not reachable           → Not on MikroTik WiFi
[WARN] Captive portal detected, redirected to:  → Ready to login
[ERROR] Requests login error: timeout           → Network issue
[INFO]  Monitor thread started.                 → Monitoring began
[INFO]  Login attempt #1                        → First login retry
```

The log auto-scrolls to show the latest messages. Up to 300 lines are kept in memory.

---

## 10. Status Indicators Explained

### Header Quick-Stats Row

| Pill | Shows |
|---|---|
| **NET** | Current connection status (Connected / Stopped / Not on MikroTik WiFi) |
| **RTY** | Retry count for the current session |
| **TIME** | Time of last successful login |
| **IP** | Configured Router IP (from settings) |

### Header Status Dot (top-right)
- Small colored circle next to the status text.
- **Pulses** (fades in/out) when actively monitoring or logging in.
- **Solid** when connected or stopped.

---

## 11. How Auto Login Works

This flowchart shows what happens every time the check interval fires:

```
Every [interval] seconds:
        │
        ▼
Is 10.50.0.1 reachable on port 80?
        │
   NO ──┼──────────────────────────────► "Not on MikroTik WiFi" → STOP
        │
       YES
        │
        ▼
Is real internet available? (HTTP 204 check)
        │
   YES ─┼──────────────────────────────► "Connected" → STOP (no action needed)
        │
       NO
        │
        ▼
Is captive portal detected? (redirect check)
        │
   NO ──┼──────────────────────────────► "Offline — No Portal" → STOP
        │
       YES
        │
        ▼
POST credentials to http://10.50.0.1/login
        │
   SUCCESS ─────────────────────────────► "Connected" ✓
   FAILED ──────────────────────────────► "Login failed" → retry after backoff
```

**Exponential Backoff:** After repeated login failures, the app waits progressively longer between retries (up to 5 minutes maximum) to avoid locking your account.

---

## 12. Troubleshooting

### Problem: Status always shows "Not on MikroTik WiFi" even when connected

**Cause:** The Router IP might be wrong, or you are connected to a different WiFi.

**Fix:**
1. Open a browser
2. Visit `http://10.50.0.1` (or your college's hotspot IP)
3. If the login page loads, confirm the IP and update it in **Router IP** field
4. Click **Save Settings** then **Login Now**

---

### Problem: Status shows "Connected" but internet doesn't actually work

**This was a known bug — now fixed.** The old version used a socket test that could pass even without real internet. The new version uses an HTTP 204 check that only passes with real internet access.

---

### Problem: Login fails with the correct credentials

**Try:**
1. Open Chrome and try logging in manually at `http://10.50.0.1/login` to confirm credentials work
2. Enable **Selenium Fallback** → ON in Advanced settings
3. Disable **Headless Mode** → OFF so you can see the browser window

---

### Problem: App shows "Offline — No Network"

**Cause:** WiFi is not connected at all.

**Fix:** Connect to the MikroTik WiFi first and then click **Login Now**.

---

### Problem: App takes a long time to detect wrong WiFi

**Fix:** Lower the **Check Interval** to `5` seconds. The wrong-WiFi detection itself has a 3-second timeout.

---

*User Manual — MikroTik Hotspot Auto Login v1.0*
*Developed by Parmanand Kumar | CSE Department | Batch 2022*
