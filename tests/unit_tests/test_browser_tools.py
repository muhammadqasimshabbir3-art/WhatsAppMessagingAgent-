"""Unit tests for browser login helpers."""

from agent.custom_tools import browser_tools


def test_login_timeout_defaults_to_120s(monkeypatch):
    monkeypatch.delenv("BROWSER_LOGIN_TIMEOUT_MS", raising=False)
    assert browser_tools._login_timeout_ms() == 120000


def test_login_timeout_respects_env(monkeypatch):
    monkeypatch.setenv("BROWSER_LOGIN_TIMEOUT_MS", "60000")
    assert browser_tools._login_timeout_ms() == 60000


def test_login_timeout_has_minimum(monkeypatch):
    monkeypatch.setenv("BROWSER_LOGIN_TIMEOUT_MS", "1000")
    assert browser_tools._login_timeout_ms() == 30000


class _FakeLocator:
    def __init__(self, visible: bool):
        self._visible = visible

    @property
    def first(self):
        return self

    def is_visible(self, timeout=0):
        return self._visible


class _FakePage:
    def __init__(self, url: str, *, email_visible=False, password_visible=False, inbox_visible=False):
        self.url = url
        self._email_visible = email_visible
        self._password_visible = password_visible
        self._inbox_visible = inbox_visible

    def locator(self, selector: str):
        if selector in browser_tools.EMAIL_SELECTORS:
            return _FakeLocator(self._email_visible)
        if selector in browser_tools.PASSWORD_SELECTORS:
            return _FakeLocator(self._password_visible)
        if selector in browser_tools.GMAIL_LOGGED_IN_SELECTORS:
            return _FakeLocator(self._inbox_visible)
        return _FakeLocator(False)


def test_google_sign_in_page_detected_on_accounts_url():
    page = _FakePage("https://accounts.google.com/v3/signin")
    assert browser_tools._is_google_sign_in_page(page) is True
    assert browser_tools._is_gmail_logged_in(page) is False


def test_gmail_not_logged_in_without_inbox_ui():
    page = _FakePage("https://mail.google.com/mail/u/0/#inbox", inbox_visible=False)
    assert browser_tools._is_gmail_logged_in(page) is False


def test_gmail_logged_in_when_inbox_visible():
    page = _FakePage("https://mail.google.com/mail/u/0/#inbox", inbox_visible=True)
    assert browser_tools._is_google_sign_in_page(page) is False
    assert browser_tools._is_gmail_logged_in(page) is True
