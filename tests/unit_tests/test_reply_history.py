"""Tests for reply history persistence."""

from agent.custom_tools.reply_history import (
    build_reply_record,
    get_reply_history,
    record_reply_entries,
)


def test_record_and_load_reply_history(tmp_path, monkeypatch):
    history_file = tmp_path / "reply_history.json"
    monkeypatch.setattr(
        "agent.custom_tools.reply_history.HISTORY_PATH",
        history_file,
    )

    reply = {
        "message_id": "msg_1",
        "author": "Alice",
        "text": "Hello!",
        "category": "positive",
        "reply_text": "Hi there!",
        "engagement_priority": "medium",
        "sentiment_score": 0.9,
    }

    records = record_reply_entries(
        [reply],
        contact_name="Alice",
        status="generated",
    )
    assert len(records) == 1
    assert records[0]["message_author"] == "Alice"
    assert records[0]["status"] == "generated"

    loaded = get_reply_history(contact_name="Alice")
    assert len(loaded) == 1
    assert loaded[0]["reply_text"] == "Hi there!"


def test_build_reply_record():
    record = build_reply_record(
        {
            "author": "User",
            "text": "Question?",
            "category": "question",
            "reply_text": "Here is the answer.",
            "message_id": "msg_0",
        },
        contact_name="Alice",
        status="posted",
        posted=True,
    )
    assert record["posted"] is True
    assert record["status"] == "posted"
