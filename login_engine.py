"""
login_engine.py
MikroTik Hotspot login engine.
Primary: requests.Session() direct POST (no browser needed)
Fallback: Selenium headless (desktop only, disabled on Android)

Tuned for Enhance Webtech Hotspot (and generic MikroTik portals).
"""

import sys
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import logger as log
from utils import (
    is_internet_available,
    is_captive_portal_present,
    build_hotspot_url,
    build_hotspot_status_url,
    SESSION_TIMEOUT,
)



# Phrases in POST response body that confirm successful login
_SUCCESS_PHRASES = [
    "you are logged in",
    "logged in successfully",
    "login successful",
    "welcome",
    "you have been authenticated",
    "authentication successful",
]

# Phrases in POST response body that confirm login failure
_FAIL_PHRASES = [
    "invalid",
    "incorrect",
    "wrong password",
    "login failed",
    "error",
    "bad password",
]


class LoginResult:
    SUCCESS = "success"
    ALREADY_LOGGED_IN = "already_logged_in"
    FAILED = "failed"
    PORTAL_NOT_FOUND = "portal_not_found"
    NO_PORTAL = "no_portal"


class MikrotikLoginEngine:
    def __init__(self, router_ip: str, username: str, password: str,
                 headless: bool = True, use_selenium: bool = False):
        self.router_ip = router_ip
        self.username = username
        self.password = password
        self.headless = headless
        self.use_selenium = use_selenium
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self._driver = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def attempt_login(self) -> str:
        """Try login. Returns LoginResult constant."""
        if is_internet_available():
            log.success("Already connected to internet.")
            return LoginResult.ALREADY_LOGGED_IN

        is_captive, redirect_url = is_captive_portal_present()
        if not is_captive:
            log.warn("No captive portal detected and no internet. Check network.")
            return LoginResult.NO_PORTAL

        log.info(f"Captive portal at: {redirect_url or self.router_ip}")

        # Try requests-based login first
        result = self._requests_login(redirect_url)
        if result == LoginResult.SUCCESS:
            return result

        # Selenium fallback (desktop only)
        if self.use_selenium:
            log.info("Falling back to Selenium login...")
            result = self._selenium_login(redirect_url)

        return result

    def verify_login(self) -> bool:
        """Verify by checking real internet or Mikrotik status page."""
        # 1. Real internet check (most reliable)
        if is_internet_available():
            return True

        # 2. Check hotspot status page for logout link (portal-specific)
        try:
            status_url = build_hotspot_status_url(self.router_ip)
            r = self.session.get(status_url, timeout=SESSION_TIMEOUT,
                                 allow_redirects=True)
            text_lower = r.text.lower()
            if ("logout" in text_lower or
                    "logged in" in text_lower or
                    "connected" in text_lower or
                    "you are logged in" in text_lower):
                return True
        except Exception:
            pass

        return False

    def logout(self) -> None:
        try:
            logout_url = f"http://{self.router_ip}/logout"
            self.session.get(logout_url, timeout=SESSION_TIMEOUT)
            log.info("Logged out from hotspot.")
        except Exception as e:
            log.warn(f"Logout error: {e}")

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    # ------------------------------------------------------------------
    # requests-based login
    # ------------------------------------------------------------------

    def _requests_login(self, redirect_url: str) -> str:
        login_url = redirect_url or build_hotspot_url(self.router_ip)
        log.info(f"Attempting requests login at: {login_url}")

        try:
            # Step 1: GET the login page to collect hidden fields + form action
            get_resp = self.session.get(
                login_url,
                timeout=SESSION_TIMEOUT,
                allow_redirects=True,
            )

            # If the GET response already shows "logged in" we're done
            if self._body_has_success(get_resp.text):
                log.success("Already authenticated (portal says logged in).")
                return LoginResult.ALREADY_LOGGED_IN

            soup = BeautifulSoup(get_resp.text, "html.parser")
            form = soup.find("form")
            if not form:
                log.warn("No form found on login page.")
                return LoginResult.PORTAL_NOT_FOUND

            # Collect all hidden inputs into payload
            payload = {}
            for inp in form.find_all("input"):
                name = inp.get("name", "")
                val  = inp.get("value", "")
                if name:
                    payload[name] = val

            # Map username / password fields
            username_field = self._find_field(
                soup, ["username", "name", "user", "login", "uid"])
            password_field = self._find_field(
                soup, ["password", "passwd", "pass", "pwd"])

            payload[username_field or "username"] = self.username
            payload[password_field or "password"] = self.password

            # Resolve POST URL from form action
            action = form.get("action", "")
            post_url = self._resolve_action(action, get_resp.url,
                                            login_url)

            log.info(f"Posting credentials to: {post_url}")
            post_resp = self.session.post(
                post_url,
                data=payload,
                timeout=SESSION_TIMEOUT,
                allow_redirects=True,
            )

            # Check the POST response body for success/failure signals
            if self._body_has_success(post_resp.text):
                log.success("Portal returned success page!")
                # Give network a moment to fully open
                time.sleep(2)
                if self.verify_login():
                    log.success("Login confirmed — internet available.")
                    return LoginResult.SUCCESS
                # Sometimes the portal session is established but DNS/routing
                # takes a moment — try once more after a short wait
                time.sleep(3)
                if self.verify_login():
                    log.success("Login confirmed (delayed) — internet available.")
                    return LoginResult.SUCCESS
                log.warn("Portal success page shown but internet not yet reachable.")
                return LoginResult.SUCCESS  # Trust the portal success page

            if self._body_has_failure(post_resp.text):
                log.error("Login failed: incorrect credentials or portal error.")
                return LoginResult.FAILED

            # Ambiguous response — do a generic internet verify
            time.sleep(2)
            if self.verify_login():
                log.success("Login successful via requests!")
                return LoginResult.SUCCESS

            log.warn("Login POST completed but connection not verified.")
            return LoginResult.FAILED

        except requests.RequestException as e:
            log.error(f"Requests login error: {e}")
            return LoginResult.FAILED

    def _resolve_action(self, action: str, current_url: str,
                        fallback_url: str) -> str:
        """Resolve form action to an absolute URL."""
        if not action:
            return fallback_url
        if action.startswith("http://") or action.startswith("https://"):
            return action
        # Use urljoin to correctly handle relative paths like "login" or "/login"
        resolved = urljoin(current_url, action)
        return resolved

    def _body_has_success(self, body: str) -> bool:
        lower = body.lower()
        return any(phrase in lower for phrase in _SUCCESS_PHRASES)

    def _body_has_failure(self, body: str) -> bool:
        lower = body.lower()
        return any(phrase in lower for phrase in _FAIL_PHRASES)

    def _find_field(self, soup, candidates: list) -> str:
        """Find first matching visible input name from candidate list."""
        for inp in soup.find_all(
            "input",
            attrs={"type": lambda t: t not in ["submit", "button", "hidden",
                                               "checkbox", "radio"]}
        ):
            name = (inp.get("name") or "").lower()
            for c in candidates:
                if c in name:
                    return inp.get("name")
        return ""

    # ------------------------------------------------------------------
    # Selenium login (desktop only)
    # ------------------------------------------------------------------

    def _selenium_login(self, redirect_url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import WebDriverException, TimeoutException
        except ImportError:
            log.error("Selenium not installed.")
            return LoginResult.FAILED

        login_url = redirect_url or build_hotspot_url(self.router_ip)
        log.info(f"Selenium login at: {login_url}")

        try:
            if not self._driver:
                opts = ChromeOptions()
                if self.headless:
                    opts.add_argument("--headless=new")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-dev-shm-usage")
                opts.add_argument("--disable-gpu")
                opts.add_argument("--disable-extensions")
                self._driver = webdriver.Chrome(options=opts)

            self._driver.get(login_url)
            wait = WebDriverWait(self._driver, 15)

            for user_selector in [
                (By.NAME, "username"), (By.ID, "username"),
                (By.NAME, "name"),     (By.NAME, "user"),
                (By.NAME, "uid"),
            ]:
                try:
                    u = wait.until(EC.presence_of_element_located(user_selector))
                    u.clear()
                    u.send_keys(self.username)
                    break
                except TimeoutException:
                    continue

            for pass_selector in [
                (By.NAME, "password"), (By.ID, "password"),
                (By.NAME, "passwd"),   (By.NAME, "pass"),
                (By.NAME, "pwd"),
            ]:
                try:
                    p = self._driver.find_element(*pass_selector)
                    p.clear()
                    p.send_keys(self.password)
                    break
                except Exception:
                    continue

            for btn_selector in [
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(text(),'Login')]"),
                (By.XPATH, "//button[contains(text(),'Log in')]"),
                (By.XPATH, "//input[@value='Log in']"),
            ]:
                try:
                    btn = self._driver.find_element(*btn_selector)
                    btn.click()
                    break
                except Exception:
                    continue

            time.sleep(3)
            # Check page source for success
            if self._body_has_success(self._driver.page_source):
                log.success("Selenium: Portal success page detected.")
                return LoginResult.SUCCESS

            if self.verify_login():
                log.success("Login successful via Selenium!")
                return LoginResult.SUCCESS

            log.error("Selenium login: connection not verified.")
            return LoginResult.FAILED

        except Exception as e:
            log.error(f"Selenium error: {e}")
            self.close()
            return LoginResult.FAILED

    def restart_driver(self) -> None:
        log.warn("Restarting browser driver...")
        self.close()
