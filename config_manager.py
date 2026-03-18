"""
config_manager.py
Handles encrypted credential storage and JSON config persistence.
"""

import os
import json
import base64
from cryptography.fernet import Fernet

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "data")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
KEY_FILE = os.path.join(CONFIG_DIR, ".secret.key")

DEFAULT_CONFIG = {
    "router_ip": "192.168.88.1",
    "username": "",
    "password": "",
    "auto_login": True,
    "auto_reconnect": True,
    "check_interval": 30,
    "headless_mode": True,
    "start_on_boot": False,
    "use_selenium": False,
}


def _get_or_create_key() -> bytes:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_key())


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    token = _fernet().encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(token).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        token = base64.urlsafe_b64decode(ciphertext.encode())
        return _fernet().decrypt(token).decode()
    except Exception:
        return ""


def load_config() -> dict:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    # Decrypt sensitive fields
    cfg["username"] = decrypt(cfg.get("username", ""))
    cfg["password"] = decrypt(cfg.get("password", ""))
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    to_store = cfg.copy()
    # Encrypt sensitive fields before saving
    to_store["username"] = encrypt(cfg.get("username", ""))
    to_store["password"] = encrypt(cfg.get("password", ""))
    with open(CONFIG_FILE, "w") as f:
        json.dump(to_store, f, indent=2)
