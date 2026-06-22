"""HTML dashboard report generator for WhatsApp messaging analysis."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent.async_utils import run_in_thread
from agent.custom_tools.report_io import prepare_report_output_path

REPORTS_DIR = Path("./reports")


def _escape(text: Any) -> str:
    return html.escape(str(text or ""), quote=True)


def _pct(part: int, total: int) -> float:
    return round((part / total) * 100, 1) if total else 0.0


def _bar_row(label: str, count: int, total: int, color: str) -> str:
    pct = _pct(count, total)
    return f"""
    <div class="bar-row">
      <div class="bar-label"><span>{_escape(label)}</span><span>{count} ({pct}%)</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
    </div>"""


def _generate_llm_executive_summary(state: dict[str, Any]) -> str:
    """Generate an LLM narrative summary of the WhatsApp conversation."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _fallback_executive_summary(state)

    conversations = state.get("conversations") or []
    unread_chats = state.get(
        "unread_chats_found",
        state.get("read_chats_found", len(conversations)),
    )
    stats = {
        "chats_scanned": state.get("chats_scanned", 0),
        "unread_chats_found": unread_chats,
        "read_chats_found": unread_chats,
        "total_messages": len(state.get("chat_messages") or []),
        "positive": len(state.get("positive_messages") or []),
        "negative": len(state.get("negative_messages") or []),
        "questions": len(state.get("question_messages") or []),
        "unanswered": len(state.get("unanswered_messages") or []),
        "replies_generated": len(state.get("generated_replies") or []),
    }
    contact_filter = state.get("contact_filter") or "all unread chats"
    prompt = (
        f"Write a concise executive summary (3-5 paragraphs) for a WhatsApp inbox "
        f"reply dashboard report.\n\n"
        f"Inbox filter: {contact_filter}\n"
        f"Unread chats processed: {stats['unread_chats_found']}\n"
        f"Message stats: {json.dumps(stats)}\n\n"
        "Cover: conversation tone, engagement quality, risks, opportunities, and recommended "
        "follow-up actions. Use plain professional language."
    )
    try:
        model = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=api_key)
        response = model.invoke(
            [
                SystemMessage(
                    content="You write WhatsApp messaging analytics executive summaries."
                ),
                HumanMessage(content=prompt),
            ]
        )
        return str(response.content).strip()
    except Exception:
        return _fallback_executive_summary(state)


def _fallback_executive_summary(state: dict[str, Any]) -> str:
    """Heuristic summary when LLM is unavailable."""
    unread_chats = state.get(
        "unread_chats_found",
        state.get("read_chats_found", len(state.get("conversations") or [])),
    )
    total = len(state.get("chat_messages") or [])
    unanswered = len(state.get("unanswered_messages") or [])
    positive = len(state.get("positive_messages") or [])
    negative = len(state.get("negative_messages") or [])
    return (
        f"This report covers {unread_chats} unread WhatsApp chat(s) from your inbox. "
        f"{total} inbound messages were analyzed. Sentiment is "
        f"{'predominantly positive' if positive > negative else 'mixed' if negative else 'neutral'}. "
        f"{unanswered} messages remain unanswered and represent immediate reply opportunities."
    )


def _reply_history_rows(records: list[dict]) -> str:
    if not records:
        return "<tr><td colspan='6'>No reply history recorded</td></tr>"
    rows = []
    for record in records:
        rows.append(
            f"<tr>"
            f"<td>{_escape(record.get('recorded_at', ''))}</td>"
            f"<td>{_escape(record.get('message_author', record.get('comment_author', '')))}</td>"
            f"<td>{_escape(record.get('message_category', record.get('comment_category', '')))}</td>"
            f"<td class='comment-text'>{_escape(record.get('message_text', record.get('comment_text', '')))}</td>"
            f"<td class='reply'>{_escape(record.get('reply_text', ''))}</td>"
            f"<td>{_escape(record.get('status', ''))}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _failed_reply_rows(failed_replies: list[dict]) -> str:
    if not failed_replies:
        return "<tr><td colspan='4'>No failed reply attempts</td></tr>"
    rows = []
    for reply in failed_replies:
        rows.append(
            f"<tr>"
            f"<td>{_escape(reply.get('author', ''))}</td>"
            f"<td class='comment-text'>{_escape(reply.get('text', ''))}</td>"
            f"<td class='reply'>{_escape(reply.get('reply_text', ''))}</td>"
            f"<td class='error'>{_escape(reply.get('post_error', 'Unknown error'))}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _reply_log_rows(replies: list[dict], screenshots: list[dict]) -> str:
    if not replies and not screenshots:
        return "<tr><td colspan='4'>No replies generated</td></tr>"
    shot_by_contact = {
        str(s.get("contact_name", "")): s.get("screenshot_path", "") for s in screenshots
    }
    rows = []
    for reply in replies:
        contact = str(reply.get("contact_name") or reply.get("author") or "Contact")
        shot = reply.get("screenshot_path") or shot_by_contact.get(contact, "")
        shot_cell = (
            f'<img src="{_escape(shot)}" alt="screenshot" style="max-width:220px;border-radius:8px" />'
            if shot
            else "—"
        )
        rows.append(
            f"<tr>"
            f"<td>{_escape(contact)}</td>"
            f"<td class='comment-text'>{_escape(reply.get('text', ''))}</td>"
            f"<td class='reply'>{_escape(reply.get('reply_text', ''))}</td>"
            f"<td>{shot_cell}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _category_section(title: str, comments: list[dict], color: str) -> str:
    if not comments:
        return f"<div class='card' style='margin-bottom:16px'><h2>{_escape(title)} (0)</h2><p class='summary'>None</p></div>"
    return f"""
    <div class="card" style="margin-bottom:16px;border-left:4px solid {color}">
      <h2>{_escape(title)} ({len(comments)})</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Author</th><th>Priority</th><th>Sentiment</th><th>Likes</th><th>Time</th><th>Comment</th>
          </tr></thead>
          <tbody>{_comment_rows(comments)}</tbody>
        </table>
      </div>
    </div>"""


def _reply_target_rows(targets: list[dict]) -> str:
    if not targets:
        return "<tr><td colspan='5'>No positive reply targets selected</td></tr>"
    rows = []
    for comment in targets:
        rows.append(
            f"<tr>"
            f"<td>{comment.get('reply_rank', '')}</td>"
            f"<td>{_escape(comment.get('author', ''))}</td>"
            f"<td>{comment.get('likes', 0)}</td>"
            f"<td>{comment.get('sentiment_score', '')}</td>"
            f"<td class='comment-text'>{_escape(comment.get('text', ''))}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _comment_rows(comments: list[dict], include_reply: bool = False) -> str:
    if not comments:
        return "<tr><td colspan='7'>No data</td></tr>"
    rows = []
    for comment in comments:
        reply_cell = (
            f"<td class='reply'>{_escape(comment.get('reply_text', ''))}</td>"
            if include_reply
            else ""
        )
        rows.append(
            f"<tr>"
            f"<td>{_escape(comment.get('author', ''))}</td>"
            f"<td>{_escape(comment.get('category', comment.get('sentiment', '')))}</td>"
            f"<td>{_escape(comment.get('engagement_priority', ''))}</td>"
            f"<td>{comment.get('sentiment_score', '')}</td>"
            f"<td>{comment.get('likes', 0)}</td>"
            f"<td>{_escape(comment.get('timestamp', ''))}</td>"
            f"<td class='comment-text'>{_escape(comment.get('text', ''))}</td>"
            f"{reply_cell}"
            f"</tr>"
        )
    return "\n".join(rows)


def generate_html_dashboard_report_sync(
    state: dict[str, Any],
    output_path: str | None = None,
) -> str:
    """Build a comprehensive dashboard-style HTML report from workflow state."""
    contact_filter = str(state.get("contact_filter") or "").strip()
    channel = contact_filter or "WhatsApp Inbox"
    slug = "whatsapp_inbox"
    if contact_filter:
        slug = re.sub(r"[^a-z0-9]+", "_", contact_filter.lower()).strip("_") or slug
    output_path = str(
        prepare_report_output_path(
            output_path or REPORTS_DIR / f"{slug}_dashboard_report.html"
        )
    )

    analyzed = state.get("analyzed_messages") or state.get("chat_messages") or []
    generated = state.get("generated_replies") or []
    screenshots = state.get("screenshots") or []
    conversations = state.get("conversations") or []
    reply_targets = list(state.get("reply_targets") or [])
    if not reply_targets and analyzed:
        from agent.config import get_whatsapp_config
        from agent.custom_tools.comment_selection import select_reply_targets

        cfg = get_whatsapp_config()
        limit = cfg["max_replies_per_run"] if cfg["max_replies_per_run"] > 0 else 5
        reply_targets = select_reply_targets(
            analyzed,
            limit=limit,
            contact_name="inbox",
        )
    if not reply_targets:
        reply_targets = generated
    failed_replies = state.get("failed_replies") or [
        reply
        for reply in generated
        if not reply.get("posted") and reply.get("post_error")
    ]
    recommendations = state.get("recommendations") or []
    reply_history = state.get("reply_history") or []
    if not reply_history:
        from agent.custom_tools.reply_history import get_reply_history

        reply_history = get_reply_history(contact_name="inbox")

    total = len(analyzed)
    stats = {
        "positive": len(state.get("positive_messages") or []),
        "negative": len(state.get("negative_messages") or []),
        "neutral": len(state.get("neutral_messages") or []),
        "questions": len(state.get("question_messages") or []),
        "suggestions": len(state.get("suggestion_messages") or []),
        "spam": len(state.get("spam_messages") or []),
        "unanswered": len(state.get("unanswered_messages") or []),
    }
    reply_stats = state.get("reply_statistics") or {}
    executive_summary = state.get("llm_summary") or _generate_llm_executive_summary(
        state
    )

    if not recommendations:
        from agent.workflow_executor import _build_recommendations

        recommendations = _build_recommendations(state)

    avg_sentiment = (
        round(sum(c.get("sentiment_score", 0) for c in analyzed) / total, 2)
        if total
        else 0
    )
    high_priority = [c for c in analyzed if c.get("engagement_priority") == "high"]

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WhatsApp Messaging Dashboard — {_escape(channel)}</title>
  <style>
    :root {{
      --bg: #0f0f0f; --card: #1a1a1a; --text: #f1f1f1; --muted: #aaaaaa;
      --accent: #ff0000; --accent2: #cc0000; --border: #303030;
      --green: #2ecc71; --yellow: #f1c40f; --red: #e74c3c; --blue: #3498db; --purple: #9b59b6;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    .header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d0a0a 100%); border: 1px solid var(--border);
      border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
    .header h1 {{ margin: 0 0 8px; font-size: 1.8rem; }}
    .header .sub {{ color: var(--muted); }}
    .grid {{ display: grid; gap: 16px; }}
    .grid-4 {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .grid-2 {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }}
    .card h2 {{ margin: 0 0 14px; font-size: 1.1rem; color: #fff; border-bottom: 2px solid var(--accent); padding-bottom: 8px; }}
    .metric {{ text-align: center; }}
    .metric .val {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
    .metric .lbl {{ color: var(--muted); font-size: 0.85rem; margin-top: 4px; }}
    .video-hero {{ display: grid; grid-template-columns: 220px 1fr; gap: 20px; align-items: start; }}
    .thumb {{ width: 100%; border-radius: 10px; aspect-ratio: 16/9; object-fit: cover; background: #222; }}
    .thumb.placeholder {{ display:flex; align-items:center; justify-content:center; min-height:120px; color:var(--muted); }}
    .meta dt {{ color: var(--muted); font-size: 0.8rem; margin-top: 10px; }}
    .meta dd {{ margin: 4px 0 0; font-weight: 600; }}
    .desc {{ color: #ccc; line-height: 1.5; white-space: pre-wrap; max-height: 160px; overflow: auto; }}
    .bar-row {{ margin-bottom: 12px; }}
    .bar-label {{ display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px; }}
    .bar-track {{ height: 10px; background: #2a2a2a; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 999px; }}
    .summary {{ line-height: 1.7; color: #ddd; white-space: pre-wrap; }}
    ul.recs {{ margin: 0; padding-left: 20px; line-height: 1.8; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; position: sticky; top: 0; background: var(--card); }}
    .comment-text {{ max-width: 320px; }}
    .reply {{ max-width: 260px; color: #9fe870; }}
    .error {{ max-width: 260px; color: var(--red); }}
    .table-wrap {{ max-height: 420px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; }}
    .footer {{ text-align: center; color: var(--muted); font-size: 0.8rem; margin-top: 28px; }}
    a {{ color: #3ea6ff; }}
    @media (max-width: 700px) {{ .video-hero {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>WhatsApp Messaging Dashboard</h1>
      <div class="sub">{_escape(channel)} · Generated {_escape(generated_at)}</div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Inbox Overview</h2>
      <dl class="meta">
        <dt>Scope</dt><dd>{_escape(channel)}</dd>
        <dt>Inbound messages</dt><dd>{len(state.get("chat_messages") or [])}</dd>
        <dt>Unread chats processed</dt><dd>{state.get("unread_chats_found", state.get("read_chats_found", len(conversations)))}</dd>
        <dt>Chats scanned</dt><dd>{state.get("chats_scanned", "—")}</dd>
        <dt>Filter mode</dt><dd>Unread chats only</dd>
      </dl>
    </div>

    <div class="grid grid-4" style="margin-bottom:24px">
      <div class="card metric"><div class="val">{total}</div><div class="lbl">Messages Analyzed</div></div>
      <div class="card metric"><div class="val">{len(reply_targets)}</div><div class="lbl">Reply Targets</div></div>
      <div class="card metric"><div class="val">{reply_stats.get("replies_generated", len(generated))}</div><div class="lbl">Replies Generated</div></div>
      <div class="card metric"><div class="val">{reply_stats.get("replies_posted", 0)}</div><div class="lbl">Replies Sent</div></div>
      <div class="card metric"><div class="val">{reply_stats.get("replies_failed", len(failed_replies))}</div><div class="lbl">Replies Failed</div></div>
      <div class="card metric"><div class="val">{avg_sentiment}</div><div class="lbl">Avg Sentiment Score</div></div>
      <div class="card metric"><div class="val">{len(high_priority)}</div><div class="lbl">High Priority</div></div>
      <div class="card metric"><div class="val">{_pct(stats["positive"], total)}%</div><div class="lbl">Positive</div></div>
      <div class="card metric"><div class="val">{_pct(stats["negative"], total)}%</div><div class="lbl">Negative</div></div>
    </div>

    <div class="grid grid-2" style="margin-bottom:24px">
      <div class="card">
        <h2>Message Categories</h2>
        {_bar_row("Positive", stats["positive"], total, "var(--green)")}
        {_bar_row("Negative", stats["negative"], total, "var(--red)")}
        {_bar_row("Neutral", stats["neutral"], total, "#95a5a6")}
        {_bar_row("Questions", stats["questions"], total, "var(--blue)")}
        {_bar_row("Suggestions", stats["suggestions"], total, "var(--purple)")}
        {_bar_row("Spam", stats["spam"], total, "#7f8c8d")}
      </div>
      <div class="card">
        <h2>Executive Summary (LLM)</h2>
        <div class="summary">{_escape(executive_summary)}</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Recommended Actions</h2>
      <ul class="recs">{"".join(f"<li>{_escape(r)}</li>" for r in recommendations)}</ul>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Reply History — What We Replied To</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>When</th><th>Author</th><th>Category</th><th>Original Message</th><th>Our Reply</th><th>Status</th>
          </tr></thead>
          <tbody>{_reply_history_rows(reply_history)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Failed Reply Attempts ({len(failed_replies)})</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Author</th><th>Original Message</th><th>Attempted Reply</th><th>Error</th>
          </tr></thead>
          <tbody>{_failed_reply_rows(failed_replies)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Messages by Category</h2>
      {_category_section("Positive Messages", state.get("positive_messages") or [], "var(--green)")}
      {_category_section("Negative Messages", state.get("negative_messages") or [], "var(--red)")}
      {_category_section("Neutral Messages", state.get("neutral_messages") or [], "#95a5a6")}
      {_category_section("Questions", state.get("question_messages") or [], "var(--blue)")}
      {_category_section("Suggestions", state.get("suggestion_messages") or [], "var(--purple)")}
      {_category_section("Spam", state.get("spam_messages") or [], "#7f8c8d")}
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>All Analyzed Messages ({total})</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Author</th><th>Category</th><th>Priority</th><th>Sentiment</th>
            <th>Likes</th><th>Time</th><th>Comment</th>
          </tr></thead>
          <tbody>{_comment_rows(analyzed)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Top Reply Targets ({len(reply_targets)})</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Rank</th><th>Author</th><th>Likes</th><th>Sentiment</th><th>Comment</th>
          </tr></thead>
          <tbody>{_reply_target_rows(reply_targets)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Message & Reply Log</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Contact</th><th>Received Message</th><th>AI Reply Sent</th><th>Screenshot</th>
          </tr></thead>
          <tbody>{_reply_log_rows(generated, screenshots)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:24px">
      <h2>Generated AI Replies ({len(generated)})</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Author</th><th>Category</th><th>Priority</th><th>Sentiment</th>
            <th>Time</th><th>Original Message</th><th>AI Reply</th>
          </tr></thead>
          <tbody>{_comment_rows(generated, include_reply=True)}</tbody>
        </table>
      </div>
    </div>

    <div class="footer">Generated by WhatsApp Messaging Agent</div>
  </div>
</body>
</html>"""

    Path(output_path).write_text(html_doc, encoding="utf-8")
    size = Path(output_path).stat().st_size
    return f"HTML dashboard report generated: {output_path} ({size} bytes)"


@tool
async def generate_html_report(state_json: str = "") -> str:
    """Generate a comprehensive HTML dashboard report for WhatsApp messaging analysis.

    Pass workflow state as a JSON string, or leave empty to use latest ./reports data.
    """
    state: dict[str, Any] = {}
    if state_json.strip():
        state = json.loads(state_json)
    return await run_in_thread(generate_html_dashboard_report_sync, state)


__all__ = ["generate_html_dashboard_report_sync", "generate_html_report"]
