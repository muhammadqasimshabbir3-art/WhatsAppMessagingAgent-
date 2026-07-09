"""WhatsApp browser session via reusable Chrome (./start.sh browser / CDP debug port)."""

from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

from agent.config import get_whatsapp_config
from agent.custom_tools.browser_tools import (
    WHATSAPP_WEB_URL,
    _is_logged_in,
    ensure_whatsapp_browser_session,
    open_whatsapp_web,
    try_connect_browser,
)
from agent.custom_tools.whatsapp_tools import _get_stored_page, _store_browser_session

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _debug_port() -> int:
    raw = os.getenv("BROWSER_DEBUG_PORT", "9222").strip()
    try:
        return int(raw)
    except ValueError:
        return 9222


def is_debug_browser_running() -> bool:
    """True when Chrome is listening on the reusable debug port."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{_debug_port()}/json/version",
            timeout=1.5,
        ):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _wait_for_debug_browser(timeout_s: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if is_debug_browser_running():
            return True
        time.sleep(0.4)
    return False


def launch_reusable_browser() -> None:
    """Start Chrome with the persistent profile (same as ./start.sh browser)."""
    script = _PROJECT_ROOT / "scripts" / "open_whatsapp_browser.sh"
    if not script.is_file():
        raise FileNotFoundError(f"Browser launcher not found: {script}")

    result = subprocess.run(
        ["bash", str(script)],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or "Failed to start WhatsApp browser")

    if not _wait_for_debug_browser():
        raise RuntimeError(
            f"Chrome did not start on debug port {_debug_port()}. "
            "Run ./start.sh browser manually and scan the QR code."
        )


def _probe_cdp_status() -> dict[str, object] | None:
    """Connect over CDP briefly to read login state without keeping a session."""
    if not is_debug_browser_running():
        return None

    playwright = sync_playwright().start()
    try:
        _browser, _context, page = try_connect_browser(
            playwright,
            preferred_url=WHATSAPP_WEB_URL,
            open_new_if_missing=False,
        )
        if page is None:
            return None
        logged_in = _is_logged_in(page)
        return {
            "active": True,
            "logged_in": logged_in,
            "needs_qr": not logged_in,
            "url": page.url,
        }
    except Exception:
        return None
    finally:
        try:
            playwright.stop()
        except Exception:
            pass


def get_account_info() -> dict[str, object]:
    email = (
        os.getenv("GMAIL_SMTP_USER")
        or os.getenv("GMAIL_DEFAULT_RECIPIENT")
        or os.getenv("SMTP_TO_EMAIL")
        or ""
    ).strip()
    return {"email": email, "configured": bool(email)}


def get_browser_status() -> dict[str, object]:
    config = get_whatsapp_config()
    profile = config.get("browser_profile_path", "./data/chrome_profile")
    browser_running = is_debug_browser_running()

    page = _get_stored_page()
    if page is not None:
        try:
            logged_in = _is_logged_in(page)
            return {
                "active": True,
                "logged_in": logged_in,
                "needs_qr": not logged_in,
                "browser_running": browser_running,
                "profile_path": profile,
                "url": page.url,
                "mode": "reusable_chrome",
            }
        except Exception as exc:
            return {
                "active": False,
                "logged_in": False,
                "needs_qr": True,
                "browser_running": browser_running,
                "profile_path": profile,
                "url": WHATSAPP_WEB_URL,
                "error": str(exc),
                "mode": "reusable_chrome",
            }

    probe = _probe_cdp_status()
    if probe is not None:
        return {
            **probe,
            "browser_running": browser_running,
            "profile_path": profile,
            "mode": "reusable_chrome",
        }

    return {
        "active": False,
        "logged_in": False,
        "needs_qr": True,
        "browser_running": browser_running,
        "profile_path": profile,
        "url": WHATSAPP_WEB_URL,
        "mode": "reusable_chrome",
    }


def setup_browser() -> dict[str, object]:
    """Open reusable Chrome (if needed) and attach Playwright over CDP."""
    if not is_debug_browser_running():
        launch_reusable_browser()

    playwright, browser, context, page, logged_in = ensure_whatsapp_browser_session(
        headless=False
    )
    _store_browser_session(playwright, browser, context, page)

    if not logged_in and page is not None:
        open_whatsapp_web(page)

    status = get_browser_status()
    status["message"] = (
        "WhatsApp session active."
        if status.get("logged_in")
        else "Chrome opened — scan the QR code in the browser window."
    )
    return status
