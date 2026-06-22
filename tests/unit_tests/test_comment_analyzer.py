"""Tests for message analysis heuristics."""

from agent.custom_tools.comment_analyzer import analyze_single_message


def test_heuristic_question_classification():
    message = {"author": "User", "text": "How are you doing?", "likes": 0}
    result = analyze_single_message(message, contact_name="Alice")
    assert result["category"] == "question"


def test_heuristic_positive_classification(monkeypatch):
    def fake_model():
        raise ValueError("no api")

    monkeypatch.setattr("agent.custom_tools.comment_analyzer._get_model", fake_model)
    message = {
        "author": "Alice",
        "text": "Love this, thanks so much!",
        "likes": 0,
    }
    result = analyze_single_message(message)
    assert result["category"] == "positive"
    assert result["sentiment_score"] > 0
