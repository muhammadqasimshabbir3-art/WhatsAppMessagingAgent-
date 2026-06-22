"""Tests for HTML dashboard report generator."""

from agent.custom_tools.html_report_generator import generate_html_dashboard_report_sync


def test_generates_html_dashboard(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    output = tmp_path / "test_dashboard.html"
    state = {
        "contact_filter": "Alice",
        "read_chats_found": 1,
        "chats_scanned": 3,
        "chat_messages": [
            {
                "author": "Alice",
                "text": "Hello!",
                "category": "positive",
                "engagement_priority": "medium",
                "sentiment_score": 0.8,
                "timestamp": "1 day ago",
            }
        ],
        "analyzed_messages": [
            {
                "author": "Alice",
                "text": "Hello!",
                "category": "positive",
                "engagement_priority": "medium",
                "sentiment_score": 0.8,
                "timestamp": "1 day ago",
            }
        ],
        "positive_messages": [
            {"author": "Alice", "text": "Hello!", "category": "positive"}
        ],
        "negative_messages": [],
        "neutral_messages": [],
        "question_messages": [],
        "suggestion_messages": [],
        "spam_messages": [],
        "unanswered_messages": [{"author": "Alice", "text": "Hello!"}],
        "generated_replies": [],
        "reply_statistics": {"replies_generated": 0, "replies_posted": 0},
    }

    result = generate_html_dashboard_report_sync(state, str(output))
    assert output.exists()
    assert "HTML dashboard report generated" in result
    content = output.read_text(encoding="utf-8")
    assert "Alice" in content
    assert "Hello!" in content
    assert "Executive Summary" in content
    assert "WhatsApp Messaging Dashboard" in content


def test_html_report_replaces_existing_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    output = tmp_path / "test_dashboard.html"
    output.write_text("old report", encoding="utf-8")
    state = {
        "contact_filter": "Alice",
        "read_chats_found": 1,
        "chat_messages": [],
        "analyzed_messages": [],
        "positive_messages": [],
        "negative_messages": [],
        "neutral_messages": [],
        "question_messages": [],
        "suggestion_messages": [],
        "spam_messages": [],
        "unanswered_messages": [],
        "generated_replies": [],
        "reply_statistics": {},
    }

    generate_html_dashboard_report_sync(state, str(output))
    content = output.read_text(encoding="utf-8")
    assert "old report" not in content
    assert "WhatsApp Messaging Dashboard" in content
