"""Select which analyzed messages should receive replies."""

from __future__ import annotations

from typing import Any

from agent.config import is_category_reply_enabled


def _author_matches_contact(author: str, contact_name: str) -> bool:
    if not contact_name or not author:
        return False
    normalized_contact = contact_name.lower().strip()
    normalized_author = author.lower().strip()
    return (
        normalized_contact in normalized_author
        or normalized_author in normalized_contact
    )


def _positive_reply_score(message: dict[str, Any]) -> float:
    sentiment = float(message.get("sentiment_score") or 0)
    priority_boost = {"high": 3, "medium": 2, "low": 1}.get(
        str(message.get("engagement_priority") or "low"), 1
    )
    likes = int(message.get("likes") or 0)
    return likes * 10 + sentiment * 5 + priority_boost


def _is_eligible(message: dict[str, Any], contact_name: str = "") -> bool:
    # Greeting messages (direct-contact mode) always qualify for a reply.
    if message.get("is_greeting"):
        return True
    if message.get("is_outgoing"):
        return False
    if message.get("agent_replied") or message.get("posted"):
        return False
    if message.get("reply_disabled"):
        return False
    category = str(message.get("category") or "neutral").lower()
    if not is_category_reply_enabled(category):
        return False
    author = str(message.get("author") or message.get("contact_name") or "")
    if contact_name and _author_matches_contact(author, contact_name) and message.get("is_channel_owner"):
        return False
    return True


def select_reply_targets(
    analyzed_messages: list[dict[str, Any]],
    *,
    limit: int = 5,
    contact_name: str = "",
) -> list[dict[str, Any]]:
    """Pick up to N messages to reply to (one latest inbound per contact)."""
    eligible = [m for m in analyzed_messages if _is_eligible(m, contact_name)]
    if not eligible:
        return []

    # Keep only the latest inbound message per contact.
    by_contact: dict[str, dict[str, Any]] = {}
    for message in eligible:
        key = str(message.get("contact_name") or message.get("author") or "contact")
        by_contact[key] = message

    ranked = sorted(
        by_contact.values(),
        key=_positive_reply_score,
        reverse=True,
    )
    if limit <= 0:
        return ranked
    selected = ranked[:limit]
    for index, message in enumerate(selected, start=1):
        message["reply_rank"] = index
    return selected


__all__ = ["select_reply_targets"]
