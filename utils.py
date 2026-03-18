"""
utils.py
Cross-platform utilities: internet check, captive portal detection.

FIX: The old socket fallback (connect to 8.8.8.8:53) was broken —
TCP SYN succeeds on MikroTik captive portals even before login.
Now uses proper HTTP response validation + DNS resolution.
"""

import socket
import requests
from logger import info, warn

SESSION_TIMEOUT = 6

# Endpoints that return HTTP 204 with empty body when internet is available
_CHECK_ENDPOINTS = [
    "http://connectivitycheck.gstatic.com/generate_204",   # HTTP (avoids SSL hijack)
    "http://clients3.google.com/generate_204",
    "http://detectportal.firefox.com/success.txt",         # returns "success\n"
]


def _check_dns() -> bool:
    """
    Verify DNS resolution works for a real internet host.
    On captive portals, DNS may be hijacked but often only resolves local IPs.
    We check that the resolved IP is NOT RFC1918 private.
    """
    try:
        results = socket.getaddrinfo("www.google.com", 80, socket.AF_INET)
        for r in results:
            ip = r[4][0]
            # Reject RFC1918 private IPs (used by captive portals for DNS hijack)
            if (ip.startswith("192.168.") or ip.startswith("10.") or
                    ip.startswith("172.") or ip == "127.0.0.1"):
                warn(f"DNS resolved to private IP {ip} — captive portal suspected")
                return False
        return True
    except OSError:
        return False


def is_internet_available() -> bool:
    """
    Check real internet connectivity.
    Strategy:
    1. Try multiple HTTP 204 endpoints (short timeout)
    2. A TRUE response requires BOTH correct status AND non-redirect body.
    Returns True only when at least one endpoint confirms real internet.
    """
    for url in _CHECK_ENDPOINTS:
        try:
            r = requests.get(
                url,
                timeout=SESSION_TIMEOUT,
                allow_redirects=False,   # CRITICAL: don't follow captive portal redirects
                headers={"Cache-Control": "no-cache"},
            )
            # Google generate_204 returns 204, Firefox returns 200 with "success"
            if r.status_code == 204:
                info("Internet check: OK (204)")
                return True
            if r.status_code == 200 and "success" in r.text.lower():
                info("Internet check: OK (200/success)")
                return True
            # Status 302/301 = captive portal redirect
            if r.status_code in (301, 302, 307, 308):
                warn(f"Internet check: redirect detected ({r.status_code}) — captive portal")
                return False
        except requests.RequestException:
            continue  # Try next endpoint

    warn("Internet check: FAILED (all endpoints)")
    return False


def get_connection_state() -> str:
    """
    Returns one of: 'internet', 'captive_portal', 'offline'
    More granular than is_internet_available() for better UI feedback.
    """
    # First check if we have any network at all via DNS
    has_dns = _check_dns()

    # Try the 204 checks
    for url in _CHECK_ENDPOINTS:
        try:
            r = requests.get(
                url,
                timeout=SESSION_TIMEOUT,
                allow_redirects=False,
                headers={"Cache-Control": "no-cache"},
            )
            if r.status_code == 204:
                return "internet"
            if r.status_code == 200 and "success" in r.text.lower():
                return "internet"
            if r.status_code in (200, 301, 302, 307, 308):
                return "captive_portal"
        except requests.ConnectionError:
            continue
        except requests.RequestException:
            continue

    # If DNS resolved public IPs but HTTP failed, might be firewall
    if has_dns:
        return "captive_portal"
    return "offline"


def is_captive_portal_present() -> tuple:
    """
    Returns (is_captive, redirect_url).
    Uses allow_redirects=False to catch the redirect destination.
    """
    for url in [_CHECK_ENDPOINTS[0], _CHECK_ENDPOINTS[1]]:
        try:
            r = requests.get(
                url,
                timeout=SESSION_TIMEOUT,
                allow_redirects=False,
            )
            if r.status_code == 204:
                return False, ""
            # Redirect = captive portal
            if r.status_code in (301, 302, 307, 308):
                redirect_to = r.headers.get("Location", "")
                info(f"Captive portal redirect to: {redirect_to}")
                return True, redirect_to
            # 200 with HTML body = portal login page
            if r.status_code == 200 and "<html" in r.text.lower():
                info(f"Captive portal HTML page at: {url}")
                return True, url
        except requests.RequestException as e:
            warn(f"Captive portal check error: {e}")
            continue

    return False, ""


def is_mikrotik_reachable(router_ip: str, timeout: int = 3) -> bool:
    """
    Check if the MikroTik router is reachable on the current network.
    Tries to open a TCP socket to the router's port 80.
    Returns True only if the router responds — i.e., we are on the MikroTik WiFi.
    Returns False if on a completely different network or WiFi not the hotspot.
    """
    import socket as _socket
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((router_ip, 80))
        s.close()
        info(f"MikroTik router reachable at {router_ip}")
        return True
    except OSError:
        warn(f"MikroTik router NOT reachable at {router_ip} — not on hotspot network")
        return False


def build_hotspot_url(router_ip: str) -> str:
    return f"http://{router_ip}/login"


def build_hotspot_status_url(router_ip: str) -> str:
    return f"http://{router_ip}/status"
