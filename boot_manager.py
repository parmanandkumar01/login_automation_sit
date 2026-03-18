"""
boot_manager.py
Cross-platform Start on Boot management.

Linux:   ~/.config/autostart/mikrotik-auto-login.desktop  (XDG autostart spec)
Windows: %APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup/MikrotikLogin.bat
"""

import os
import sys
import platform

import logger as log

APP_NAME    = "MikroTik Auto Login"
DESKTOP_ID  = "mikrotik-auto-login"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _project_root() -> str:
    """Return the absolute path to the project directory."""
    return os.path.dirname(os.path.abspath(__file__))


def _python_exe() -> str:
    """Return the Python interpreter currently running this app."""
    return sys.executable


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _is_windows() -> bool:
    return platform.system() == "Windows"


# ── Linux ─────────────────────────────────────────────────────────────────────

def _linux_desktop_path() -> str:
    autostart_dir = os.path.join(
        os.path.expanduser("~"), ".config", "autostart"
    )
    os.makedirs(autostart_dir, exist_ok=True)
    return os.path.join(autostart_dir, f"{DESKTOP_ID}.desktop")


def _linux_enable() -> tuple[bool, str]:
    path = _linux_desktop_path()
    root = _project_root()
    python = _python_exe()
    main_py = os.path.join(root, "main.py")

    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={python} {main_py}\n"
        f"Path={root}\n"
        "Icon=network-wireless\n"
        "Comment=MikroTik Hotspot Auto Login\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Hidden=false\n"
    )
    try:
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)
        log.success(f"Autostart enabled → {path}")
        return True, f"Autostart enabled:\n{path}"
    except Exception as e:
        log.error(f"Failed to create autostart entry: {e}")
        return False, f"Error: {e}"


def _linux_disable() -> tuple[bool, str]:
    path = _linux_desktop_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            log.info(f"Autostart entry removed: {path}")
            return True, "Autostart disabled."
        except Exception as e:
            log.error(f"Failed to remove autostart entry: {e}")
            return False, f"Error: {e}"
    return True, "Autostart already disabled."


def _linux_is_enabled() -> bool:
    return os.path.exists(_linux_desktop_path())


# ── Windows ───────────────────────────────────────────────────────────────────

def _windows_startup_path() -> str:
    base = os.environ.get(
        "APPDATA",
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    )
    startup_dir = os.path.join(
        base,
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    os.makedirs(startup_dir, exist_ok=True)
    return os.path.join(startup_dir, f"{DESKTOP_ID}.bat")


def _windows_enable() -> tuple[bool, str]:
    path = _windows_startup_path()
    root = _project_root()
    python = _python_exe()
    main_py = os.path.join(root, "main.py")

    # Hidden-window batch launcher so no console flashes on boot
    content = (
        "@echo off\n"
        f'cd /d "{root}"\n'
        f'start "" /B "{python}" "{main_py}"\n'
    )
    try:
        with open(path, "w") as f:
            f.write(content)
        log.success(f"Autostart enabled → {path}")
        return True, f"Autostart enabled:\n{path}"
    except Exception as e:
        log.error(f"Failed to create startup entry: {e}")
        return False, f"Error: {e}"


def _windows_disable() -> tuple[bool, str]:
    path = _windows_startup_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            log.info(f"Startup entry removed: {path}")
            return True, "Autostart disabled."
        except Exception as e:
            log.error(f"Failed to remove startup entry: {e}")
            return False, f"Error: {e}"
    return True, "Autostart already disabled."


def _windows_is_enabled() -> bool:
    return os.path.exists(_windows_startup_path())


# ── Public API ────────────────────────────────────────────────────────────────

def enable_autostart() -> tuple[bool, str]:
    """Register app to start on system login. Returns (success, message)."""
    if _is_linux():
        return _linux_enable()
    if _is_windows():
        return _windows_enable()
    return False, f"Start on Boot not supported on {platform.system()}."


def disable_autostart() -> tuple[bool, str]:
    """Remove autostart registration. Returns (success, message)."""
    if _is_linux():
        return _linux_disable()
    if _is_windows():
        return _windows_disable()
    return False, f"Start on Boot not supported on {platform.system()}."


def is_autostart_enabled() -> bool:
    """Check if autostart entry exists on disk."""
    if _is_linux():
        return _linux_is_enabled()
    if _is_windows():
        return _windows_is_enabled()
    return False


def sync_autostart(enabled: bool) -> tuple[bool, str]:
    """Enable or disable based on a boolean flag."""
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
