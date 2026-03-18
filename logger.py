"""
logger.py
Thread-safe log queue for real-time UI log viewer.
"""

import queue
import threading
from datetime import datetime

_log_queue: queue.Queue = queue.Queue(maxsize=500)
_lock = threading.Lock()


def log(message: str, level: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    try:
        _log_queue.put_nowait(entry)
    except queue.Full:
        # Drop oldest, keep rolling
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            pass
        _log_queue.put_nowait(entry)


def info(msg: str) -> None:
    log(msg, "INFO")


def warn(msg: str) -> None:
    log(msg, "WARN")


def error(msg: str) -> None:
    log(msg, "ERROR")


def success(msg: str) -> None:
    log(msg, "OK")


def get_logs(max_lines: int = 100) -> list:
    """Drain up to max_lines entries from the queue."""
    entries = []
    for _ in range(max_lines):
        try:
            entries.append(_log_queue.get_nowait())
        except queue.Empty:
            break
    return entries
