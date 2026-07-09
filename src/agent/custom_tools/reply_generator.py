"""AI reply generation for WhatsApp conversations."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent.config import get_whatsapp_config, is_category_reply_enabled


def _get_model() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.3, api_key=api_key)


def _format_conversation_context(message: dict[str, Any]) -> str:
    history = message.get("conversation_history") or []
    if not history:
        return ""
    limit = max(1, int(get_whatsapp_config().get("max_messages_per_chat", 10)))
    lines: list[str] = []
    for item in history[-limit:]:
        speaker = "Me" if item.get("is_outgoing") else item.get("author", "Contact")
        text = str(item.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    if not lines:
        return ""
    return (
        f"Last {len(lines)} messages in this chat (use for reply context):\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _user_prompt_for_message(message: dict[str, Any], contact_name: str) -> str:
    contact = str(message.get("contact_name") or contact_name or "Contact")
    category = message.get("category", "neutral")
    context = _format_conversation_context(message)
    is_greeting = message.get("is_greeting", False)

    if is_greeting:
        return (
            f"You are opening a conversation on WhatsApp with '{contact}'.\n"
            f"{context}"
            "Based on the conversation history above, write one short, natural "
            "WhatsApp greeting or opener that feels appropriate for the relationship. "
            "If their last message was a question or request, respond to it naturally. "
            "If the conversation ended normally, start a friendly new exchange. "
            "Keep it under 280 characters. Do not use hashtags. "
            "Never mention automation or that you are an AI."
        )

    return (
        f"You are replying on WhatsApp to '{contact}'.\n"
        f"{context}"
        f"Their latest {category} message to reply to:\n"
        f"{message.get('text', '')}\n\n"
        "Write one short, natural WhatsApp reply based on the full conversation context. "
        "Keep it under 280 characters. Do not use hashtags. "
        "Never mention automation or that you are an AI."
    )


def generate_reply_for_message(
    message: dict[str, Any],
    contact_name: str = "",
    personality: str = "",
) -> str:
    """Generate a contextual reply for a WhatsApp chat message."""
    config = get_whatsapp_config()
    personality = personality or config.get("reply_personality", "friendly")
    model = _get_model()
    is_greeting = message.get("is_greeting", False)
    if is_greeting:
        system = (
            f"You write {personality}, natural WhatsApp greetings and openers. "
            "Match the tone and relationship style shown in the conversation history."
        )
    else:
        system = (
            f"You write {personality}, natural WhatsApp replies. "
            "Match the tone of the conversation and answer what was asked."
        )
    prompt = _user_prompt_for_message(message, contact_name)
    try:
        response = model.invoke(
            [SystemMessage(content=system), HumanMessage(content=prompt)]
        )
        return str(response.content).strip()
    except Exception:
        if is_greeting:
            return "Hey! How's it going?"
        return "Thanks for your message — I'll get back to you shortly."


def generate_replies(
    messages: list[dict[str, Any]],
    contact_name: str = "",
    prior_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate replies for selected messages using conversation context."""
    config = get_whatsapp_config()
    generated: list[dict[str, Any]] = []
    skipped = 0

    for message in messages:
        if message.get("agent_replied") or message.get("posted"):
            skipped += 1
            continue
        is_greeting = message.get("is_greeting", False)
        category = message.get("category", "neutral")
        if not is_greeting and not is_category_reply_enabled(category):
            skipped += 1
            continue
        name = str(message.get("contact_name") or contact_name or "Contact")
        reply_text = generate_reply_for_message(message, name)
        generated.append({**message, "contact_name": name, "reply_text": reply_text, "posted": False})

    stats = {
        **(prior_stats or {}),
        "total_messages": len(messages),
        "replies_generated": len(generated),
        "replies_skipped": skipped,
        "replies_target_limit": config["max_replies_per_run"],
        "posting_enabled": config["enable_message_replies"],
        "reply_personality": config.get("reply_personality", "friendly"),
    }
    return {"generated_replies": generated, "reply_statistics": stats}


__all__ = ["generate_replies", "generate_reply_for_message"]
