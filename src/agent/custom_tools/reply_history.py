"""Persist WhatsApp reply history to JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_PATH = Path("./data/reply_history.json")


def _history_path() -> Path:
    return HISTORY_PATH


def _load_records() -> list[dict[str, Any]]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def _save_records(records: list[dict[str, Any]]) -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def build_reply_record(
    message: dict[str, Any],
    *,
    contact_name: str = "",
    status: str = "generated",
    posted: bool | None = None,
) -> dict[str, Any]:
    """Build a normalized reply history record."""
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "contact_name": contact_name or message.get("contact_name", ""),
        "message_id": message.get("message_id", ""),
        "message_author": message.get("author", ""),
        "message_text": message.get("text", ""),
        "message_category": message.get("category", ""),
        "reply_text": message.get("reply_text", ""),
        "engagement_priority": message.get("engagement_priority", ""),
        "sentiment_score": message.get("sentiment_score", ""),
        "status": status,
        "posted": posted if posted is not None else bool(message.get("posted")),
        "post_error": message.get("post_error", ""),
        "screenshot_path": message.get("screenshot_path", ""),
    }


def record_reply_entries(
    replies: list[dict[str, Any]],
    *,
    contact_name: str = "",
    status: str = "generated",
) -> list[dict[str, Any]]:
    """Append reply records to history and return the new entries."""
    if not replies:
        return []
    records = _load_records()
    new_entries = [
        build_reply_record(
            reply,
            contact_name=str(reply.get("contact_name") or contact_name),
            status=status,
            posted=bool(reply.get("posted")) if status == "posted" else None,
        )
        for reply in replies
        if reply.get("reply_text")
    ]
    records.extend(new_entries)
    _save_records(records)
    return new_entries


def get_reply_history(contact_name: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Load recent reply history, optionally filtered by contact."""
    records = _load_records()
    if contact_name:
        needle = contact_name.lower().strip()
        records = [
            record
            for record in records
            if needle in str(record.get("contact_name", "")).lower()
            or needle in str(record.get("message_author", "")).lower()
        ]
    return records[-limit:]


__all__ = [
    "build_reply_record",
    "get_reply_history",
    "record_reply_entries",
    "HISTORY_PATH",
]
