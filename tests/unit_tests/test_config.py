"""Tests for environment configuration."""

import os

from agent.config import (
    apply_runtime_overrides,
    get_whatsapp_config,
    is_category_reply_enabled,
)


def test_config_max_replies_default(monkeypatch):
    monkeypatch.delenv("MAX_REPLIES_PER_RUN", raising=False)
    monkeypatch.delenv("REPLY_PERSONALITY", raising=False)
    get_whatsapp_config.cache_clear()
    config = get_whatsapp_config()
    assert config["max_replies_per_run"] == 5
    assert config["reply_personality"] == "friendly"


def test_browser_profile_defaults(monkeypatch):
    monkeypatch.delenv("BROWSER_PROFILE_PATH", raising=False)
    monkeypatch.delenv("BROWSER_CHANNEL", raising=False)
    get_whatsapp_config.cache_clear()
    config = get_whatsapp_config()
    assert config["browser_profile_path"] == "./data/chrome_profile"
    assert config["browser_channel"] == ""


def test_gmail_login_credentials_from_env(monkeypatch):
    monkeypatch.setenv("EMAIL", "user@gmail.com")
    monkeypatch.setenv("PASSWORD", "secret")
    get_whatsapp_config.cache_clear()
    config = get_whatsapp_config()
    assert config["email"] == "user@gmail.com"
    assert config["password"] == "secret"
    monkeypatch.delenv("EMAIL", raising=False)
    monkeypatch.delenv("PASSWORD", raising=False)
    get_whatsapp_config.cache_clear()


def test_inbox_scan_defaults(monkeypatch):
    monkeypatch.delenv("MAX_CHATS_TO_PROCESS", raising=False)
    monkeypatch.delenv("MAX_MESSAGES_PER_CHAT", raising=False)
    monkeypatch.delenv("REPLY_ONLY_UNREAD_CHATS", raising=False)
    monkeypatch.delenv("REPLY_ONLY_READ_CHATS", raising=False)
    get_whatsapp_config.cache_clear()
    config = get_whatsapp_config()
    assert config["max_chats_to_process"] == 5
    assert config["max_messages_per_chat"] == 20
    assert config["reply_only_unread_chats"] is True


def test_reply_category_defaults(monkeypatch):
    monkeypatch.delenv("REPLY_TO_POSITIVE", raising=False)
    monkeypatch.delenv("REPLY_TO_SPAM", raising=False)
    get_whatsapp_config.cache_clear()
    assert is_category_reply_enabled("positive") is True
    assert is_category_reply_enabled("spam") is False


def test_reply_category_override(monkeypatch):
    monkeypatch.setenv("REPLY_TO_NEGATIVE", "true")
    get_whatsapp_config.cache_clear()
    assert is_category_reply_enabled("negative") is True


def test_apply_runtime_overrides_from_ui(monkeypatch):
    monkeypatch.setenv("MAX_REPLIES_PER_RUN", "5")
    monkeypatch.setenv("ENABLE_MESSAGE_REPLIES", "false")
    monkeypatch.setenv("REPLY_PERSONALITY", "friendly")
    get_whatsapp_config.cache_clear()

    apply_runtime_overrides(
        {
            "max_replies_per_run": 3,
            "max_chats_to_process": 2,
            "max_messages_per_chat": 25,
            "reply_personality": "professional",
            "enable_message_replies": True,
            "reply_only_unread_chats": True,
            "keep_browser_open": True,
            "email_reports": True,
            "reply_to_negative": True,
            "contact_filter": "Alice",
            "email_recipient": "run@example.com",
        }
    )
    config = get_whatsapp_config()
    assert config["max_replies_per_run"] == 3
    assert config["max_chats_to_process"] == 2
    assert config["max_messages_per_chat"] == 25
    assert config["reply_personality"] == "professional"
    assert config["enable_message_replies"] is True
    assert config["reply_only_unread_chats"] is True
    assert config["keep_browser_open"] is True
    assert config["email_reports"] is True
    assert config["reply_to_negative"] is True
    assert config["contact_filter"] == "Alice"
    assert os.getenv("GMAIL_DEFAULT_RECIPIENT") == "run@example.com"
