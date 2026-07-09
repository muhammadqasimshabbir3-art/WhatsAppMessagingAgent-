"""Execute WhatsApp messaging workflow steps."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from agent.config import apply_runtime_overrides, get_whatsapp_config
from agent.custom_tools.comment_analyzer import analyze_messages
from agent.custom_tools.comment_selection import select_reply_targets
from agent.custom_tools.email_tools import send_smtp_email
from agent.custom_tools.html_report_generator import (
    _generate_llm_executive_summary,
    generate_html_dashboard_report_sync,
)
from agent.custom_tools.pdf_generator import _generate_whatsapp_report_pdf_sync
from agent.custom_tools.reply_generator import generate_replies
from agent.custom_tools.reply_history import record_reply_entries
from agent.custom_tools.whatsapp_tools import (
    fetch_read_conversations,
    release_browser_session,
    send_replies_to_messages,
)
from agent.routing import build_analysis_summary
from agent.task_planner import TaskPlan

REPORTS_DIR = Path("./reports")


def _build_recommendations(state: dict[str, Any]) -> list[str]:
    """Generate recommended actions from message analysis."""
    recommendations: list[str] = []
    unanswered = len(state.get("unanswered_messages") or [])
    questions = len(state.get("question_messages") or [])
    negative = len(state.get("negative_messages") or [])

    if unanswered > 0:
        recommendations.append(
            f"Reply to {unanswered} unanswered messages to keep the conversation going."
        )
    positive_count = len(state.get("positive_messages") or [])
    config = get_whatsapp_config()
    if positive_count:
        recommendations.append(
            f"Reply workflow targets up to {config['max_replies_per_run']} messages "
            f"({positive_count} positive found after analysis)."
        )
    if questions > 0:
        recommendations.append(
            f"Prioritize {questions} question messages — they expect a direct answer."
        )
    if negative > 0:
        recommendations.append(
            f"Address {negative} negative messages professionally."
        )
    if not recommendations:
        recommendations.append(
            "Conversation looks healthy. Keep monitoring new messages."
        )
    return recommendations


def _build_pdf_stats(state: dict[str, Any]) -> dict[str, int]:
    """Aggregate stats for PDF report."""
    stats = state.get("reply_statistics") or {}
    return {
        "total": len(state.get("chat_messages") or []),
        "positive": len(state.get("positive_messages") or []),
        "negative": len(state.get("negative_messages") or []),
        "neutral": len(state.get("neutral_messages") or []),
        "questions": len(state.get("question_messages") or []),
        "suggestions": len(state.get("suggestion_messages") or []),
        "spam": len(state.get("spam_messages") or []),
        "unanswered": len(state.get("unanswered_messages") or []),
        "replies_generated": stats.get(
            "replies_generated", len(state.get("generated_replies") or [])
        ),
        "replies_posted": stats.get("replies_posted", 0),
        "replies_failed": stats.get(
            "replies_failed", len(state.get("failed_replies") or [])
        ),
    }


def execute_whatsapp_login(state: dict[str, Any]) -> dict[str, Any]:
    """Open WhatsApp Web after logging into Gmail to ensure active session."""
    from agent.custom_tools.browser_tools import (
        WHATSAPP_WEB_URL,
        close_browser_session,
        ensure_gmail_browser_session,
        wait_for_whatsapp_login,
    )
    from agent.custom_tools.whatsapp_tools import _store_browser_session

    apply_runtime_overrides(state)
    config = get_whatsapp_config()
    playwright = browser = context = page = None
    whatsapp_logged_in = False
    keep_session_alive = False
    profile = config.get("browser_profile_path", "./data/chrome_profile")
    try:
        playwright, browser, context, page, gmail_ok = (
            ensure_gmail_browser_session(open_whatsapp=True)
        )
        if page is not None:
            _store_browser_session(playwright, browser, context, page)
            keep_session_alive = True

        if page is not None:
            try:
                whatsapp_logged_in = wait_for_whatsapp_login(page, block_for_qr=True)
            except TimeoutError:
                whatsapp_logged_in = False

        if whatsapp_logged_in:
            detail = f"Google & WhatsApp Web ready — profile saved at {profile}"
        else:
            detail = (
                f"Opened {WHATSAPP_WEB_URL} in Chrome profile ({profile}). "
                "Scan the QR code in the browser window (first time only)."
            )
        return {
            "gmail_logged_in": gmail_ok,
            "logged_in": whatsapp_logged_in,
            "whatsapp_logged_in": whatsapp_logged_in,
            "login_detail": detail,
            "whatsapp_login_detail": detail,
            **({"error": detail} if not keep_session_alive else {}),
        }
    except Exception as exc:
        return {
            "gmail_logged_in": False,
            "logged_in": False,
            "whatsapp_logged_in": False,
            "login_detail": str(exc),
            "whatsapp_login_detail": str(exc),
            "error": str(exc),
        }
    finally:
        if not keep_session_alive:
            close_browser_session(playwright, browser, context)


def _attach_conversation_context(
    conversations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten inbound messages and attach full thread context for reply generation."""
    flat: list[dict[str, Any]] = []
    for conv in conversations:
        contact = str(conv.get("contact_name") or "Contact")
        history = list(conv.get("messages") or [])
        for msg in conv.get("inbound_messages") or []:
            enriched = dict(msg)
            enriched["contact_name"] = contact
            enriched["conversation_history"] = history
            enriched["chat_preview"] = conv.get("preview", "")
            flat.append(enriched)
    return flat


def execute_fetch_chat_messages(state: dict[str, Any]) -> dict[str, Any]:
    """Scan inbox for unread chats and extract conversation messages.

    When a specific contact is named (via ``contact_filter``), the agent
    navigates directly to that contact's chat, reads the conversation history,
    and injects a greeting message — even if there are zero unread chats.
    It also processes any other unread inbox chats as normal.
    """
    contact_filter = str(
        state.get("contact_filter")
        or state.get("whatsapp_contact_name")
        or ""
    ).strip()
    result = fetch_read_conversations(contact_filter=contact_filter)
    if not result.get("success"):
        return {"error": result.get("error", "Failed to read conversations")}
    conversations = result.get("conversations") or []
    chat_messages = _attach_conversation_context(conversations)
    return {
        "whatsapp_logged_in": True,
        "whatsapp_login_detail": "Inbox open — chats scanned",
        "conversations": conversations,
        "chats_scanned": result.get("chats_scanned", 0),
        "unread_chats_found": result.get("unread_chats_found", 0),
        "read_chats_found": result.get("read_chats_found", 0),
        "eligible_chats_found": result.get("eligible_chats_found", 0),
        "greeting_injected": result.get("greeting_injected", False),
        "greeting_contact": result.get("greeting_contact", ""),
        "chat_messages": chat_messages,
        "inbound_messages_count": len(chat_messages),
    }


def execute_analyze_messages(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze collected messages with LLM classification."""
    messages = state.get("chat_messages") or []
    return analyze_messages(messages, contact_name="inbox")


def execute_select_reply_targets(state: dict[str, Any]) -> dict[str, Any]:
    """Pick up to N messages to reply to after full analysis."""
    apply_runtime_overrides(state)
    config = get_whatsapp_config()
    analyzed = list(state.get("analyzed_messages") or [])
    if not analyzed:
        analyzed = list(state.get("positive_messages") or [])
    contact_name = str(
        state.get("contact_filter")
        or state.get("whatsapp_contact_name")
        or state.get("greeting_contact")
        or ""
    ).strip()
    positive_total = len(state.get("positive_messages") or [])
    limit = state.get("max_replies_per_run")
    if limit is None or int(limit) <= 0:
        limit = config["max_replies_per_run"]
    if int(limit) <= 0:
        limit = 5
    else:
        limit = int(limit)
    reply_targets = select_reply_targets(
        analyzed,
        limit=limit,
        contact_name=contact_name,
    )
    return {
        "reply_targets": reply_targets,
        "reply_statistics": {
            **(state.get("reply_statistics") or {}),
            "positive_messages_total": positive_total,
            "reply_targets_selected": len(reply_targets),
            "reply_target_limit": limit,
        },
    }


def execute_generate_replies(state: dict[str, Any]) -> dict[str, Any]:
    """Generate AI replies for pre-selected messages."""
    config = get_whatsapp_config()
    contact_name = str(
        state.get("contact_filter")
        or state.get("whatsapp_contact_name")
        or state.get("greeting_contact")
        or ""
    ).strip()
    reply_targets = list(state.get("reply_targets") or [])
    if not reply_targets:
        analyzed = state.get("analyzed_messages") or []
        limit = config["max_replies_per_run"] if config["max_replies_per_run"] > 0 else 5
        reply_targets = select_reply_targets(
            analyzed,
            limit=limit,
            contact_name=contact_name,
        )
    result = generate_replies(
        reply_targets,
        contact_name,
        state.get("reply_statistics"),
    )
    generated = result.get("generated_replies") or []
    history = record_reply_entries(generated, contact_name="inbox", status="generated")
    return {**result, "reply_history": history, "reply_targets": reply_targets}


def execute_send_replies(state: dict[str, Any]) -> dict[str, Any]:
    """Send generated replies when enabled in .env."""
    apply_runtime_overrides(state)
    config = get_whatsapp_config()
    replies = list(state.get("generated_replies") or [])
    enable_replies = (
        state.get("enable_message_replies")
        if state.get("enable_message_replies") is not None
        else config["enable_message_replies"]
    )
    if not enable_replies or not replies:
        stats = dict(state.get("reply_statistics") or {})
        stats["replies_posted"] = 0
        return {"reply_statistics": stats}

    result = send_replies_to_messages(replies, enabled=bool(enable_replies))
    stats = dict(state.get("reply_statistics") or {})
    stats["replies_posted"] = result.get("posted", 0)
    stats["replies_failed"] = result.get("failed", 0)
    updated_replies = result.get("replies", replies)
    failed_replies = result.get("failed_replies") or [
        reply for reply in updated_replies if not reply.get("posted")
    ]
    history = record_reply_entries(
        updated_replies,
        contact_name=str(
            state.get("contact_filter")
            or state.get("whatsapp_contact_name")
            or state.get("greeting_contact")
            or ""
        ).strip(),
        status="posted",
    )
    return {
        "generated_replies": updated_replies,
        "failed_replies": failed_replies,
        "reply_statistics": stats,
        "reply_history": history,
        "screenshots": result.get("screenshots") or [],
    }


def execute_generate_pdf_report(state: dict[str, Any]) -> dict[str, Any]:
    """Generate PDF messaging report."""
    contact_name = state.get("contact_filter") or "WhatsApp Inbox"
    slug = re.sub(r"[^a-z0-9]+", "_", contact_name.lower()).strip("_") or "contact"
    output_path = str(REPORTS_DIR / f"{slug}_messaging_report.pdf")

    analyzed = state.get("analyzed_messages") or []
    top_opportunities = sorted(
        [msg for msg in analyzed if not msg.get("replied")],
        key=lambda msg: {"high": 3, "medium": 2, "low": 1}.get(
            msg.get("engagement_priority", "low"), 1
        ),
        reverse=True,
    )[:10]

    result = _generate_whatsapp_report_pdf_sync(
        contact_name=contact_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        stats=_build_pdf_stats(state),
        top_opportunities=top_opportunities,
        generated_replies=state.get("generated_replies") or [],
        recommendations=_build_recommendations(state),
        output_path=output_path,
        failed_replies=state.get("failed_replies") or [],
    )
    return {"pdf_path": output_path, "pdf_result": result}


def execute_generate_html_report(state: dict[str, Any]) -> dict[str, Any]:
    """Generate comprehensive HTML dashboard report."""
    release_browser_session()

    slug = "whatsapp_inbox"
    output_path = str(REPORTS_DIR / f"{slug}_dashboard_report.html")

    enriched_state = dict(state)
    enriched_state["recommendations"] = _build_recommendations(state)
    enriched_state["llm_summary"] = _generate_llm_executive_summary(enriched_state)

    result = generate_html_dashboard_report_sync(enriched_state, output_path)
    return {
        "html_path": output_path,
        "html_result": result,
        "llm_summary": enriched_state["llm_summary"],
    }


def execute_email_report(state: dict[str, Any]) -> dict[str, Any]:
    """Email HTML dashboard and PDF reports when EMAIL_REPORTS is enabled."""
    config = get_whatsapp_config()
    pdf_path = state.get("pdf_path", "")
    html_path = state.get("html_path", "")
    contact_name = state.get("contact_filter") or "WhatsApp Inbox"

    if not config["email_reports"]:
        saved = []
        if html_path and Path(html_path).exists():
            saved.append(html_path)
        if pdf_path and Path(pdf_path).exists():
            saved.append(pdf_path)
        if saved:
            return {
                "email_result": (
                    "EMAIL_REPORTS is disabled. Reports saved locally: "
                    + ", ".join(saved)
                ),
            }
        return {"email_result": "EMAIL_REPORTS is disabled. Report saved locally only."}

    attachments: list[str] = []
    if html_path and Path(html_path).exists():
        attachments.append(html_path)
    if pdf_path and Path(pdf_path).exists():
        attachments.append(pdf_path)

    if not attachments:
        return {"email_result": "No HTML or PDF report found to email."}

    body_lines = [
        build_analysis_summary(state),
        "",
        f"Contact: {contact_name}",
        "",
        "Attached reports:",
    ]
    for path in attachments:
        body_lines.append(f"- {path}")

    contact_label = f"{state.get('unread_chats_found', state.get('read_chats_found', 0))} unread chat(s)"
    result = send_smtp_email(
        subject=f"WhatsApp Inbox Reply Report — {contact_label}",
        body="\n".join(body_lines),
        attachment_paths=",".join(attachments),
        to_email=str(state.get("email_recipient") or "").strip(),
    )
    return {"email_result": result}


def execute_task_plan(
    plan: TaskPlan, initial_state: dict[str, Any] | None = None
) -> AIMessage:
    """Run each planned WhatsApp task in order and return a combined response."""
    state: dict[str, Any] = dict(initial_state or {})
    if plan.contact_filter:
        state.setdefault("contact_filter", plan.contact_filter)
    sections: list[str] = [f"**Workflow:** {plan.summary()}", ""]

    task_handlers = {
        "login": ("### Login", execute_whatsapp_login),
        "fetch_messages": ("### Chat Messages", execute_fetch_chat_messages),
        "analyze": ("### Message Analysis", execute_analyze_messages),
        "select_reply_targets": ("### Reply Targets", execute_select_reply_targets),
        "generate_replies": ("### Reply Generation", execute_generate_replies),
        "send_replies": ("### Send Replies", execute_send_replies),
        "generate_pdf": ("### PDF Report", execute_generate_pdf_report),
        "generate_html": ("### HTML Dashboard Report", execute_generate_html_report),
        "email_report": ("### Email Report", execute_email_report),
    }

    for task in plan.tasks:
        label, handler = task_handlers.get(task, (task, None))
        if handler is None:
            continue
        sections.append(label)
        updates = handler(state)
        if updates.get("error"):
            sections.append(f"Error: {updates['error']}")
            break
        state.update(updates)
        if task == "login":
            sections.append(
                "Chrome profile open — WhatsApp Web ready."
                if state.get("whatsapp_logged_in") or state.get("logged_in")
                else "WhatsApp login pending — scan QR in browser (first time only)."
            )
        elif task == "fetch_messages":
            msg_count = len(state.get('chat_messages') or [])
            greeting_contact = state.get('greeting_contact', '')
            if greeting_contact:
                sections.append(
                    f"Greeting injected for {greeting_contact} — "
                    f"{msg_count} message(s) to process."
                )
            else:
                sections.append(
                    f"Collected {msg_count} inbound messages."
                )
        elif task == "analyze":
            sections.append(build_analysis_summary(state))
        elif task == "select_reply_targets":
            stats = state.get("reply_statistics") or {}
            selected = stats.get(
                "reply_targets_selected", len(state.get("reply_targets") or [])
            )
            limit = stats.get("reply_target_limit", 5)
            sections.append(
                f"Selected {selected} of up to {limit} messages for replies."
            )
        elif task == "generate_replies":
            stats = state.get("reply_statistics") or {}
            sections.append(f"Generated {stats.get('replies_generated', 0)} replies.")
        elif task == "send_replies":
            stats = state.get("reply_statistics") or {}
            sections.append(
                f"Sent {stats.get('replies_posted', 0)} replies; "
                f"{stats.get('replies_failed', 0)} failed."
            )
        elif task == "generate_pdf":
            sections.append(state.get("pdf_result", ""))
        elif task == "generate_html":
            sections.append(state.get("html_result", ""))
        elif task == "email_report":
            sections.append(state.get("email_result", ""))

    return AIMessage(content="\n\n".join(sections).strip())
