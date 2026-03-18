"""
monitor.py
Background monitoring thread with exponential backoff and graceful shutdown.
Uses get_connection_state() for accurate captive-portal-aware status.

auto_login    — attempt login when captive portal detected on fresh connection
auto_reconnect — attempt login when session drops after being connected
"""

import threading
import time

import logger as log
from login_engine import MikrotikLoginEngine, LoginResult
from utils import get_connection_state, is_mikrotik_reachable

MIN_INTERVAL = 5        # minimum 5 seconds between checks
MAX_BACKOFF = 300       # 5 minutes max backoff


class MonitorThread(threading.Thread):
    def __init__(self, config: dict, status_callback=None):
        super().__init__(daemon=True, name="HotspotMonitor")
        self.config = config
        self.status_callback = status_callback or (lambda **kw: None)

        self._stop_event = threading.Event()
        self._login_lock = threading.Lock()

        self.retry_count = 0
        self.session_total_retries = 0   # cumulative — never resets
        self.last_login_time = "Never"
        self.current_status = "Idle"
        self._was_connected = False      # True once internet was confirmed

        self._engine = None
        self._build_engine()

    def _build_engine(self):
        c = self.config
        self._engine = MikrotikLoginEngine(
            router_ip=c.get("router_ip", "192.168.88.1"),
            username=c.get("username", ""),
            password=c.get("password", ""),
            headless=c.get("headless_mode", True),
            use_selenium=c.get("use_selenium", False),
        )

    def update_config(self, config: dict):
        self.config = config
        self._build_engine()

    def stop(self):
        log.info("Monitor: stop signal received.")
        self._stop_event.set()
        if self._engine:
            self._engine.close()

    def run(self):
        log.info("Monitor thread started.")
        self._set_status("Monitoring")
        backoff = 0

        while not self._stop_event.is_set():
            interval = max(
                MIN_INTERVAL,
                int(self.config.get("check_interval", 30))
            )

            # Honour backoff
            if backoff > 0:
                log.info(f"Backoff: waiting {backoff}s before retry...")
                self._set_status(f"Backing off ({backoff}s)")
                self._stop_event.wait(backoff)
                backoff = 0
                if self._stop_event.is_set():
                    break

            self._check_and_login()

            # Wait for next check interval
            self._stop_event.wait(interval)

            # If last attempt failed, apply exponential backoff
            if self.current_status == "Login failed":
                backoff = min(interval * (2 ** min(self.retry_count, 5)), MAX_BACKOFF)

        self._set_status("Stopped")
        log.info("Monitor thread stopped.")

    def _check_and_login(self):
        auto_login     = self.config.get("auto_login", True)
        auto_reconnect = self.config.get("auto_reconnect", True)

        # Skip entirely if both are off
        if not auto_login and not auto_reconnect:
            self._set_status("Auto-Login Disabled")
            return

        with self._login_lock:
            router_ip = self.config.get("router_ip", "192.168.88.1")

            # ── Step 1: Is the MikroTik router even on this network? ──────────
            self._set_status("Checking...")
            if not is_mikrotik_reachable(router_ip, timeout=3):
                msg = "Not on MikroTik WiFi"
                log.warn(f"Router {router_ip} not reachable — {msg}")
                self._was_connected = False   # reset — on a different network now
                self._set_status(msg)
                return   # Do nothing — wrong network

            state = get_connection_state()

            if state == "internet":
                self.retry_count = 0
                self._was_connected = True    # mark: we had internet
                self._set_status("Connected")
                self.status_callback(
                    status="Connected",
                    retry_count=0,
                    session_total=self.session_total_retries,
                )
                return

            if state == "offline":
                log.warn("No network detected. Check your WiFi connection.")
                self._set_status("Offline — No Network")
                self.status_callback(
                    status="Offline — No Network",
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )
                return

            # ── state == "captive_portal" ─────────────────────────────────────
            # Decide: is this a fresh login or a reconnect?
            is_reconnect = self._was_connected

            if is_reconnect:
                # Session dropped after we were connected
                if not auto_reconnect:
                    log.info("Session dropped but Auto-Reconnect is OFF — skipping.")
                    self._set_status("Session Dropped (Reconnect OFF)")
                    self.status_callback(
                        status="Session Dropped (Reconnect OFF)",
                        retry_count=self.retry_count,
                        session_total=self.session_total_retries,
                    )
                    return
                action_label = "Reconnecting..."
                log.info("Session dropped — attempting auto-reconnect.")
            else:
                # Fresh captive portal on first connection
                if not auto_login:
                    log.info("Captive portal detected but Auto-Login is OFF — skipping.")
                    self._set_status("Captive Portal Detected (Login OFF)")
                    self.status_callback(
                        status="Captive Portal Detected (Login OFF)",
                        retry_count=self.retry_count,
                        session_total=self.session_total_retries,
                    )
                    return
                action_label = "Logging in..."

            self._set_status(action_label)
            self.retry_count += 1
            self.session_total_retries += 1
            log.info(f"{'Reconnect' if is_reconnect else 'Login'} attempt "
                     f"#{self.retry_count} (session total: {self.session_total_retries})")
            self.status_callback(
                status=action_label,
                retry_count=self.retry_count,
                session_total=self.session_total_retries,
            )

            try:
                result = self._engine.attempt_login()
            except Exception as e:
                log.error(f"Login engine crash: {e}")
                if self.config.get("use_selenium"):
                    self._engine.restart_driver()
                result = LoginResult.FAILED

            if result == LoginResult.SUCCESS:
                self.last_login_time = time.strftime("%Y-%m-%d %H:%M:%S")
                self.retry_count = 0
                self._was_connected = True
                self._set_status("Connected")
                self.status_callback(
                    status="Connected",
                    last_login=self.last_login_time,
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )
            elif result == LoginResult.ALREADY_LOGGED_IN:
                self.retry_count = 0
                self._was_connected = True
                self._set_status("Connected")
                self.status_callback(
                    status="Connected",
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )
            elif result == LoginResult.NO_PORTAL:
                self._set_status("Offline — No Portal")
                self.status_callback(
                    status="Offline — No Portal",
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )
            else:
                self._set_status("Login failed")
                self.status_callback(
                    status="Login failed",
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )

    def _set_status(self, status: str):
        self.current_status = status
        self.status_callback(
            status=status,
            retry_count=self.retry_count,
            session_total=self.session_total_retries,
        )

    def force_login(self):
        """Trigger an immediate login attempt from UI — bypasses auto_login/reconnect flags."""
        threading.Thread(
            target=self._do_forced_login,
            daemon=True,
            name="ForceLogin"
        ).start()

    def _do_forced_login(self):
        """Direct login ignoring auto_login / auto_reconnect flags (manual trigger)."""
        with self._login_lock:
            router_ip = self.config.get("router_ip", "192.168.88.1")
            if not is_mikrotik_reachable(router_ip, timeout=3):
                log.warn("Router not reachable — check your WiFi.")
                self._set_status("Not on MikroTik WiFi")
                return

            self._set_status("Logging in...")
            self.retry_count += 1
            self.session_total_retries += 1
            self.status_callback(
                status="Logging in...",
                retry_count=self.retry_count,
                session_total=self.session_total_retries,
            )
            try:
                result = self._engine.attempt_login()
            except Exception as e:
                log.error(f"Login engine crash: {e}")
                result = LoginResult.FAILED

            if result in (LoginResult.SUCCESS, LoginResult.ALREADY_LOGGED_IN):
                self.last_login_time = time.strftime("%Y-%m-%d %H:%M:%S")
                self.retry_count = 0
                self._was_connected = True
                self._set_status("Connected")
                self.status_callback(
                    status="Connected",
                    last_login=self.last_login_time,
                    retry_count=0,
                    session_total=self.session_total_retries,
                )
            else:
                self._set_status("Login failed")
                self.status_callback(
                    status="Login failed",
                    retry_count=self.retry_count,
                    session_total=self.session_total_retries,
                )
