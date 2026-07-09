"""Unit tests for WhatsApp automation tools."""

from __future__ import annotations

from typing import Any
from agent.custom_tools import whatsapp_tools


def test_fetch_named_contact_conversation_inbound(monkeypatch):
    # Mock navigate_to_contact and scrape_conversation
    monkeypatch.setattr(whatsapp_tools, "navigate_to_contact", lambda page, name: None)
    monkeypatch.setattr(
        whatsapp_tools,
        "scrape_conversation",
        lambda page, name: [
            {"text": "hi", "is_outgoing": False, "timestamp": "12:00"}
        ],
    )

    result = whatsapp_tools._fetch_named_contact_conversation(None, "Asim Bhai", 20)
    assert result is not None
    assert result["contact_name"] == "Asim Bhai"
    assert result["is_greeting"] is True
    assert len(result["inbound_messages"]) == 1
    assert result["inbound_messages"][0]["text"] == "hi"
    assert result["inbound_messages"][0]["is_greeting"] is True
    assert result["inbound_messages"][0]["agent_replied"] is False


def test_fetch_named_contact_conversation_outgoing(monkeypatch):
    # Mock navigate_to_contact and scrape_conversation
    monkeypatch.setattr(whatsapp_tools, "navigate_to_contact", lambda page, name: None)
    monkeypatch.setattr(
        whatsapp_tools,
        "scrape_conversation",
        lambda page, name: [
            {"text": "hi", "is_outgoing": False, "timestamp": "12:00"},
            {"text": "hello back", "is_outgoing": True, "timestamp": "12:01"},
        ],
    )

    result = whatsapp_tools._fetch_named_contact_conversation(None, "Asim Bhai", 20)
    # Since the last message is outgoing (already replied), it should return None
    assert result is None


def test_fetch_named_contact_conversation_empty_creates_initial_message(monkeypatch):
    # Mock navigate_to_contact and scrape_conversation to return empty
    monkeypatch.setattr(whatsapp_tools, "navigate_to_contact", lambda page, name: None)
    monkeypatch.setattr(whatsapp_tools, "scrape_conversation", lambda page, name: [])

    result = whatsapp_tools._fetch_named_contact_conversation(None, "Asim Bhai", 20)
    assert result is not None
    assert result["contact_name"] == "Asim Bhai"
    assert result["is_greeting"] is True
    assert result["messages"] == []
    assert len(result["inbound_messages"]) == 1
    assert result["inbound_messages"][0]["is_initial_message"] is True
    assert result["inbound_messages"][0]["is_greeting"] is True
    assert result["inbound_messages"][0]["agent_replied"] is False
