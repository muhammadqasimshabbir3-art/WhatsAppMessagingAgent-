"""Unit tests for message reply target selection."""

from agent.custom_tools.comment_selection import select_reply_targets


def _message(
    author: str,
    *,
    category: str = "positive",
    replied: bool = False,
    sentiment: float = 0.8,
    is_outgoing: bool = False,
) -> dict:
    return {
        "author": author,
        "text": f"Message from {author}",
        "category": category,
        "sentiment_score": sentiment,
        "engagement_priority": "medium",
        "replied": replied,
        "is_outgoing": is_outgoing,
    }


def test_select_reply_targets_allows_fewer_than_limit():
    analyzed = [_message("Alice"), _message("Bob")]
    selected = select_reply_targets(analyzed, limit=5)
    assert len(selected) == 2


def test_select_reply_targets_skips_outgoing_messages():
    analyzed = [
        _message("Alice", is_outgoing=True),
        _message("Bob"),
    ]
    selected = select_reply_targets(analyzed, limit=5)
    assert len(selected) == 1
    assert selected[0]["author"] == "Bob"


def test_select_reply_targets_skips_agent_replied():
    analyzed = [
        {**_message("Alice"), "agent_replied": True},
        _message("Bob"),
    ]
    selected = select_reply_targets(analyzed, limit=5)
    assert len(selected) == 1
    assert selected[0]["author"] == "Bob"
