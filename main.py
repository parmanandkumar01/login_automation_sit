"""
main.py
Entry point for the Mikrotik Hotspot Auto Login App.
"""

import os
import sys

# Ensure the project root is on the Python path (needed by PyInstaller & Buildozer)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Kivy environment config (must be before kivy imports)
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

# ── Fix: prevent cursor movement from triggering scroll ───────────────────────
# Must be set BEFORE any kivy.* imports
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

# Prevent Kivy from hijacking the Linux touchpad as a raw multi-touch screen
try:
    for key, value in Config.items('input'):
        if 'probesysfs' in value or 'mtdev' in value or 'hidinput' in value:
            Config.remove_option('input', key)
except Exception:
    pass

from kivy.app import App
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

from app_ui import HotspotUI

BG_DARK = get_color_from_hex("#0D1117")


class MikrotikApp(App):
    title = "MikroTik Auto Login"
    icon = os.path.join(_ROOT, "data", "icon.png")

    def build(self):
        Window.clearcolor = BG_DARK
        return HotspotUI()

    def on_stop(self):
        root = self.root
        if root and hasattr(root, "on_stop"):
            root.on_stop()


if __name__ == "__main__":
    MikrotikApp().run()
