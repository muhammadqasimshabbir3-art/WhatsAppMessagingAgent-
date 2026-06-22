"""Fixtures for integration tests — avoid real browser/WhatsApp calls."""

from __future__ import annotations

import pytest


def _mock_analyze_messages(messages, contact_name=""):
    analyzed = []
    for message in messages:
        analyzed.append(
            {
                **message,
                "category": "positive",
                "sentiment_score": 0.8,
                "engagement_priority": "medium",
            }
        )
    return {
        "analyzed_messages": analyzed,
        "positive_messages": analyzed,
        "negative_messages": [],
        "neutral_messages": [],
        "question_messages": [],
        "suggestion_messages": [],
        "spam_messages": [],
        "unanswered_messages": analyzed,
    }


def _mock_generate_replies(targets, contact_name="", prior_stats=None):
    return {
        "generated_replies": [],
        "reply_statistics": {
            "replies_generated": 0,
            "replies_skipped": len(targets),
            "posting_enabled": False,
            "filters": {},
        },
    }


@pytest.fixture(autouse=True)
def mock_playwright_and_whatsapp(monkeypatch):
    """Stub Playwright and WhatsApp fetch so integration tests do not need browsers."""
    monkeypatch.setattr(
        "agent.custom_tools.browser_tools.ensure_whatsapp_browser_session",
        lambda *args, **kwargs: (None, None, None, None, True),
    )
    monkeypatch.setattr(
        "agent.custom_tools.browser_tools.launch_persistent_browser",
        lambda *args, **kwargs: (None, None, None, None),
    )
    monkeypatch.setattr(
        "agent.custom_tools.browser_tools.ensure_gmail_browser_session",
        lambda *args, **kwargs: (None, None, None, None, True),
    )
    monkeypatch.setattr(
        "agent.custom_tools.browser_tools.ensure_whatsapp_session",
        lambda *args, **kwargs: (None, None, None, None, True),
    )
    monkeypatch.setattr(
        "agent.custom_tools.browser_tools.close_browser_session",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "agent.workflow_executor.fetch_read_conversations",
        lambda contact_filter="": {
            "success": True,
            "chats_scanned": 3,
            "unread_chats_found": 1,
            "read_chats_found": 1,
            "conversations": [
                {
                    "contact_name": "Alice",
                    "preview": "Hello there!",
                    "last_seen": "1 hour ago",
                    "is_unread": True,
                    "messages": [
                        {
                            "author": "Alice",
                            "text": "Hello there!",
                            "timestamp": "1 hour ago",
                            "is_outgoing": False,
                            "message_id": "msg_0",
                        }
                    ],
                    "inbound_messages": [
                        {
                            "author": "Alice",
                            "contact_name": "Alice",
                            "text": "Hello there!",
                            "timestamp": "1 hour ago",
                            "is_outgoing": False,
                            "message_id": "msg_0",
                        }
                    ],
                }
            ],
            "chat_messages": [
                {
                    "author": "Alice",
                    "contact_name": "Alice",
                    "text": "Hello there!",
                    "timestamp": "1 hour ago",
                    "replied": False,
                    "message_id": "msg_0",
                    "is_outgoing": False,
                }
            ],
            "inbound_messages_count": 1,
        },
    )
    monkeypatch.setattr(
        "agent.workflow_executor.send_replies_to_messages",
        lambda replies, enabled=True: {"posted": 0, "failed": 0, "replies": replies},
    )
    monkeypatch.setattr(
        "agent.workflow_executor.analyze_messages",
        _mock_analyze_messages,
    )
    monkeypatch.setattr(
        "agent.workflow_executor.generate_replies",
        _mock_generate_replies,
    )
    monkeypatch.setattr(
        "agent.custom_tools.html_report_generator._generate_llm_executive_summary",
        lambda state: "Test executive summary.",
    )
