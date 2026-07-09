"""WhatsApp Web inbox scanning, conversation reading, and message sending."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

_browsers_cache = Path.home() / ".cache" / "ms-playwright"
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and _browsers_cache.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_browsers_cache)

from agent.config import get_whatsapp_config
from agent.custom_tools.browser_tools import (
    WHATSAPP_WEB_URL,
    close_browser_session,
    launch_whatsapp_browser_from_session,
    navigate_to_contact,
    open_whatsapp_web,
    wait_for_whatsapp_login,
)

_BROWSER_SESSION: dict[str, Any] = {}
SCREENSHOTS_DIR = Path("./reports/screenshots")

COMPOSE_INPUT_SELECTORS = (
    'div[data-testid="conversation-compose-box-input"]',
    'footer div[contenteditable="true"][data-tab="10"]',
    'footer div[contenteditable="true"]',
    '#main footer div[contenteditable="true"]',
    # Some WhatsApp Web builds use a plain input in the compose footer
    'footer input[type="text"]',
)

SEND_BUTTON_SELECTORS = (
    'button[aria-label="Send"][data-tab="11"]',
    'button[data-testid="compose-btn-send"]',
    'span[data-testid="wds-ic-send-filled"]',
    'button[aria-label="Send"]',
)

SCAN_CHAT_LIST_SCRIPT = """
() => {
  const list = document.querySelector('[data-testid="chat-list"]');
  if (!list) return [];
  const cells = list.querySelectorAll('[data-testid="cell-frame-container"]');
  const results = [];
  cells.forEach((cell, index) => {
    const titleEl = cell.querySelector('[data-testid="cell-frame-title"] span[title]')
      || cell.querySelector('[data-testid="cell-frame-title"] span');
    const title = (titleEl?.getAttribute('title') || titleEl?.innerText || '').trim();
    const previewEl = cell.querySelector('[data-testid="cell-frame-secondary"] span')
      || cell.querySelector('[data-testid="cell-frame-secondary"]');
    const preview = (previewEl?.innerText || '').trim();
    const timeEl = cell.querySelector('[data-testid="cell-frame-primary-detail"] span');
    const last_seen = (timeEl?.innerText || '').trim();
    const unreadBadge = cell.querySelector(
      '[data-testid="icon-unread-count"], [aria-label*="unread"], span[data-icon="unread-count"], span[data-icon="unread"]'
    );
    const unreadCountText = (cell.querySelector('[data-testid="icon-unread-count"]')?.innerText || '').trim();
    const unread_count = unreadCountText ? parseInt(unreadCountText, 10) || 1 : (unreadBadge ? 1 : 0);
    const is_unread = unread_count > 0 || !!unreadBadge;
    if (!title) return;
    results.push({ index, title, preview, last_seen, is_unread });
  });
  return results;
}
"""

# ---------------------------------------------------------------------------
# Conversation scraping
# ---------------------------------------------------------------------------
# Strategy: read data-pre-plain-text="[HH:MM, DD/MM/YYYY] Sender:" attributes
# on .copyable-text wrappers. When the sender name IS the local user we mark
# the message as outgoing; when it is the remote contact it is inbound.
# Outgoing bubble containers carry class "message-out" OR are inside a row
# that has data-testid containing "msg" with a tail-out SVG — we detect both.

SCRAPE_CONVERSATION_SCRIPT = """
() => {
  // Collect all copyable-text wrappers that carry the metadata attribute.
  const wrappers = document.querySelectorAll('.copyable-text[data-pre-plain-text]');
  const results = [];

  // Build a small helper to pull visible text from a wrapper.
  function extractText(el) {
    const parts = [];
    el.querySelectorAll(
      'span[data-testid="selectable-text"] span, span.selectable-text span, p.selectable-text'
    ).forEach(s => {
      const t = (s.innerText || '').trim();
      if (t) parts.push(t);
    });
    if (!parts.length) {
      // Fallback: grab first selectable-text span
      const fb = el.querySelector('span[data-testid="selectable-text"], span.selectable-text');
      if (fb) parts.push((fb.innerText || '').trim());
    }
    return parts.join('\\n').trim();
  }

  wrappers.forEach((wrapper, idx) => {
    const meta = wrapper.getAttribute('data-pre-plain-text') || '';
    // meta looks like: "[7:19 PM, 6/21/2026] Asim Bhai: "
    const metaMatch = meta.match(/^\\[([^\\]]+)\\]\\s+(.+?):\\s*$/);
    const timestamp = metaMatch ? metaMatch[1].trim() : '';
    const senderName = metaMatch ? metaMatch[2].trim() : '';

    const text = extractText(wrapper);
    if (!text) return;

    // Detect outgoing: bubble has message-out class, or ancestor row has it,
    // or a tail-out SVG exists inside the same message bubble.
    const bubble = wrapper.closest('[data-testid="msg-container"]') || wrapper.parentElement;
    let isOutgoing = false;
    if (bubble) {
      isOutgoing = bubble.classList.contains('message-out')
        || !!bubble.closest('.message-out')
        || !!bubble.querySelector('[data-testid="tail-out"], [data-icon="tail-out"]');
    }

    const dataId = (bubble && bubble.getAttribute('data-id')) || `msg_${idx}`;

    results.push({
      message_id: dataId,
      text,
      timestamp,
      sender_name: senderName,
      is_outgoing: isOutgoing,
    });
  });

  return results;
}
"""


def _store_browser_session(
    playwright: Playwright,
    browser: Browser | None,
    context: BrowserContext,
    page: Page,
) -> None:
    _BROWSER_SESSION.clear()
    _BROWSER_SESSION.update(
        {
            "playwright": playwright,
            "browser": browser,
            "context": context,
            "page": page,
            "keep_alive": True,
        }
    )


def _get_stored_page() -> Page | None:
    page = _BROWSER_SESSION.get("page")
    if page is None:
        return None
    try:
        if page.is_closed():
            _BROWSER_SESSION.clear()
            return None
    except Exception:
        _BROWSER_SESSION.clear()
        return None
    return page


def _close_browser_session(
    playwright: Playwright | None,
    browser: Browser | None,
    context: BrowserContext | None,
    *,
    force: bool = False,
) -> None:
    """Close Playwright resources unless the login step marked the session keep-alive."""
    if _BROWSER_SESSION.get("keep_alive") and not force:
        return
    close_browser_session(playwright, browser, context)


def release_browser_session() -> None:
    """Close the shared browser session at the end of the workflow."""
    playwright = _BROWSER_SESSION.get("playwright")
    browser = _BROWSER_SESSION.get("browser")
    context = _BROWSER_SESSION.get("context")
    _BROWSER_SESSION["keep_alive"] = False
    close_browser_session(playwright, browser, context)
    _BROWSER_SESSION.clear()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "contact"


def scan_chat_list(page: Page) -> list[dict[str, Any]]:
    """Read visible chats from the WhatsApp sidebar."""
    if WHATSAPP_WEB_URL not in page.url or not _is_whatsapp_ready(page):
        page.goto(WHATSAPP_WEB_URL, wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="chat-list"]', timeout=60000)
    page.wait_for_timeout(1500)
    raw = page.evaluate(SCAN_CHAT_LIST_SCRIPT)
    return list(raw or [])


def _is_whatsapp_ready(page: Page) -> bool:
    try:
        return page.locator('[data-testid="chat-list"]').first.is_visible(timeout=1500)
    except Exception:
        return False


def filter_inbox_chats(
    chats: list[dict[str, Any]],
    *,
    only_unread: bool = True,
    contact_filter: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Keep chats eligible for auto-reply (unread chats only by default)."""
    eligible: list[dict[str, Any]] = []
    contact_filter = contact_filter.strip().lower()
    for chat in chats:
        if only_unread and not chat.get("is_unread"):
            continue
        title = str(chat.get("title") or "")
        if contact_filter and contact_filter not in title.lower():
            continue
        if not str(chat.get("preview") or "").strip() and not title:
            continue
        eligible.append(chat)
        if limit > 0 and len(eligible) >= limit:
            break
    return eligible


def filter_read_chats(
    chats: list[dict[str, Any]],
    *,
    only_read: bool = True,
    contact_filter: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Backward-compatible alias — prefer filter_inbox_chats."""
    only_unread = not only_read
    return filter_inbox_chats(
        chats,
        only_unread=only_unread,
        contact_filter=contact_filter,
        limit=limit,
    )


def open_chat_from_list(page: Page, chat: dict[str, Any]) -> None:
    """Click a chat row in the sidebar by index."""
    index = int(chat.get("index", 0))
    rows = page.locator('[data-testid="cell-frame-container"]')
    rows.nth(index).click()
    page.wait_for_timeout(2000)
    page.wait_for_selector(
        'div[data-testid="conversation-panel-body"], #main',
        timeout=15000,
    )


def scrape_conversation(page: Page, contact_name: str) -> list[dict[str, Any]]:
    """Extract messages from the open chat using WhatsApp Web DOM."""
    raw_messages = page.evaluate(SCRAPE_CONVERSATION_SCRIPT)
    messages: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_messages or []):
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        is_outgoing = bool(raw.get("is_outgoing"))
        # Prefer sender_name from metadata; fall back to contact_name for inbound
        sender_name = str(raw.get("sender_name") or "").strip()
        author: str
        if is_outgoing:
            author = "Me"
        else:
            author = sender_name or contact_name
        messages.append(
            {
                "message_id": str(raw.get("message_id") or f"msg_{index}"),
                "contact_name": contact_name,
                "author": author,
                "text": text,
                "timestamp": str(raw.get("timestamp") or ""),
                "is_outgoing": is_outgoing,
                "agent_replied": is_outgoing,
                "posted": is_outgoing,
            }
        )
    return messages


def _latest_inbound_needing_reply(
    messages: list[dict[str, Any]],
    messages_per_chat: int,
) -> list[dict[str, Any]]:
    """Return the latest inbound message(s) that need a reply."""
    inbound = [m for m in messages if not m.get("is_outgoing")]
    if not inbound:
        return []
    if messages_per_chat <= 1:
        return [inbound[-1]]
    if messages_per_chat > 0:
        inbound = inbound[-messages_per_chat:]
    return inbound


def _resolve_whatsapp_page() -> tuple[Playwright | None, Browser | None, BrowserContext | None, Page, bool]:
    """Reuse stored browser from login step, or reconnect and open WhatsApp only."""
    page = _get_stored_page()
    if page is not None:
        try:
            whatsapp_ok = wait_for_whatsapp_login(page, block_for_qr=True)
        except TimeoutError:
            whatsapp_ok = False
        return None, None, None, page, whatsapp_ok

    from agent.custom_tools.browser_tools import ensure_whatsapp_browser_session

    playwright, browser, context, page, whatsapp_ok = ensure_whatsapp_browser_session()
    _store_browser_session(playwright, browser, context, page)
    return playwright, browser, context, page, whatsapp_ok


def _fetch_named_contact_conversation(
    page: Page,
    contact_name: str,
    max_messages: int,
) -> dict[str, Any] | None:
    """Navigate directly to a named contact chat and scrape its conversation.

    Returns a conversation dict with ``is_greeting=True`` attached to each
    message so downstream generators know to write an opener rather than a
    plain reply-to-unread. If the chat has no visible messages yet, a
    synthetic opener anchor is created so the agent can send the first
    WhatsApp message to the configured contact. Returns None if navigation
    fails or if the last message is outgoing.
    """
    try:
        navigate_to_contact(page, contact_name)
        messages = scrape_conversation(page, contact_name)
        if max_messages > 0:
            messages = messages[-max_messages:]
        if not messages:
            greeting_msg = {
                "message_id": f"initial_{_slugify(contact_name)}",
                "contact_name": contact_name,
                "author": contact_name,
                "text": "Start a new WhatsApp conversation.",
                "timestamp": "",
                "is_outgoing": False,
                "agent_replied": False,
                "posted": False,
                "conversation_history": [],
                "is_greeting": True,
                "is_initial_message": True,
            }
            return {
                "contact_name": contact_name,
                "is_unread": False,
                "is_greeting": True,
                "messages": [],
                "inbound_messages": [greeting_msg],
            }

        # Check if the last message in the chat is outgoing.
        # If so, we have already replied, so we do not send a greeting.
        if messages[-1].get("is_outgoing"):
            return None

        # Since the last message is inbound, pick it as the greeting anchor.
        last_inbound = messages[-1]

        # Clone and mark as greeting so the LLM uses the right persona.
        greeting_msg = {
            **last_inbound,
            "contact_name": contact_name,
            "conversation_history": messages,
            "is_greeting": True,
            "is_initial_message": False,
            "agent_replied": False,
            "posted": False,
        }
        return {
            "contact_name": contact_name,
            "is_unread": False,
            "is_greeting": True,
            "messages": messages,
            "inbound_messages": [greeting_msg],
        }
    except Exception:
        return None


def fetch_read_conversations(
    contact_filter: str = "",
) -> dict[str, Any]:
    """Scan inbox for unread chats, open each, and extract conversation messages.

    When *contact_filter* names a specific contact the agent will:
    1. Navigate directly to that contact (regardless of read/unread status)
       and build a greeting message from the last conversation exchange.
    2. Also scan the full inbox for any *other* unread chats to reply to.
    """
    config = get_whatsapp_config()
    active_filter = (contact_filter or config.get("contact_filter", "")).strip()
    playwright = browser = context = None
    owns_session = False
    try:
        playwright, browser, context, page, whatsapp_ok = _resolve_whatsapp_page()
        owns_session = playwright is not None
        if not whatsapp_ok:
            return {
                "success": False,
                "error": (
                    "WhatsApp Web is not logged in. Set BROWSER_HEADLESS=false, "
                    "scan the QR code in the browser, then re-run."
                ),
            }

        conversations: list[dict[str, Any]] = []
        flat_messages: list[dict[str, Any]] = []
        greeting_injected = False

        # ── Step 1: If a contact is named, open their chat and build a greeting ──
        if active_filter:
            greeting_conv = _fetch_named_contact_conversation(
                page,
                active_filter,
                max(1, config["max_messages_per_chat"]),
            )
            if greeting_conv:
                conversations.append(greeting_conv)
                for msg in greeting_conv["inbound_messages"]:
                    flat_messages.append(msg)
                greeting_injected = True

        # ── Step 2: Scan inbox for eligible chats (all contacts) ──
        all_chats = scan_chat_list(page)
        only_unread = bool(config.get("reply_only_unread_chats", True))
        eligible_chats = filter_inbox_chats(
            all_chats,
            only_unread=only_unread,
            contact_filter="",
            limit=config["max_chats_to_process"],
        )

        for chat in eligible_chats:
            title = str(chat.get("title") or "Contact")
            # Skip if this chat IS the named contact (already handled above).
            # If direct-contact mode produced no target because our last
            # message is already outgoing, avoid re-processing it as a read chat.
            if active_filter and active_filter.lower() in title.lower():
                continue
            try:
                open_chat_from_list(page, chat)
                messages = scrape_conversation(page, title)
                inbound = _latest_inbound_needing_reply(
                    messages, max(1, config["max_messages_per_chat"])
                )
                # Attach full conversation history for LLM context
                for msg in inbound:
                    msg["conversation_history"] = messages
                conversations.append(
                    {
                        "contact_name": title,
                        "preview": chat.get("preview", ""),
                        "last_seen": chat.get("last_seen", ""),
                        "is_unread": chat.get("is_unread", False),
                        "messages": messages,
                        "inbound_messages": inbound,
                    }
                )
                flat_messages.extend(inbound)
            except Exception as exc:
                conversations.append(
                    {
                        "contact_name": title,
                        "preview": chat.get("preview", ""),
                        "error": str(exc),
                        "messages": [],
                        "inbound_messages": [],
                    }
                )

        if config["keep_browser_open"] and owns_session and playwright and browser and context:
            _store_browser_session(playwright, browser, context, page)

        unread_found = sum(1 for chat in all_chats if chat.get("is_unread"))
        read_found = sum(1 for chat in all_chats if not chat.get("is_unread"))
        return {
            "success": True,
            "whatsapp_logged_in": True,
            "chats_scanned": len(all_chats),
            "unread_chats_found": unread_found,
            "read_chats_found": read_found,
            "eligible_chats_found": len(eligible_chats),
            "greeting_injected": greeting_injected,
            "greeting_contact": active_filter if greeting_injected else "",
            "conversations": conversations,
            "chat_messages": flat_messages,
            "inbound_messages_count": len(flat_messages),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _type_in_compose_box(page: Page, text: str) -> None:
    compose = None
    for selector in COMPOSE_INPUT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=3000):
                compose = locator
                break
        except Exception:
            continue
    if compose is None:
        raise RuntimeError("Could not find WhatsApp compose input.")

    compose.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(text, delay=20)
    page.wait_for_timeout(300)


def _click_send(page: Page) -> None:
    for selector in SEND_BUTTON_SELECTORS:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=2000):
                locator.click()
                page.wait_for_timeout(1200)
                return
        except Exception:
            continue
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)


def _screenshot_chat(page: Page, contact_name: str) -> str:
    """Capture screenshot after sending a message."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOTS_DIR / f"{_slugify(contact_name)}_{stamp}.png"
    page.screenshot(path=str(path), full_page=False)
    return str(path)


def send_whatsapp_message(page: Page, text: str) -> bool:
    """Type and send a message in the open chat."""
    if not text.strip():
        return False
    _type_in_compose_box(page, text.strip())
    _click_send(page)
    return True


def send_replies_to_messages(
    replies: list[dict[str, Any]],
    enabled: bool = True,
) -> dict[str, Any]:
    """Open each contact chat, send reply, and capture a screenshot."""
    if not enabled or not replies:
        return {"posted": 0, "failed": 0, "replies": replies or [], "screenshots": []}

    page = _get_stored_page()
    playwright = browser = context = None
    own_session = False

    if page is None:
        own_session = True
        try:
            playwright, browser, context, page, logged_in = _resolve_whatsapp_page()
        except RuntimeError as exc:
            return {
                "posted": 0,
                "failed": len(replies),
                "replies": replies,
                "screenshots": [],
                "error": str(exc),
            }
        if not logged_in:
            return {
                "posted": 0,
                "failed": len(replies),
                "replies": replies,
                "screenshots": [],
                "error": "WhatsApp session not available.",
            }

    posted = 0
    failed = 0
    updated: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []

    for reply in replies:
        item = dict(reply)
        contact = str(item.get("contact_name") or "Contact")
        text = str(item.get("reply_text") or "").strip()
        try:
            navigate_to_contact(page, contact)
            page.wait_for_timeout(1500)
            if send_whatsapp_message(page, text):
                shot_path = _screenshot_chat(page, contact)
                item["posted"] = True
                item["agent_replied"] = True
                item["screenshot_path"] = shot_path
                screenshots.append(
                    {
                        "contact_name": contact,
                        "screenshot_path": shot_path,
                        "reply_text": text,
                        "original_message": item.get("text", ""),
                    }
                )
                posted += 1
            else:
                item["posted"] = False
                item["post_error"] = "Empty reply text"
                failed += 1
        except Exception as exc:
            item["posted"] = False
            item["post_error"] = str(exc)
            failed += 1
        updated.append(item)

    config = get_whatsapp_config()
    if own_session and not config["keep_browser_open"]:
        _close_browser_session(
            playwright or _BROWSER_SESSION.get("playwright"),
            browser or _BROWSER_SESSION.get("browser"),
            context or _BROWSER_SESSION.get("context"),
            force=True,
        )
        _BROWSER_SESSION.clear()
    elif _BROWSER_SESSION.get("page") is page:
        _store_browser_session(
            _BROWSER_SESSION.get("playwright"),
            _BROWSER_SESSION.get("browser"),
            _BROWSER_SESSION.get("context"),
            page,
        )

    return {
        "posted": posted,
        "failed": failed,
        "replies": updated,
        "failed_replies": [r for r in updated if not r.get("posted")],
        "screenshots": screenshots,
    }


# Backward-compatible alias used by older imports/tests
def fetch_chat_messages(contact_name: str = "", phone_number: str = "") -> dict[str, Any]:
    """Fetch messages — uses inbox scan or optional single-contact filter."""
    contact_filter = contact_name or phone_number
    return fetch_read_conversations(contact_filter=contact_filter)


__all__ = [
    "fetch_read_conversations",
    "fetch_chat_messages",
    "scan_chat_list",
    "filter_read_chats",
    "scrape_conversation",
    "send_replies_to_messages",
    "send_whatsapp_message",
    "release_browser_session",
    "SCREENSHOTS_DIR",
    "_fetch_named_contact_conversation",
]
