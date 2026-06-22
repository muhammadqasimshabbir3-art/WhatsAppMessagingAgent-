"""Playwright browser automation for WhatsApp Web login and navigation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    sync_playwright,
)

from agent.config import get_whatsapp_config

_DEFAULT_PLAYWRIGHT_BROWSERS = Path.home() / ".cache" / "ms-playwright"
if not os.getenv("PLAYWRIGHT_BROWSERS_PATH") and _DEFAULT_PLAYWRIGHT_BROWSERS.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_DEFAULT_PLAYWRIGHT_BROWSERS)

WHATSAPP_WEB_URL = "https://web.whatsapp.com/"
GMAIL_INBOX_URL = "https://mail.google.com/mail/u/0/#inbox"
GOOGLE_SIGNIN_URL = (
    "https://accounts.google.com/v3/signin/identifier"
    "?continue=https://mail.google.com/mail/u/0/"
    "&flowName=GlifWebSignIn"
    "&flowEntry=ServiceLogin"
)

EMAIL_SELECTORS = (
    "#identifierId",
    'input[name="identifier"]',
    'input[type="email"]',
    'input[autocomplete="username"]',
)

PASSWORD_SELECTORS = (
    'input[name="Passwd"]',
    'input[type="password"]',
    'input[autocomplete="current-password"]',
)

NEXT_BUTTON_SELECTORS = (
    "#identifierNext button",
    "#identifierNext",
    'button:has-text("Next")',
)

PASSWORD_NEXT_SELECTORS = (
    "#passwordNext button",
    "#passwordNext",
    'button:has-text("Next")',
)

LOGGED_IN_SELECTORS = (
    'div[data-testid="chat-list"]',
    "#pane-side",
    'div[aria-label="Chat list"]',
)

QR_CODE_SELECTORS = (
    'canvas[aria-label="Scan me!"]',
    'div[data-testid="qrcode"]',
    'div[data-ref]',
)

SEARCH_INPUT_SELECTORS = (
    # Primary: actual WhatsApp Web search input element
    'input[aria-label="Search or start a new chat"]',
    'input[data-tab="3"]',
    '#side input[type="text"]',
    # Legacy fallbacks (older WhatsApp Web builds)
    '#side div[contenteditable="true"][data-tab="3"]',
    'div[data-testid="chat-list-search"]',
    'div[title="Search input textbox"]',
)

CHAT_ROW_SELECTORS = (
    'div[data-testid="cell-frame-container"]',
    'div[role="listitem"]',
)

GMAIL_LOGGED_IN_SELECTORS = (
    'div[role="main"]',
    'div[aria-label="Main menu"]',
    'div[gh="tl"]',
    '[data-tooltip="Compose"]',
)


def _gmail_credentials() -> tuple[str, str]:
    config = get_whatsapp_config()
    return config.get("email", ""), config.get("password", "")


def _is_google_sign_in_page(page: Page) -> bool:
    """True when Google account email/password screens are visible."""
    url = page.url
    if "accounts.google.com" in url:
        return True
    for selector in (*EMAIL_SELECTORS, *PASSWORD_SELECTORS):
        try:
            if page.locator(selector).first.is_visible(timeout=500):
                return True
        except Exception:
            continue
    return False


def _is_gmail_logged_in(page: Page) -> bool:
    """True only when Gmail inbox UI is visible (not on a sign-in screen)."""
    if _is_google_sign_in_page(page):
        return False
    if "mail.google.com/mail" not in page.url:
        return False
    for selector in GMAIL_LOGGED_IN_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=3000):
                return True
        except Exception:
            continue
    return False


def _click_if_visible(
    page: Page, selectors: Iterable[str], timeout_ms: int = 2000
) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=timeout_ms):
                locator.click()
                return True
        except Exception:
            continue
    return False


def _dismiss_optional_screens(page: Page) -> None:
    """Skip optional Google setup prompts when they appear."""
    optional_selectors = [
        "button:has-text('Not now')",
        "button:has-text('Skip')",
        "button:has-text('No thanks')",
        "button:has-text('Dismiss')",
        "button:has-text('I agree')",
        "#confirm",
    ]
    for selector in optional_selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1500):
                locator.click()
                page.wait_for_timeout(500)
        except Exception:
            continue


def _open_google_sign_in(page: Page, timeout_ms: int) -> None:
    """Open the Google sign-in page (start from accounts, not WhatsApp)."""
    page.goto(GOOGLE_SIGNIN_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(2000)
    _dismiss_optional_screens(page)


def _click_account_if_shown(page: Page, email: str) -> bool:
    """Pick the saved Google account when the chooser screen appears."""
    if not email:
        return False
    selectors = (
        f'div[data-email="{email}"]',
        f'[data-identifier="{email}"]',
        f'div[aria-label*="{email}"]',
    )
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1500):
                locator.click()
                page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    try:
        locator = page.get_by_text(email, exact=False).first
        if locator.is_visible(timeout=1000):
            locator.click()
            page.wait_for_timeout(2000)
            return True
    except Exception:
        pass
    return False


def _type_into_input(locator: Locator, value: str) -> None:
    """Type credentials the way Google expects (sequential keystrokes)."""
    locator.click()
    locator.fill("")
    locator.press_sequentially(value, delay=40)


def _fill_google_identifier(page: Page, email: str, timeout_ms: int) -> None:
    _prepare_identifier_step(page)
    email_input = _first_visible_locator(page, EMAIL_SELECTORS, timeout_ms)
    _type_into_input(email_input, email)
    if not _click_if_visible(page, NEXT_BUTTON_SELECTORS, timeout_ms=5000):
        page.keyboard.press("Enter")
    page.wait_for_timeout(2000)


def _fill_google_password(page: Page, password: str, timeout_ms: int) -> None:
    password_input = _first_visible_locator(page, PASSWORD_SELECTORS, timeout_ms)
    _type_into_input(password_input, password)
    if not _click_if_visible(page, PASSWORD_NEXT_SELECTORS, timeout_ms=5000):
        page.keyboard.press("Enter")
    page.wait_for_timeout(3000)
    _dismiss_optional_screens(page)


def _wait_for_gmail_inbox(page: Page, timeout_ms: int) -> bool:
    """Wait until Gmail inbox is loaded after submitting credentials."""
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        if _is_gmail_logged_in(page):
            return True
        if WHATSAPP_WEB_URL in page.url:
            return False
        if _is_google_sign_in_page(page):
            _dismiss_optional_screens(page)
            page.wait_for_timeout(1000)
            continue
        try:
            page.goto(GMAIL_INBOX_URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            _dismiss_optional_screens(page)
        except Exception:
            page.wait_for_timeout(1000)
    return _is_gmail_logged_in(page)


def _prepare_identifier_step(page: Page) -> None:
    """Handle account chooser screens before entering email."""
    for selector in EMAIL_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                return
        except Exception:
            continue

    _click_if_visible(
        page,
        (
            "text=Use another account",
            "div:has-text('Use another account')",
            "text=Add account",
        ),
        timeout_ms=2000,
    )


def login_gmail(page: Page, email: str = "", password: str = "") -> bool:
    """Log in to Gmail via Google account credentials from .env."""
    config = get_whatsapp_config()
    email = email or config.get("email", "")
    password = password or config.get("password", "")
    timeout_ms = _login_timeout_ms()

    if not email or not password:
        raise ValueError("EMAIL and PASSWORD must be set in .env for Gmail login.")

    try:
        if WHATSAPP_WEB_URL in page.url:
            return _is_logged_in(page) or _is_gmail_logged_in(page)

        page.goto(GMAIL_INBOX_URL, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2000)
        _dismiss_optional_screens(page)

        if _is_gmail_logged_in(page):
            return True

        if _click_account_if_shown(page, email):
            if _is_gmail_logged_in(page):
                return True
            if not _is_google_sign_in_page(page):
                return _wait_for_gmail_inbox(page, timeout_ms)

        _open_google_sign_in(page, timeout_ms)
        if _is_gmail_logged_in(page):
            return True

        if _click_account_if_shown(page, email):
            if _is_gmail_logged_in(page):
                return True
        else:
            _fill_google_identifier(page, email, timeout_ms)

        if _is_google_sign_in_page(page):
            _fill_google_password(page, password, timeout_ms)

        return _wait_for_gmail_inbox(page, timeout_ms)
    except Exception as exc:
        headless_hint = ""
        if config["headless"]:
            headless_hint = (
                " Try setting BROWSER_HEADLESS=false in .env so you can complete "
                "any Google security prompts manually."
            )
        raise TimeoutError(
            f"Gmail login failed while waiting for Google sign-in fields: {exc}.{headless_hint}"
        ) from exc


def ensure_gmail_login(page: Page, timeout_ms: int | None = None) -> bool:
    """Ensure Gmail is open and signed in (saved session or EMAIL/PASSWORD)."""
    if WHATSAPP_WEB_URL in page.url:
        return True

    timeout_ms = timeout_ms or _login_timeout_ms()
    page.goto(GMAIL_INBOX_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(2000)

    if _is_gmail_logged_in(page):
        return True

    email, password = _gmail_credentials()
    if email and password:
        return login_gmail(page, email, password)

    raise ValueError(
        "Gmail is not signed in. Set EMAIL and PASSWORD in .env, or sign in once "
        "with BROWSER_HEADLESS=false to save the session."
    )


def _login_timeout_ms() -> int:
    raw = os.getenv("BROWSER_LOGIN_TIMEOUT_MS", "120000").strip()
    try:
        return max(30000, int(raw))
    except ValueError:
        return 120000


def _browser_debug_port() -> int:
    raw = os.getenv("BROWSER_DEBUG_PORT", "9222").strip()
    try:
        return int(raw)
    except ValueError:
        return 9222


def _chromium_launch_args() -> list[str]:
    return [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--remote-debugging-port={_browser_debug_port()}",
    ]


def try_connect_browser(
    playwright: Playwright,
) -> tuple[Browser | None, BrowserContext | None, Page | None]:
    """Reconnect to an already-running Chromium window (same browser across graph steps)."""
    port = _browser_debug_port()
    try:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        return browser, context, page
    except Exception:
        return None, None, None


def _new_browser_context(
    browser: Browser,
    session_path: str | None = None,
) -> BrowserContext:
    """Create a browser context, optionally loading a saved session."""
    kwargs: dict = {
        "viewport": {"width": 1280, "height": 900},
        "locale": "en-US",
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
    }
    if session_path and Path(session_path).exists():
        kwargs["storage_state"] = session_path
    return browser.new_context(**kwargs)


def launch_browser(
    headless: bool | None = None,
) -> tuple[Playwright, Browser, BrowserContext, Page]:
    """Launch Chromium with Playwright and return playwright, browser, context, page."""
    config = get_whatsapp_config()
    headless = config["headless"] if headless is None else headless

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=headless,
        args=_chromium_launch_args(),
    )
    context = _new_browser_context(browser)
    page = context.new_page()
    return playwright, browser, context, page


def save_session(context: BrowserContext, path: str | None = None) -> str:
    """Persist browser storage state for session reuse."""
    config = get_whatsapp_config()
    session_path = path or config["session_path"]
    Path(session_path).parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=session_path)
    return session_path


def load_session(
    browser: Browser,
    path: str | None = None,
) -> BrowserContext:
    """Load a previously saved browser session."""
    config = get_whatsapp_config()
    session_path = path or config["session_path"]
    return _new_browser_context(browser, session_path)


def _first_visible_locator(
    page: Page,
    selectors: Iterable[str],
    timeout_ms: int,
) -> Locator:
    """Return the first locator that becomes visible within the timeout."""
    selector_list = tuple(selectors)
    per_selector_timeout = max(3000, timeout_ms // max(len(selector_list), 1))
    last_error: Exception | None = None

    for selector in selector_list:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=per_selector_timeout)
            return locator
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise TimeoutError("No matching element became visible.")


def _is_logged_in(page: Page) -> bool:
    for selector in LOGGED_IN_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1500):
                return True
        except Exception:
            continue
    return False


def _is_qr_visible(page: Page) -> bool:
    for selector in QR_CODE_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                return True
        except Exception:
            continue
    return False


def open_whatsapp_web(page: Page, timeout_ms: int | None = None) -> None:
    """Open WhatsApp Web in the browser (navigate to the URL like a normal tab)."""
    timeout_ms = timeout_ms or _login_timeout_ms()
    page.goto(WHATSAPP_WEB_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(2500)


def wait_for_whatsapp_login(
    page: Page,
    timeout_ms: int | None = None,
    *,
    block_for_qr: bool = True,
) -> bool:
    """Wait until WhatsApp Web shows the chat list (logged in)."""
    timeout_ms = timeout_ms or _login_timeout_ms()
    if WHATSAPP_WEB_URL not in page.url:
        open_whatsapp_web(page, timeout_ms)

    if _is_logged_in(page):
        return True

    if not block_for_qr:
        return _is_logged_in(page)

    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        if _is_logged_in(page):
            return True
        page.wait_for_timeout(2000)

    config = get_whatsapp_config()
    hint = ""
    if config["headless"]:
        hint = (
            " Set BROWSER_HEADLESS=false in .env, scan the QR code in the "
            "browser window, then re-run."
        )
    raise TimeoutError(
        f"WhatsApp Web login timed out waiting for QR scan.{hint}"
    )


def close_browser_session(
    playwright: Playwright | None,
    browser: Browser | None,
    context: BrowserContext | None,
) -> None:
    """Clean up Playwright resources (supports persistent context where browser is None)."""
    if context is not None:
        try:
            context.close()
        except Exception:
            pass
    elif browser is not None:
        try:
            browser.close()
        except Exception:
            pass
    if playwright is not None:
        try:
            playwright.stop()
        except Exception:
            pass


def _persistent_context_kwargs(headless: bool) -> dict:
    """Build kwargs for launch_persistent_context (saved Chrome profile)."""
    config = get_whatsapp_config()
    kwargs: dict = {
        "headless": headless,
        "args": _chromium_launch_args(),
        "viewport": {"width": 1280, "height": 900},
        "locale": "en-US",
        "ignore_default_args": ["--enable-automation"],
    }
    channel = config.get("browser_channel", "").strip()
    if channel:
        kwargs["channel"] = channel
    return kwargs


def launch_persistent_browser(
    headless: bool | None = None,
) -> tuple[Playwright, Browser | None, BrowserContext, Page]:
    """Launch or reconnect Chromium using a persistent on-disk profile."""
    config = get_whatsapp_config()
    headless = config["headless"] if headless is None else headless
    profile_path = Path(config["browser_profile_path"])
    profile_path.mkdir(parents=True, exist_ok=True)

    playwright = sync_playwright().start()
    browser, context, page = try_connect_browser(playwright)
    if page is not None:
        return playwright, browser, context, page

    context = playwright.chromium.launch_persistent_context(
        str(profile_path),
        **_persistent_context_kwargs(headless),
    )
    page = context.pages[0] if context.pages else context.new_page()
    return playwright, None, context, page


def ensure_whatsapp_browser_session(
    headless: bool | None = None,
) -> tuple[Playwright, Browser | None, BrowserContext, Page, bool]:
    """Open WhatsApp Web in a persistent Chrome profile (scan QR once, then reuse)."""
    playwright, browser, context, page = launch_persistent_browser(headless)

    if _is_logged_in(page):
        return playwright, browser, context, page, True

    open_whatsapp_web(page)
    try:
        logged_in = wait_for_whatsapp_login(page, block_for_qr=True)
    except TimeoutError:
        logged_in = _is_logged_in(page)

    return playwright, browser, context, page, logged_in


def launch_whatsapp_browser_from_session(
    headless: bool | None = None,
) -> tuple[Playwright, Browser | None, BrowserContext, Page]:
    """Reconnect or launch persistent browser for WhatsApp Web."""
    return launch_persistent_browser(headless)


def open_chat_search(page: Page, timeout_ms: int | None = None) -> Locator:
    """Focus the WhatsApp chat search box."""
    timeout_ms = timeout_ms or _login_timeout_ms()
    search = _first_visible_locator(page, SEARCH_INPUT_SELECTORS, timeout_ms)
    search.click()
    return search


def navigate_to_contact(
    page: Page,
    contact_name: str = "",
    phone_number: str = "",
) -> str:
    """Open a WhatsApp chat by contact name or phone number. Returns resolved label."""
    query = (contact_name or phone_number or "").strip()
    if not query:
        raise ValueError("Provide a contact name or phone number to open a chat.")

    timeout_ms = _login_timeout_ms()
    search = open_chat_search(page, timeout_ms)

    # Clear and type query – works for both <input> and contenteditable div
    try:
        search.fill("")
    except Exception:
        search.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
    page.keyboard.type(query, delay=50)
    page.wait_for_timeout(1800)

    # 1) Try to click a search result whose title text matches the contact name
    if contact_name:
        try:
            # WhatsApp renders matched text inside span[data-testid="text-highlight"]
            # wrapped in a cell-frame-title span. Find the cell whose title contains our query.
            matched = page.locator(
                'div[data-testid="cell-frame-container"]',
            ).filter(has_text=contact_name).first
            if matched.is_visible(timeout=3000):
                matched.click()
                page.wait_for_timeout(2000)
                page.wait_for_selector(
                    'div[data-testid="conversation-panel-body"], #main',
                    timeout=10000,
                )
                return contact_name
        except Exception:
            pass

    # 2) Fallback: click the first result in the search list
    for selector in CHAT_ROW_SELECTORS:
        rows = page.locator(selector)
        try:
            if rows.count() > 0:
                rows.first.click()
                page.wait_for_timeout(2000)
                return contact_name or phone_number or query
        except Exception:
            continue

    # 3) Last resort: press Enter to open whatever WhatsApp highlights
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)
    return contact_name or phone_number or query


def ensure_gmail_browser_session(
    headless: bool | None = None,
    *,
    open_whatsapp: bool = False,
) -> tuple[Playwright, Browser, BrowserContext, Page, bool]:
    """Launch browser and sign into Gmail (EMAIL/PASSWORD from .env)."""
    config = get_whatsapp_config()
    headless = config["headless"] if headless is None else headless
    session_path = config["session_path"]

    playwright = sync_playwright().start()
    browser, context, page = try_connect_browser(playwright)
    if page is not None:
        if WHATSAPP_WEB_URL in page.url or _is_logged_in(page):
            return playwright, browser, context, page, True
        if _is_gmail_logged_in(page):
            gmail_ok = True
        else:
            email, password = _gmail_credentials()
            if email and password:
                gmail_ok = login_gmail(page, email, password)
            else:
                gmail_ok = ensure_gmail_login(page)
        if gmail_ok:
            save_session(context, session_path)
            if open_whatsapp:
                open_whatsapp_web(page)
                save_session(context, session_path)
        return playwright, browser, context, page, gmail_ok

    browser = playwright.chromium.launch(
        headless=headless,
        args=_chromium_launch_args(),
    )
    context = _new_browser_context(
        browser,
        session_path if Path(session_path).exists() else None,
    )
    page = context.new_page()

    email, password = _gmail_credentials()
    if email and password:
        gmail_ok = login_gmail(page, email, password)
    else:
        gmail_ok = ensure_gmail_login(page)

    if gmail_ok:
        save_session(context, session_path)
        if open_whatsapp:
            open_whatsapp_web(page)
            save_session(context, session_path)

    return playwright, browser, context, page, gmail_ok


def ensure_whatsapp_session(
    headless: bool | None = None,
) -> tuple[Playwright, Browser | None, BrowserContext, Page, bool]:
    """Launch persistent browser profile and open WhatsApp Web."""
    return ensure_whatsapp_browser_session(headless)


__all__ = [
    "WHATSAPP_WEB_URL",
    "GMAIL_INBOX_URL",
    "launch_browser",
    "save_session",
    "load_session",
    "login_gmail",
    "ensure_gmail_login",
    "ensure_gmail_browser_session",
    "ensure_whatsapp_browser_session",
    "launch_persistent_browser",
    "launch_whatsapp_browser_from_session",
    "try_connect_browser",
    "open_whatsapp_web",
    "wait_for_whatsapp_login",
    "navigate_to_contact",
    "open_chat_search",
    "ensure_whatsapp_session",
    "close_browser_session",
]
