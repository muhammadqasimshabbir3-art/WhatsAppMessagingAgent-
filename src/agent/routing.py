"""Intent detection and routing for WhatsApp Messaging Agent."""

from __future__ import annotations

import re

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

WHATSAPP_KEYWORDS = (
    "whatsapp",
    "whats app",
    "message",
    "messages",
    "chat",
    "reply",
    "replies",
    "contact",
    "conversation",
    "send message",
    "respond",
)

REPORT_KEYWORDS = (
    "pdf",
    "report",
    "generate report",
    "create report",
)

EMAIL_KEYWORDS = (
    "email",
    "e-mail",
    "mail me",
    "send me",
    "send report",
    "email report",
)


def get_latest_user_text(messages: list[AnyMessage]) -> str:
    """Return the most recent human message text."""
    for message in reversed(messages):
        if (
            isinstance(message, HumanMessage)
            or getattr(message, "type", None) == "human"
        ):
            content = message.content
            if isinstance(content, str):
                return content
            return str(content)
    return ""


def extract_phone_number(text: str) -> str:
    """Extract a phone number from user text."""
    match = re.search(r"\+?\d[\d\s\-()]{7,}\d", text)
    if match:
        return re.sub(r"[\s\-()]", "", match.group(0))
    return ""


def extract_contact_name(text: str) -> str:
    """Extract contact name from natural language."""
    patterns = (
        r"(?i)(?:message|reply to|chat with|contact)\s+['\"]?([^'\".\n]+?)['\"]?(?:\s+on whatsapp)?$",
        r"(?i)for\s+contact\s+['\"]?([^'\".\n]+)['\"]?",
        r"(?i)whatsapp\s+['\"]?([^'\".\n]+)['\"]?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def wants_whatsapp_messaging(text: str, state_contact_filter: str = "") -> bool:
    """Detect whether the user wants WhatsApp inbox automation."""
    if not text.strip():
        return True
    _ = state_contact_filter
    lowered = text.lower()
    if extract_phone_number(text):
        return True
    if any(keyword in lowered for keyword in WHATSAPP_KEYWORDS):
        return True
    if "web.whatsapp.com" in lowered:
        return True
    return False


def wants_pdf_report(text: str) -> bool:
    """Detect PDF report generation intent."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in REPORT_KEYWORDS)


def wants_email_report(text: str) -> bool:
    """Detect email report intent."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in EMAIL_KEYWORDS)


def is_empty_ai_message(response: AIMessage) -> bool:
    """Check if an AI message has no usable text content."""
    content = response.content
    if content is None or content == "":
        return True
    if isinstance(content, list):
        return len(content) == 0
    if isinstance(content, str):
        return not content.strip()
    return False


def build_analysis_summary(state: dict) -> str:
    """Build a human-readable summary from analysis state."""
    total = len(state.get("chat_messages") or [])
    analyzed = state.get("analyzed_messages") or []
    stats = state.get("reply_statistics") or {}
    contact = (
        state.get("contact_filter")
        or state.get("whatsapp_contact_name")
        or state.get("greeting_contact")
        or "Unknown Contact"
    )

    lines = [
        f"**WhatsApp Conversation Analysis — {contact}**",
        "",
        f"- Total inbound messages collected: {total}",
        f"- Positive: {len(state.get('positive_messages') or [])}",
        f"- Negative: {len(state.get('negative_messages') or [])}",
        f"- Neutral: {len(state.get('neutral_messages') or [])}",
        f"- Questions: {len(state.get('question_messages') or [])}",
        f"- Suggestions: {len(state.get('suggestion_messages') or [])}",
        f"- Spam: {len(state.get('spam_messages') or [])}",
        f"- Unanswered: {len(state.get('unanswered_messages') or [])}",
        f"- Reply targets selected: {len(state.get('reply_targets') or [])}",
        f"- Replies generated: {stats.get('replies_generated', len(state.get('generated_replies') or []))}",
        f"- Replies sent: {stats.get('replies_posted', 0)}",
        f"- Replies failed: {stats.get('replies_failed', len(state.get('failed_replies') or []))}",
    ]

    if state.get("pdf_path"):
        lines.extend(["", f"PDF report: `{state['pdf_path']}`"])
    if state.get("html_path"):
        lines.extend(["", f"HTML dashboard: `{state['html_path']}`"])

    if analyzed:
        high_priority = [
            msg
            for msg in analyzed
            if msg.get("engagement_priority") == "high" and not msg.get("replied")
        ][:3]
        if high_priority:
            lines.extend(["", "**Top messages to respond to:**"])
            for message in high_priority:
                lines.append(
                    f"- [{message.get('category')}] {message.get('author')}: "
                    f"{message.get('text', '')[:120]}"
                )

    return "\n".join(lines)


def format_login_result(logged_in: bool, contact_name: str = "") -> AIMessage:
    """Format login node result."""
    if logged_in:
        msg = "Successfully logged in to WhatsApp Web."
        if contact_name:
            msg += f" Session ready for contact: {contact_name}"
        return AIMessage(content=msg)
    return AIMessage(
        content=(
            "WhatsApp Web login failed. Scan the QR code in the browser "
            "(set BROWSER_HEADLESS=false for first login)."
        )
    )


__all__ = [
    "get_latest_user_text",
    "extract_phone_number",
    "extract_contact_name",
    "wants_whatsapp_messaging",
    "wants_pdf_report",
    "wants_email_report",
    "is_empty_ai_message",
    "build_analysis_summary",
    "format_login_result",
]
