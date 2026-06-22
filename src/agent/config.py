"""Environment-driven configuration for WhatsApp Messaging Agent."""

from __future__ import annotations

import os
from functools import lru_cache


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key, str(default)).strip().lower()
    return value in ("1", "true", "yes", "on")


def _set_env_if_present(key: str, value: object | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text == "":
        return
    os.environ[key] = text


def _set_env_bool_if_present(key: str, value: object | None) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        os.environ[key] = "true" if value else "false"
        return
    text = str(value).strip().lower()
    if text == "":
        return
    os.environ[key] = "true" if text in ("1", "true", "yes", "on") else "false"


def _set_env_int_if_present(key: str, value: object | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text == "":
        return
    os.environ[key] = str(int(text))


def apply_runtime_overrides(state: dict | None = None) -> None:
    """Apply per-run UI overrides to process env before reading config."""
    if not state:
        return

    _set_env_int_if_present("MAX_CHATS_TO_PROCESS", state.get("max_chats_to_process"))
    _set_env_int_if_present("MAX_MESSAGES_PER_CHAT", state.get("max_messages_per_chat"))
    _set_env_int_if_present("MAX_REPLIES_PER_RUN", state.get("max_replies_per_run"))
    _set_env_if_present("REPLY_PERSONALITY", state.get("reply_personality"))
    _set_env_if_present("CONTACT_FILTER", state.get("contact_filter"))
    _set_env_bool_if_present("ENABLE_MESSAGE_REPLIES", state.get("enable_message_replies"))
    _set_env_bool_if_present("REPLY_ONLY_UNREAD_CHATS", state.get("reply_only_unread_chats"))
    _set_env_bool_if_present("KEEP_BROWSER_OPEN", state.get("keep_browser_open"))
    _set_env_bool_if_present("EMAIL_REPORTS", state.get("email_reports"))
    _set_env_bool_if_present("REPLY_TO_POSITIVE", state.get("reply_to_positive"))
    _set_env_bool_if_present("REPLY_TO_NEGATIVE", state.get("reply_to_negative"))
    _set_env_bool_if_present("REPLY_TO_NEUTRAL", state.get("reply_to_neutral"))
    _set_env_bool_if_present("REPLY_TO_QUESTIONS", state.get("reply_to_questions"))
    _set_env_bool_if_present("REPLY_TO_SUGGESTIONS", state.get("reply_to_suggestions"))
    _set_env_bool_if_present("REPLY_TO_SPAM", state.get("reply_to_spam"))

    recipient = str(state.get("email_recipient") or "").strip()
    if recipient:
        os.environ["GMAIL_DEFAULT_RECIPIENT"] = recipient

    get_whatsapp_config.cache_clear()


def _env_secret(key: str) -> str:
    value = os.getenv(key, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def _reply_only_unread_from_env() -> bool:
    """Prefer REPLY_ONLY_UNREAD_CHATS; legacy REPLY_ONLY_READ_CHATS inverts the flag."""
    unread_raw = os.getenv("REPLY_ONLY_UNREAD_CHATS")
    if unread_raw is not None and unread_raw.strip() != "":
        return _env_bool("REPLY_ONLY_UNREAD_CHATS", True)
    read_raw = os.getenv("REPLY_ONLY_READ_CHATS")
    if read_raw is not None and read_raw.strip() != "":
        return not _env_bool("REPLY_ONLY_READ_CHATS", True)
    return True


@lru_cache(maxsize=1)
def get_whatsapp_config() -> dict:
    """Load WhatsApp inbox-reply configuration from environment."""
    return {
        "email": _env_secret("EMAIL"),
        "password": _env_secret("PASSWORD"),
        "contact_filter": os.getenv("CONTACT_FILTER", "").strip(),
        "enable_message_replies": _env_bool("ENABLE_MESSAGE_REPLIES", False),
        "email_reports": _env_bool("EMAIL_REPORTS", True),
        "reply_only_unread_chats": _reply_only_unread_from_env(),
        "reply_to_positive": _env_bool("REPLY_TO_POSITIVE", True),
        "reply_to_negative": _env_bool("REPLY_TO_NEGATIVE", True),
        "reply_to_neutral": _env_bool("REPLY_TO_NEUTRAL", True),
        "reply_to_questions": _env_bool("REPLY_TO_QUESTIONS", True),
        "reply_to_suggestions": _env_bool("REPLY_TO_SUGGESTIONS", True),
        "reply_to_spam": _env_bool("REPLY_TO_SPAM", False),
        "max_chats_to_process": int(os.getenv("MAX_CHATS_TO_PROCESS", "5")),
        "max_messages_per_chat": int(os.getenv("MAX_MESSAGES_PER_CHAT", "20")),
        "max_replies_per_run": int(os.getenv("MAX_REPLIES_PER_RUN", "5")),
        "reply_personality": os.getenv("REPLY_PERSONALITY", "friendly").strip().lower(),
        "browser_profile_path": os.getenv(
            "BROWSER_PROFILE_PATH", "./data/chrome_profile"
        ).strip(),
        "browser_channel": os.getenv("BROWSER_CHANNEL", "").strip(),
        "session_path": os.getenv(
            "WHATSAPP_SESSION_PATH", "./data/whatsapp_session.json"
        ),
        "reply_history_path": os.getenv(
            "REPLY_HISTORY_PATH", "./data/reply_history.json"
        ),
        "headless": _env_bool("BROWSER_HEADLESS", True),
        "keep_browser_open": _env_bool("KEEP_BROWSER_OPEN", True),
    }


def is_category_reply_enabled(category: str) -> bool:
    """Return whether replies are enabled for a message category."""
    config = get_whatsapp_config()
    mapping = {
        "positive": config["reply_to_positive"],
        "negative": config["reply_to_negative"],
        "neutral": config["reply_to_neutral"],
        "question": config["reply_to_questions"],
        "suggestion": config["reply_to_suggestions"],
        "spam": config["reply_to_spam"],
    }
    return mapping.get(category.lower(), False)
