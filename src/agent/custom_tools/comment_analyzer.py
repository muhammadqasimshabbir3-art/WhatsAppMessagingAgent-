"""LLM and heuristic classification for WhatsApp messages."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent.config import get_whatsapp_config, is_category_reply_enabled

POSITIVE_WORDS = (
    "thanks",
    "thank you",
    "love",
    "great",
    "awesome",
    "amazing",
    "good",
    "nice",
    "happy",
    "excellent",
    "wonderful",
    "appreciate",
)
NEGATIVE_WORDS = (
    "bad",
    "terrible",
    "awful",
    "hate",
    "angry",
    "upset",
    "disappointed",
    "worst",
    "horrible",
    "frustrated",
)
QUESTION_MARKERS = ("?", "how", "what", "when", "where", "why", "who", "can you", "could you")
SPAM_MARKERS = ("click here", "free money", "winner", "lottery", "crypto pump")


def _get_model() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)


def _heuristic_analysis(message: dict[str, Any]) -> dict[str, Any]:
    text = str(message.get("text") or "").strip().lower()
    if not text:
        return {
            **message,
            "category": "neutral",
            "sentiment_score": 0.0,
            "engagement_priority": "low",
        }

    if any(marker in text for marker in SPAM_MARKERS):
        category = "spam"
        sentiment = -0.5
        priority = "low"
    elif "?" in text or any(text.startswith(q) for q in QUESTION_MARKERS):
        category = "question"
        sentiment = 0.1
        priority = "high"
    elif any(word in text for word in NEGATIVE_WORDS):
        category = "negative"
        sentiment = -0.7
        priority = "high"
    elif any(word in text for word in POSITIVE_WORDS):
        category = "positive"
        sentiment = 0.8
        priority = "medium"
    elif "suggest" in text or "should" in text or "could" in text:
        category = "suggestion"
        sentiment = 0.2
        priority = "medium"
    else:
        category = "neutral"
        sentiment = 0.0
        priority = "low"

    return {
        **message,
        "category": category,
        "sentiment_score": sentiment,
        "engagement_priority": priority,
    }


def analyze_single_message(
    message: dict[str, Any],
    contact_name: str = "",
) -> dict[str, Any]:
    """Classify one WhatsApp message."""
    if message.get("is_outgoing"):
        return {
            **message,
            "category": "neutral",
            "sentiment_score": 0.0,
            "engagement_priority": "low",
            "agent_replied": True,
        }

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _heuristic_analysis(message)

    author = str(message.get("author") or message.get("contact_name") or contact_name or "Contact")
    prompt = (
        "Classify this WhatsApp message. Return JSON only with keys: "
        "category (positive|negative|neutral|question|suggestion|spam), "
        "sentiment_score (-1 to 1), engagement_priority (low|medium|high).\n\n"
        f"Author: {author}\nMessage: {message.get('text', '')}"
    )
    try:
        model = _get_model()
        response = model.invoke(
            [
                SystemMessage(content="You classify WhatsApp messages for a messaging dashboard."),
                HumanMessage(content=prompt),
            ]
        )
        raw = str(response.content).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return _heuristic_analysis(message)
        data = json.loads(match.group())
        return {
            **message,
            "category": str(data.get("category", "neutral")).lower(),
            "sentiment_score": float(data.get("sentiment_score", 0)),
            "engagement_priority": str(data.get("engagement_priority", "low")).lower(),
        }
    except Exception:
        return _heuristic_analysis(message)


def _bucket_messages(analyzed: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "positive_messages": [],
        "negative_messages": [],
        "neutral_messages": [],
        "question_messages": [],
        "suggestion_messages": [],
        "spam_messages": [],
        "unanswered_messages": [],
    }
    mapping = {
        "positive": "positive_messages",
        "negative": "negative_messages",
        "neutral": "neutral_messages",
        "question": "question_messages",
        "suggestion": "suggestion_messages",
        "spam": "spam_messages",
    }
    for message in analyzed:
        category = str(message.get("category") or "neutral").lower()
        key = mapping.get(category, "neutral_messages")
        buckets[key].append(message)
        if not message.get("replied") and not message.get("is_outgoing"):
            buckets["unanswered_messages"].append(message)
    return buckets


def analyze_messages(
    messages: list[dict[str, Any]],
    contact_name: str = "",
) -> dict[str, Any]:
    """Analyze a list of WhatsApp messages and bucket by category."""
    config = get_whatsapp_config()
    analyzed: list[dict[str, Any]] = []
    for message in messages:
        result = analyze_single_message(message, contact_name=contact_name)
        category = str(result.get("category") or "neutral").lower()
        if not is_category_reply_enabled(category):
            result["reply_disabled"] = True
        analyzed.append(result)

    buckets = _bucket_messages(analyzed)
    return {
        "analyzed_messages": analyzed,
        **buckets,
        "reply_statistics": {
            "messages_analyzed": len(analyzed),
            "contact_filter": config.get("contact_filter", ""),
        },
    }


__all__ = ["analyze_messages", "analyze_single_message"]
