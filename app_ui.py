"""
app_ui.py
Premium Kivy-based UI for MikroTik Hotspot Auto Login.
Features: animated status indicator, color-coded logs, gradient cards,
          pulsing connectivity dot, modern dark theme.
"""

import threading
import sys
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.stencilview import StencilView
from kivy.graphics import (
    Color, RoundedRectangle, Rectangle, Line, Ellipse,
    InstructionGroup
)
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.properties import ListProperty, StringProperty

import config_manager as cfg_mgr
import logger as log
from monitor import MonitorThread
import boot_manager

# ── Colour palette ───────────────────────────────────────────────────────────
BG_DARK       = get_color_from_hex("#0A0E14")
BG_CARD       = get_color_from_hex("#131920")
BG_CARD2      = get_color_from_hex("#0F1620")
BORDER        = get_color_from_hex("#1E2D3D")
ACCENT        = get_color_from_hex("#4FC3F7")    
ACCENT2       = get_color_from_hex("#0288D1")     
ACCENT_GREEN  = get_color_from_hex("#00E676")     
ACCENT_RED    = get_color_from_hex("#FF5252")   
ACCENT_ORANGE = get_color_from_hex("#FFB74D")    
ACCENT_YELLOW = get_color_from_hex("#FFF176")     
TEXT_PRIMARY  = get_color_from_hex("#E8EDF2")
TEXT_MUTED    = get_color_from_hex("#607D8B")
TEXT_LABEL    = get_color_from_hex("#90A4AE")
BTN_LOGIN     = get_color_from_hex("#00897B")     
BTN_STOP      = get_color_from_hex("#C62828")
BTN_SAVE      = get_color_from_hex("#1565C0")
INPUT_BG      = get_color_from_hex("#0D1B2A")

# Status → color mapping
STATUS_COLORS = {
    "connected":     ACCENT_GREEN,
    "logging in":    ACCENT,
    "reconnecting":  ACCENT,
    "checking":      ACCENT_YELLOW,
    "captive":       ACCENT_ORANGE,
    "session dropped": ACCENT_ORANGE,
    "offline":       ACCENT_RED,
    "failed":        ACCENT_RED,
    "stopped":       TEXT_MUTED,
    "idle":          TEXT_MUTED,
    "disabled":      TEXT_MUTED,
    "login off":     TEXT_MUTED,
    "monitoring":    ACCENT,
    "backing off":   ACCENT_ORANGE,
    "not on mikrotik": ACCENT_ORANGE,   # wrong WiFi network
}


def _status_color(status: str):
    s = status.lower()
    for key, color in STATUS_COLORS.items():
        if key in s:
            return color
    return TEXT_MUTED


Window.size = (860, 740)
Window.clearcolor = BG_DARK


# ── Canvas helpers ───────────────────────────────────────────────────────────

def _draw_card(widget, radius=dp(10), color=None):
    c = color or BG_CARD
    widget.canvas.before.clear()
    with widget.canvas.before:
        # Subtle border
        Color(*BORDER)
        RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius + 1])
        # Card fill
        Color(*c)
        RoundedRectangle(pos=(widget.x + 1, widget.y + 1),
                         size=(widget.width - 2, widget.height - 2),
                         radius=[radius])


def _bind_redraw(widget, radius=dp(10), color=None):
    def _redraw(*_):
        _draw_card(widget, radius=radius, color=color)
    widget.bind(pos=_redraw, size=_redraw)
    _redraw()
    return widget


def _make_circular_avatar(image_path: str, size_dp: int = 82):
    """
    Returns a Widget showing an image clipped to a circle.
    Uses StencilView so the image doesn't overflow the circle.
    A green accent ring is drawn around it.
    """
    s      = dp(size_dp)
    border = dp(3)
    inner  = s - border * 2

    outer = Widget(size_hint=(None, None), size=(s, s))

    stencil = StencilView(size_hint=(None, None), size=(inner, inner))
    img = Image(source=image_path, size_hint=(None, None), size=(inner, inner))
    stencil.add_widget(img)
    outer.add_widget(stencil)

    def _place(*_):
        stencil.pos = (outer.x + border, outer.y + border)
        stencil.size = (inner, inner)
        img.pos  = stencil.pos
        img.size = stencil.size
        outer.canvas.before.clear()
        with outer.canvas.before:
            Color(*get_color_from_hex("#0C1821"))
            Ellipse(pos=outer.pos, size=(s, s))
        outer.canvas.after.clear()
        with outer.canvas.after:
            Color(*ACCENT_GREEN)
            Line(ellipse=(outer.x, outer.y, s, s), width=border)

    outer.bind(pos=_place, size=_place)
    return outer


def _card(padding=None, spacing=dp(8), orientation="vertical", color=None):
    p = padding if padding is not None else [dp(14), dp(12)]
    layout = BoxLayout(
        orientation=orientation,
        padding=p,
        spacing=spacing,
        size_hint_y=None,
    )
    layout.bind(minimum_height=layout.setter("height"))
    _bind_redraw(layout, color=color)
    return layout


# ── Label factory ────────────────────────────────────────────────────────────

def _label(text, color=None, font_size=None, bold=False, halign="left",
           height=dp(26), size_hint_x=1):
    lbl = Label(
        text=text,
        color=color or TEXT_PRIMARY,
        font_size=font_size or dp(13.5),
        bold=bold,
        size_hint=(size_hint_x, None),
        height=height,
        halign=halign,
        valign="middle",
        markup=True,
    )
    lbl.bind(size=lambda w, v: setattr(w, "text_size", (w.width, None)))
    return lbl


# ── Stat pill widget (for header stats) ──────────────────────────────────────

class StatPill(BoxLayout):
    """Small pill showing an icon + value."""
    def __init__(self, icon, value="—", color=None, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(None, None),
            size=(dp(90), dp(52)),
            padding=[dp(6), dp(4)],
            **kw
        )
        self._color = color or ACCENT
        self._icon_lbl = Label(
            text=icon, font_size=dp(18),
            color=self._color,
            size_hint_y=None, height=dp(24),
            halign="center",
        )
        self._icon_lbl.bind(size=lambda w, v: setattr(w, "text_size", (w.width, None)))
        self._val_lbl = Label(
            text=value, font_size=dp(10),
            color=TEXT_LABEL,
            size_hint_y=None, height=dp(16),
            halign="center",
        )
        self._val_lbl.bind(size=lambda w, v: setattr(w, "text_size", (w.width, None)))
        self.add_widget(self._icon_lbl)
        self.add_widget(self._val_lbl)
        _bind_redraw(self, radius=dp(8), color=BG_CARD2)

    def set_value(self, val, color=None):
        self._val_lbl.text = val
        if color:
            self._icon_lbl.color = color


# ── Pulsing status dot ────────────────────────────────────────────────────────

class PulsingDot(Widget):
    """Animated pulsing circle for connection status."""
    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(14), dp(14)), **kw)
        self._color = list(TEXT_MUTED)
        self._anim = None
        self._draw()

    def _draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self._color)
            self._ellipse = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*self._color)
            Ellipse(pos=self.pos, size=self.size)

    def set_color(self, color, pulse=False):
        self._color = list(color)
        self._redraw()
        if self._anim:
            self._anim.stop(self)
            self._anim = None
        if pulse:
            anim = (Animation(opacity=0.3, duration=0.7) +
                    Animation(opacity=1.0, duration=0.7))
            anim.repeat = True
            anim.start(self)
            self._anim = anim
        else:
            self.opacity = 1.0


# ── Input factory ────────────────────────────────────────────────────────────

def _input(hint="", password=False, text="", input_filter=None):
    ti = TextInput(
        hint_text=hint,
        password=password,
        text=str(text),
        multiline=False,
        background_color=INPUT_BG,
        foreground_color=TEXT_PRIMARY,
        cursor_color=ACCENT,
        hint_text_color=TEXT_MUTED,
        font_size=dp(13.5),
        padding=[dp(12), dp(10)],
        size_hint_y=None,
        height=dp(42),
        input_filter=input_filter,
    )
    return ti


# ── Button factory ────────────────────────────────────────────────────────────

def _btn(text, bg_color, on_press=None, icon=""):
    full_text = f"{icon}  {text}" if icon else text
    btn = Button(
        text=full_text,
        background_color=bg_color,
        background_normal="",
        color=TEXT_PRIMARY,
        font_size=dp(13.5),
        bold=True,
        size_hint_y=None,
        height=dp(46),
    )
    if on_press:
        btn.bind(on_press=on_press)
    return btn


# ── Row builder ──────────────────────────────────────────────────────────────

def _row(label_text, widget, label_width=0.36):
    row = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(46),
        spacing=dp(10),
    )
    lbl = _label(label_text, color=TEXT_LABEL, font_size=dp(13), height=dp(46))
    lbl.size_hint_x = label_width
    row.add_widget(lbl)

    if isinstance(widget, list):
        val_box = BoxLayout(orientation="horizontal", spacing=dp(6))
        for w in widget:
            val_box.add_widget(w)
        row.add_widget(val_box)
    else:
        row.add_widget(widget)
    return row


def _switch_row(label_text, active=False):
    sw = Switch(active=active, size_hint=(None, None), size=(dp(80), dp(38)))
    row = _row(label_text, sw)
    return row, sw


def _section_header(text):
    """Coloured section separator with accent bar."""
    box = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
    # Accent bar widget
    bar = Widget(size_hint=(None, None), size=(dp(4), dp(22)))
    with bar.canvas:
        Color(*ACCENT)
        RoundedRectangle(pos=(bar.x, bar.y), size=(dp(4), dp(22)),
                         radius=[dp(2)])
    bar.bind(pos=lambda w, v: _redraw_bar(w), size=lambda w, v: _redraw_bar(w))
    lbl = _label(text, color=ACCENT, font_size=dp(14), bold=True, height=dp(30))
    box.add_widget(bar)
    box.add_widget(lbl)
    return box


def _redraw_bar(w):
    w.canvas.clear()
    with w.canvas:
        Color(*ACCENT)
        RoundedRectangle(pos=w.pos, size=(dp(4), dp(22)), radius=[dp(2)])


# ── Main UI ──────────────────────────────────────────────────────────────────

class HotspotUI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            padding=[dp(10), dp(8), dp(10), dp(10)],
            spacing=dp(8),
            **kw
        )
        self._config = cfg_mgr.load_config()
        self._monitor: MonitorThread | None = None
        self._log_lines = []
        self._build_ui()
        Clock.schedule_interval(self._poll_logs, 1.0)

    # ── Build ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        c = self._config

        # ── Header bar ───────────────────────────────────────────────────────
        header = BoxLayout(
            size_hint_y=None, height=dp(66),
            spacing=dp(10), padding=[dp(4), dp(4)]
        )
        _bind_redraw(header, radius=dp(12), color=BG_CARD2)

        # Icon
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "icon.png"
        )
        if os.path.exists(icon_path):
            icon_img = Image(
                source=icon_path,
                size_hint=(None, None),
                size=(dp(52), dp(52)),
                allow_stretch=True,
            )
            header.add_widget(icon_img)

        # Title group
        title_box = BoxLayout(orientation="vertical", spacing=0)
        title_lbl = _label(
            "[b]  MikroTik Auto Login[/b]",
            color=ACCENT, font_size=dp(17), bold=True, height=dp(28)
        )
        subtitle_lbl = _label(
            "  Hotspot Connection Manager",
            color=TEXT_MUTED, font_size=dp(11), height=dp(18)
        )
        title_box.add_widget(title_lbl)
        title_box.add_widget(subtitle_lbl)
        header.add_widget(title_box)

        # Spacer
        header.add_widget(Widget())

        # Status pill (dot + text) in header
        status_pill = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None), size=(dp(130), dp(34)),
            spacing=dp(6), padding=[dp(10), dp(6)]
        )
        _bind_redraw(status_pill, radius=dp(17), color=get_color_from_hex("#0A1520"))
        self._status_dot = PulsingDot()
        self._status_lbl = Label(
            text="Idle",
            color=TEXT_MUTED,
            font_size=dp(12),
            bold=True,
            size_hint=(1, 1),
            halign="left",
            valign="middle",
        )
        self._status_lbl.bind(
            size=lambda w, v: setattr(w, "text_size", (w.width, None))
        )
        status_pill.add_widget(self._status_dot)
        status_pill.add_widget(self._status_lbl)
        header.add_widget(status_pill)

        self.add_widget(header)

        # ── Scrollable body ───────────────────────────────────────────────────
        sv = ScrollView(do_scroll_x=False, bar_width=dp(3),
                        bar_color=ACCENT, bar_inactive_color=BORDER)
        body = BoxLayout(
            orientation="vertical", spacing=dp(8),
            size_hint_y=None, padding=[0, dp(2), 0, dp(16)]
        )
        body.bind(minimum_height=body.setter("height"))
        sv.add_widget(body)

        # ── Quick-stat bar ────────────────────────────────────────────────────
        stats_row = BoxLayout(
            size_hint_y=None, height=dp(60),
            spacing=dp(8),
        )
        self._pill_conn   = StatPill("NET", "Status", color=TEXT_MUTED)
        self._pill_retries = StatPill("RTY", "—", color=ACCENT_ORANGE)
        self._pill_last   = StatPill("TIME", "Never", color=ACCENT)
        self._pill_ip     = StatPill("IP", c.get("router_ip", "---"), color=ACCENT2)
        for p in [self._pill_conn, self._pill_retries, self._pill_last, self._pill_ip]:
            p.size_hint_x = 1
            p.size_hint_y = None
            p.height = dp(60)
            stats_row.add_widget(p)
        body.add_widget(stats_row)

        # ── Settings card ─────────────────────────────────────────────────────
        s_card = _card()
        s_card.add_widget(_section_header("Settings"))
        s_card.add_widget(_hdivider())

        self._ip_input       = _input("Router IP", text=c.get("router_ip", ""))
        self._user_input     = _input("Username",  text=c.get("username", ""))
        self._pass_input     = _input("Password", password=True,
                                      text=c.get("password", ""))
        self._interval_input = _input("Seconds",
                                      text=str(c.get("check_interval", 30)),
                                      input_filter="int")

        # Eye button for password
        self._eye_btn = Button(
            text="Show",
            background_color=INPUT_BG,
            background_normal="",
            color=TEXT_MUTED,
            font_size=dp(11),
            size_hint=(None, None),
            size=(dp(52), dp(42)),
        )
        self._eye_btn.bind(on_press=self._toggle_password)

        s_card.add_widget(_row("Router IP",    self._ip_input))
        s_card.add_widget(_row("Username",     self._user_input))
        s_card.add_widget(_row("Password",
                                [self._pass_input, self._eye_btn]))
        s_card.add_widget(_row("Check Interval (s)", self._interval_input))

        # Divider before toggles
        s_card.add_widget(_hdivider())
        s_card.add_widget(_label("  Automation", color=TEXT_MUTED,
                                 font_size=dp(11), height=dp(20)))

        row_al, self._sw_auto_login = _switch_row(
            "Auto-Login", c.get("auto_login", True))
        row_ar, self._sw_auto_reconnect = _switch_row(
            "Auto-Reconnect", c.get("auto_reconnect", True))
        s_card.add_widget(row_al)
        s_card.add_widget(row_ar)

        s_card.add_widget(_hdivider())
        s_card.add_widget(_label("  Advanced", color=TEXT_MUTED,
                                 font_size=dp(11), height=dp(20)))
        row_hl, self._sw_headless = _switch_row(
            "Headless Mode", c.get("headless_mode", True))
        row_sel, self._sw_selenium = _switch_row(
            "Selenium Fallback", c.get("use_selenium", False))
        row_boot, self._sw_boot = _switch_row(
            "Start on Boot", boot_manager.is_autostart_enabled())
        self._sw_boot.bind(active=self._on_boot_toggle)
        s_card.add_widget(row_hl)
        s_card.add_widget(row_sel)
        s_card.add_widget(row_boot)

        body.add_widget(s_card)

        # ── Status card ───────────────────────────────────────────────────────
        st_card = _card()
        st_card.add_widget(_section_header("Connection Status"))
        st_card.add_widget(_hdivider())

        self._lbl_conn = _label("Connection: Idle", color=TEXT_MUTED,
                                font_size=dp(14))
        self._lbl_last_login = _label("Last Login: Never", color=TEXT_MUTED)
        self._lbl_retries    = _label("Total Login Attempts: —", color=TEXT_MUTED)
        st_card.add_widget(self._lbl_conn)
        st_card.add_widget(self._lbl_last_login)
        st_card.add_widget(self._lbl_retries)
        body.add_widget(st_card)

        # ── Action buttons ────────────────────────────────────────────────────
        action_row = GridLayout(cols=2, spacing=dp(8),
                                size_hint_y=None, height=dp(54))
        action_row.add_widget(_btn("Login Now", BTN_LOGIN,
                                   self._on_login_now, icon=">"))
        action_row.add_widget(_btn("Stop",      BTN_STOP,
                                   self._on_stop,      icon="x"))
        body.add_widget(action_row)

        save_row = BoxLayout(size_hint_y=None, height=dp(54))
        save_row.add_widget(_btn("Save Settings", BTN_SAVE,
                                 self._on_save, icon="*"))
        body.add_widget(save_row)

        # ── Log viewer ────────────────────────────────────────────────────────
        log_card = BoxLayout(
            orientation="vertical", padding=[dp(12), dp(10)],
            spacing=dp(4), size_hint_y=None, height=dp(200)
        )
        _bind_redraw(log_card, color=BG_CARD2)
        log_card.add_widget(_section_header("Live Log"))
        log_card.add_widget(_hdivider())

        log_sv = ScrollView(do_scroll_x=False, size_hint=(1, 1),
                            bar_width=dp(2), bar_color=ACCENT)
        self._log_label = Label(
            text="",
            font_size=dp(11.5),
            size_hint_y=None,
            halign="left",
            valign="top",
            markup=True,
            color=TEXT_PRIMARY,
        )
        self._log_label.bind(texture_size=self._log_label.setter("size"))
        self._log_label.bind(
            size=lambda w, v: setattr(w, "text_size", (w.width, None))
        )
        log_sv.add_widget(self._log_label)
        log_card.add_widget(log_sv)
        self._log_sv = log_sv
        body.add_widget(log_card)

        # ── Developer Credits Card ─────────────────────────────────────────────
        body.add_widget(self._build_developer_card())

        self.add_widget(sv)

        # Start monitor automatically if auto_login is on
        if self._config.get("auto_login", True):
            Clock.schedule_once(lambda dt: self._start_monitor(), 0.5)

    # ── Developer card ────────────────────────────────────────────────────────

    def _build_developer_card(self):
        """Builds the 'Developed by' panel at the bottom of the UI."""
        dev_card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(110),
            spacing=dp(14),
            padding=[dp(14), dp(10)],
        )
        _bind_redraw(dev_card, radius=dp(12),
                     color=get_color_from_hex("#0C1821"))

        # Left accent bar
        accent = Widget(size_hint=(None, None), size=(dp(3), dp(90)))
        with accent.canvas:
            Color(*ACCENT_GREEN)
            RoundedRectangle(pos=accent.pos, size=accent.size, radius=[dp(2)])
        accent.bind(pos=lambda w, _: _bar_redraw(w, ACCENT_GREEN),
                    size=lambda w, _: _bar_redraw(w, ACCENT_GREEN))
        dev_card.add_widget(accent)

        # Developer photo (circular mask via corner radius = half height)
        dev_photo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "developer.png"
        )
        if os.path.exists(dev_photo_path):
            dev_card.add_widget(
                _make_circular_avatar(dev_photo_path, size_dp=82)
            )

        # Info column
        info_col = BoxLayout(orientation="vertical", spacing=dp(2))

        dev_title = _label(
            "Developed by",
            color=TEXT_MUTED, font_size=dp(10), height=dp(16)
        )
        dev_name = _label(
            "[b]Parmanand Kumar[/b]",
            color=ACCENT_GREEN, font_size=dp(15), bold=True, height=dp(22)
        )
        dev_dept = _label(
            "Dept. of Computer Science & Engineering",
            color=TEXT_LABEL, font_size=dp(11), height=dp(18)
        )
        dev_batch = _label(
            "Batch: 2022",
            color=ACCENT, font_size=dp(11), height=dp(16)
        )
        dev_proj = _label(
            "MikroTik Hotspot Auto Login",
            color=TEXT_MUTED, font_size=dp(10), height=dp(16)
        )
        info_col.add_widget(dev_title)
        info_col.add_widget(dev_name)
        info_col.add_widget(dev_dept)
        info_col.add_widget(dev_batch)
        info_col.add_widget(dev_proj)
        dev_card.add_widget(info_col)

        return dev_card

    # ── Events ───────────────────────────────────────────────────────────────

    def _toggle_password(self, btn):
        self._pass_input.password = not self._pass_input.password
        if self._pass_input.password:
            btn.text = "Show"
            btn.color = TEXT_MUTED
            btn.font_size = dp(11)
        else:
            btn.text = "Hide"
            btn.color = ACCENT
            btn.font_size = dp(11)

    def _on_save(self, *_):
        self._save_config()
        log.success("Settings saved successfully.")

    def _on_login_now(self, *_):
        self._save_config()
        if not self._monitor or not self._monitor.is_alive():
            self._start_monitor()
        else:
            self._monitor.force_login()

    def _on_stop(self, *_):
        if self._monitor and self._monitor.is_alive():
            self._monitor.stop()
            self._monitor = None
        self._set_status_ui("Stopped", TEXT_MUTED)
        log.info("Monitoring stopped by user.")

    def _on_boot_toggle(self, switch, value):
        """Immediately apply / remove the autostart entry when the switch fires."""
        ok, msg = boot_manager.sync_autostart(value)
        status_icon = "[OK]" if ok else "[ERROR]"
        log.info(f"{status_icon} Boot: {msg}")
        # Also persist the flag in config so it survives reloads
        self._config["start_on_boot"] = value
        cfg_mgr.save_config(self._config)


    # ── Monitor ───────────────────────────────────────────────────────────────

    def _start_monitor(self):
        self._monitor = MonitorThread(
            config=self._config,
            status_callback=self._on_status_update,
        )
        self._monitor.start()
        self._set_status_ui("Monitoring", ACCENT, pulse=True)

    def _on_status_update(self, status=None, last_login=None,
                          retry_count=None, session_total=None):
        def _update(dt):
            if status:
                col = _status_color(status)
                self._lbl_conn.text = f"[b]Connection:[/b]  {status}"
                self._lbl_conn.color = col
                self._set_status_ui(status, col,
                                    pulse=(status.lower() in
                                           ("logging in...", "reconnecting...",
                                            "checking...", "monitoring")))
                # Update stat pill
                self._pill_conn.set_value(status, color=col)

            if last_login:
                self._lbl_last_login.text = f"[b]Last Login:[/b]  {last_login}"
                # Show just the time part in pill
                self._pill_last.set_value(last_login.split(" ")[-1])

            if session_total is not None:
                if session_total == 0:
                    # No login attempts yet — show dash
                    self._lbl_retries.text = "[b]Total Login Attempts:[/b]  —"
                    self._lbl_retries.color = TEXT_MUTED
                    self._pill_retries.set_value("—", color=TEXT_MUTED)
                else:
                    rc = retry_count or 0
                    rc_color = (ACCENT_RED if rc > 3 else
                                ACCENT_ORANGE if rc > 0 else ACCENT_GREEN)
                    self._lbl_retries.text = (
                        f"[b]Total Login Attempts:[/b]  {session_total}"
                        + (f"   [b](current streak: {rc})[/b]" if rc > 0 else "")
                    )
                    self._lbl_retries.color = rc_color
                    self._pill_retries.set_value(
                        f"Total: {session_total}", color=rc_color
                    )

        Clock.schedule_once(_update, 0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status_ui(self, text: str, color, pulse: bool = False):
        self._status_lbl.text = text
        self._status_lbl.color = color
        self._status_dot.set_color(color, pulse=pulse)

    def _save_config(self):
        self._config["router_ip"]      = self._ip_input.text.strip()
        self._config["username"]       = self._user_input.text.strip()
        self._config["password"]       = self._pass_input.text
        self._config["check_interval"] = int(self._interval_input.text or 30)
        self._config["auto_login"]     = self._sw_auto_login.active
        self._config["auto_reconnect"] = self._sw_auto_reconnect.active
        self._config["headless_mode"]  = self._sw_headless.active
        self._config["use_selenium"]   = self._sw_selenium.active
        self._config["start_on_boot"]  = self._sw_boot.active
        # ── Apply Start on Boot ──────────────────────────────────────────
        ok, msg = boot_manager.sync_autostart(self._sw_boot.active)
        status_icon = "[OK]" if ok else "[ERROR]"
        log.info(f"{status_icon} Boot: {msg}")
        # Update IP stat pill live
        self._pill_ip.set_value(self._config["router_ip"])
        cfg_mgr.save_config(self._config)
        if self._monitor:
            self._monitor.update_config(self._config)

    def _colorize_log(self, line: str) -> str:
        """Add markup colors to log lines by level."""
        if "[OK]" in line:
            return f"[color=#00E676]{line}[/color]"
        elif "[ERROR]" in line:
            return f"[color=#FF5252]{line}[/color]"
        elif "[WARN]" in line:
            return f"[color=#FFB74D]{line}[/color]"
        elif "[INFO]" in line:
            return f"[color=#90A4AE]{line}[/color]"
        return f"[color=#607D8B]{line}[/color]"

    def _poll_logs(self, dt):
        new_lines = log.get_logs(50)
        if new_lines:
            colored = [self._colorize_log(l) for l in new_lines]
            self._log_lines.extend(colored)
            self._log_lines = self._log_lines[-300:]
            self._log_label.text = "\n".join(self._log_lines)
            self._log_sv.scroll_y = 0

    def on_stop(self):
        if self._monitor:
            self._monitor.stop()


# ── Divider helper ────────────────────────────────────────────────────────────

def _hdivider():
    """Thin horizontal line divider."""
    box = BoxLayout(size_hint_y=None, height=dp(10))
    with box.canvas:
        Color(*BORDER)
        Line(points=[dp(4), dp(5), 10000, dp(5)], width=dp(0.8))
    return box


def _bar_redraw(w, color):
    """Redraw a small colored accent bar widget."""
    w.canvas.clear()
    with w.canvas:
        Color(*color)
        RoundedRectangle(pos=w.pos, size=(dp(4), dp(22)), radius=[dp(2)])
