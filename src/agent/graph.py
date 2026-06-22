"""WhatsApp Messaging Agent - LangGraph workflow."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import NotRequired, TypedDict

from agent.async_utils import run_in_thread, run_playwright
from agent.config import apply_runtime_overrides, get_whatsapp_config
from agent.custom_tools.email_tools import send_email
from agent.custom_tools.html_report_generator import (
    generate_html_report as generate_html_report_tool,
)
from agent.custom_tools.pdf_generator import generate_pdf_report, generate_table_report
from agent.routing import (
    build_analysis_summary,
    extract_contact_name,
    extract_phone_number,
    get_latest_user_text,
    is_empty_ai_message,
    wants_email_report,
    wants_pdf_report,
    wants_whatsapp_messaging,
)
from agent.task_planner import is_whatsapp_workflow_request, plan_tasks
from agent.workflow_executor import (
    execute_analyze_messages,
    execute_email_report,
    execute_fetch_chat_messages,
    execute_generate_html_report,
    execute_generate_pdf_report,
    execute_generate_replies,
    execute_select_reply_targets,
    execute_send_replies,
    execute_task_plan,
    execute_whatsapp_login,
)

load_dotenv()

SYSTEM_PROMPT = (
    "You are the WhatsApp Messaging Agent. "
    "You scan the WhatsApp Web inbox for unread conversations, extract messages, "
    "generate contextual AI replies, send them in the browser, capture screenshots, "
    "and email HTML reports."
)

GRAPH_RUN_CONFIG = {"recursion_limit": 100}

AgentRoute = Literal[
    "whatsapp_workflow",
    "execute_workflow",
    "call_model",
]


class State(TypedDict):
    """State for the WhatsApp Messaging Agent graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_input: NotRequired[str]
    workflow_action: NotRequired[str]
    contact_filter: NotRequired[str]
    conversations: NotRequired[list[dict]]
    screenshots: NotRequired[list[dict]]
    chats_scanned: NotRequired[int]
    read_chats_found: NotRequired[int]
    unread_chats_found: NotRequired[int]
    gmail_logged_in: NotRequired[bool]
    whatsapp_logged_in: NotRequired[bool]
    login_detail: NotRequired[str]
    max_chats_to_process: NotRequired[int]
    max_messages_per_chat: NotRequired[int]
    reply_only_unread_chats: NotRequired[bool]
    chat_messages: NotRequired[list[dict]]
    analyzed_messages: NotRequired[list[dict]]
    positive_messages: NotRequired[list[dict]]
    negative_messages: NotRequired[list[dict]]
    neutral_messages: NotRequired[list[dict]]
    question_messages: NotRequired[list[dict]]
    suggestion_messages: NotRequired[list[dict]]
    spam_messages: NotRequired[list[dict]]
    unanswered_messages: NotRequired[list[dict]]
    reply_targets: NotRequired[list[dict]]
    generated_replies: NotRequired[list[dict]]
    failed_replies: NotRequired[list[dict]]
    reply_history: NotRequired[list[dict]]
    reply_statistics: NotRequired[dict]
    pdf_path: NotRequired[str]
    html_path: NotRequired[str]
    llm_summary: NotRequired[str]
    task_plan_summary: NotRequired[str]
    agent_route: NotRequired[AgentRoute]
    max_replies_per_run: NotRequired[int]
    max_messages_to_fetch: NotRequired[int]
    email_recipient: NotRequired[str]
    reply_personality: NotRequired[str]
    enable_message_replies: NotRequired[bool]
    keep_browser_open: NotRequired[bool]
    reply_to_positive: NotRequired[bool]
    reply_to_negative: NotRequired[bool]
    reply_to_neutral: NotRequired[bool]
    reply_to_questions: NotRequired[bool]
    reply_to_suggestions: NotRequired[bool]
    reply_to_spam: NotRequired[bool]
    email_reports: NotRequired[bool]
    logged_in: NotRequired[bool]
    whatsapp_login_detail: NotRequired[str]
    inbound_messages_count: NotRequired[int]
    greeting_injected: NotRequired[bool]
    greeting_contact: NotRequired[str]


_model_instance = None


def _init_model():
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    _model_instance = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=api_key,
    )
    return _model_instance


def get_model():
    return _init_model()


llm_tools = [
    generate_pdf_report,
    generate_table_report,
    generate_html_report_tool,
    send_email,
]

tool_node = ToolNode(llm_tools)


def _is_fresh_user_turn(messages: list[AnyMessage]) -> bool:
    if not messages:
        return False
    last_message = messages[-1]
    return (
        isinstance(last_message, HumanMessage)
        or getattr(last_message, "type", None) == "human"
    )


def _default_workflow_prompt(contact_filter: str = "") -> str:
    """Build the default inbox-reply prompt."""
    if contact_filter:
        return f"Scan WhatsApp inbox and reply to unread messages from {contact_filter}"
    return "Scan WhatsApp inbox and reply to unread conversations"


def _prepare_messages(state: State) -> tuple[list[AnyMessage], list[AnyMessage]]:
    """Build conversation messages and any new messages to append to state."""
    existing_messages = list(state.get("messages") or [])
    state_updates: list[AnyMessage] = []

    if existing_messages:
        return existing_messages, state_updates

    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        contact_filter = str(
            state.get("contact_filter")
            or state.get("whatsapp_contact_name")
            or get_whatsapp_config().get("contact_filter", "")
        ).strip()
        if state.get("workflow_action") or not user_input:
            user_input = _default_workflow_prompt(contact_filter)

    human_message = HumanMessage(content=user_input)
    state_updates.append(human_message)
    return [human_message], state_updates


def _state_as_dict(state: State) -> dict[str, Any]:
    return dict(state)


def _pick_route(state: State, messages: list[AnyMessage], user_text: str) -> AgentRoute:
    """Decide which graph branch should handle the request."""
    if not _is_fresh_user_turn(messages) and not state.get("workflow_action"):
        return "call_model"

    workflow_action = state.get("workflow_action", "")
    if workflow_action:
        return "whatsapp_workflow"

    if wants_whatsapp_messaging(user_text):
        return "whatsapp_workflow"

    text_name = extract_contact_name(user_text)
    if is_whatsapp_workflow_request(user_text, text_name):
        return "execute_workflow"

    return "call_model"


async def prepare_input(state: State) -> dict[str, Any]:
    """Normalize input and bootstrap inbox workflow runs."""
    apply_runtime_overrides(dict(state))
    updates: dict[str, Any] = {}

    contact_filter = str(
        state.get("contact_filter")
        or state.get("whatsapp_contact_name")
        or get_whatsapp_config().get("contact_filter", "")
    ).strip()
    if contact_filter:
        updates["contact_filter"] = contact_filter

    merged: dict[str, Any] = {**state, **updates}
    user_input = (state.get("user_input") or "").strip()
    has_messages = bool(state.get("messages"))

    if not state.get("workflow_action") and not has_messages and not user_input:
        updates["workflow_action"] = "analyze"
        merged["workflow_action"] = "analyze"

    _, state_updates = _prepare_messages(merged)  # type: ignore[arg-type]
    if state_updates:
        updates["messages"] = state_updates

    return updates


async def decision_agent(state: State) -> dict[str, Any]:
    """Analyze the user query and choose the execution path."""
    messages, _ = _prepare_messages(state)
    user_text = get_latest_user_text(messages)
    contact_filter = state.get("contact_filter", "")
    task_plan = plan_tasks(user_text, contact_filter, state.get("workflow_action", ""))
    route = _pick_route(state, messages, user_text)

    summary = (
        task_plan.summary() if task_plan.is_whatsapp_workflow else "General conversation"
    )
    return {
        "task_plan_summary": summary,
        "agent_route": route,
    }


async def execute_workflow(state: State) -> dict[str, Any]:
    """Run full WhatsApp workflow from task plan."""
    messages, _ = _prepare_messages(state)
    user_text = get_latest_user_text(messages)
    task_plan = plan_tasks(
        user_text,
        state.get("contact_filter", ""),
        state.get("workflow_action", ""),
    )
    collected = await run_in_thread(
        _run_workflow_and_collect, task_plan, _state_as_dict(state)
    )
    response = await run_in_thread(execute_task_plan, task_plan, _state_as_dict(state))
    return {**collected, "messages": [response]}


def _run_workflow_and_collect(plan, initial_state: dict) -> dict:
    """Run workflow steps and return accumulated state updates."""
    state = dict(initial_state)
    handlers = [
        execute_whatsapp_login,
        execute_fetch_chat_messages,
        execute_analyze_messages,
        execute_select_reply_targets,
        execute_generate_replies,
        execute_send_replies,
        execute_generate_pdf_report,
        execute_generate_html_report,
        execute_email_report,
    ]
    task_map = {
        "login": 0,
        "fetch_messages": 1,
        "analyze": 2,
        "select_reply_targets": 3,
        "generate_replies": 4,
        "send_replies": 5,
        "generate_pdf": 6,
        "generate_html": 7,
        "email_report": 8,
    }
    for task in plan.tasks:
        idx = task_map.get(task)
        if idx is None or idx >= len(handlers):
            continue
        updates = handlers[idx](state)
        if updates.get("error"):
            break
        state.update(updates)
    return state


async def login_whatsapp(state: State) -> dict[str, Any]:
    """Open WhatsApp Web in a persistent Chrome profile."""
    updates = await run_playwright(execute_whatsapp_login, _state_as_dict(state))
    ok = updates.get("whatsapp_logged_in", updates.get("logged_in", False))
    content = (
        updates.get("login_detail") or "WhatsApp Web session ready."
        if ok
        else updates.get("error", "WhatsApp Web login failed.")
    )
    return {**updates, "messages": [AIMessage(content=content)]}


async def scan_read_conversations(state: State) -> dict[str, Any]:
    """Scan inbox for unread chats and extract conversations."""
    updates = await run_playwright(execute_fetch_chat_messages, _state_as_dict(state))
    if updates.get("error"):
        return {
            "messages": [
                AIMessage(content=f"Failed to read conversations: {updates['error']}")
            ]
        }
    count = len(updates.get("chat_messages") or [])
    unread = updates.get("unread_chats_found", updates.get("read_chats_found", 0))
    scanned = updates.get("chats_scanned", 0)
    greeting_contact = updates.get("greeting_contact", "")
    parts: list[str] = []
    if greeting_contact:
        parts.append(
            f"Greeting prepared for {greeting_contact} based on conversation history."
        )
    parts.append(
        f"Scanned {scanned} chats in inbox, found {unread} unread conversation(s), "
        f"extracted {count} message(s) to process."
    )
    msg = " ".join(parts)
    return {**updates, "messages": [AIMessage(content=msg)]}


async def analyze_messages(state: State) -> dict[str, Any]:
    """Analyze scraped messages with LLM classification."""
    updates = await run_in_thread(execute_analyze_messages, _state_as_dict(state))
    merged = {**_state_as_dict(state), **updates}
    summary = build_analysis_summary(merged)
    analyzed_count = len(updates.get("analyzed_messages") or [])
    positive_count = len(updates.get("positive_messages") or [])
    return {
        **updates,
        "messages": [
            AIMessage(
                content=(
                    f"Analyzed {analyzed_count} messages "
                    f"({positive_count} positive). {summary}"
                )
            )
        ],
    }


async def select_reply_targets(state: State) -> dict[str, Any]:
    """Select up to N messages for reply generation."""
    updates = await run_in_thread(execute_select_reply_targets, _state_as_dict(state))
    stats = updates.get("reply_statistics") or {}
    selected = stats.get(
        "reply_targets_selected", len(updates.get("reply_targets") or [])
    )
    limit = stats.get(
        "reply_target_limit", get_whatsapp_config()["max_replies_per_run"]
    )
    positive_total = stats.get("positive_messages_total", 0)
    targets = updates.get("reply_targets") or []
    preview_lines = [
        f"Selected {selected} of up to {limit} messages "
        f"(from {positive_total} positive total)."
    ]
    for target in targets[:5]:
        preview_lines.append(
            f"- #{target.get('reply_rank', '?')} {target.get('author', 'contact')} "
            f": {str(target.get('text', ''))[:100]}"
        )
    return {**updates, "messages": [AIMessage(content="\n".join(preview_lines))]}


async def generate_replies(state: State) -> dict[str, Any]:
    """Generate AI replies for selected messages."""
    updates = await run_in_thread(execute_generate_replies, _state_as_dict(state))
    stats = updates.get("reply_statistics") or {}
    count = stats.get("replies_generated", 0)
    personality = stats.get("reply_personality", "friendly")
    posting = "enabled" if stats.get("posting_enabled") else "disabled in .env"
    return {
        **updates,
        "messages": [
            AIMessage(
                content=(
                    f"Generated {count} {personality} AI replies. "
                    f"WhatsApp sending is {posting}."
                )
            )
        ],
    }


async def send_replies(state: State) -> dict[str, Any]:
    """Send replies through WhatsApp Web when ENABLE_MESSAGE_REPLIES=true."""
    apply_runtime_overrides(_state_as_dict(state))
    merged = {**_state_as_dict(state)}
    updates = await run_playwright(execute_send_replies, merged)
    stats = updates.get("reply_statistics") or merged.get("reply_statistics") or {}
    posted = stats.get("replies_posted", 0)
    failed = stats.get("replies_failed", 0)
    config = get_whatsapp_config()
    enable_replies = (
        state.get("enable_message_replies")
        if state.get("enable_message_replies") is not None
        else config["enable_message_replies"]
    )
    if not enable_replies:
        content = "Reply sending skipped (ENABLE_MESSAGE_REPLIES=false). Replies saved in report."
    elif posted and not failed:
        content = f"Sent {posted} replies on WhatsApp."
    elif posted:
        content = f"Sent {posted} replies; {failed} failed (see report for details)."
    elif failed:
        content = f"All {failed} send attempt(s) failed (see report for details)."
    else:
        content = "No replies were sent (none generated or browser send failed)."
    shots = len(updates.get("screenshots") or [])
    if shots:
        content += f" Captured {shots} screenshot(s)."
    return {
        **updates,
        "screenshots": updates.get("screenshots") or [],
        "messages": [AIMessage(content=content)],
    }


async def generate_html_report(state: State) -> dict[str, Any]:
    """Generate comprehensive HTML dashboard report."""
    merged = {**_state_as_dict(state)}
    updates = await run_playwright(execute_generate_html_report, merged)
    html_result = updates.get("html_result", "HTML report generated.")
    return {**updates, "messages": [AIMessage(content=html_result)]}


async def generate_pdf_report(state: State) -> dict[str, Any]:
    """Generate PDF messaging report."""
    action = state.get("workflow_action", "")
    if action not in ("report", "email") and not wants_pdf_report(
        get_latest_user_text(state.get("messages") or [])
    ):
        return {
            "messages": [
                AIMessage(content="PDF generation skipped for analyze-only run.")
            ]
        }
    updates = await run_in_thread(execute_generate_pdf_report, _state_as_dict(state))
    pdf_result = updates.get("pdf_result", "PDF generated.")
    return {**updates, "messages": [AIMessage(content=pdf_result)]}


async def email_report(state: State) -> dict[str, Any]:
    """Email HTML dashboard and PDF reports when enabled."""
    apply_runtime_overrides(_state_as_dict(state))
    action = state.get("workflow_action", "")
    config = get_whatsapp_config()
    should_email = (
        action == "email"
        or wants_email_report(get_latest_user_text(state.get("messages") or []))
        or state.get("email_reports") is True
        or (state.get("email_reports") is not False and config["email_reports"])
    )
    if not should_email:
        html_path = _state_as_dict(state).get("html_path", "")
        if html_path:
            return {
                "email_result": "Email skipped — HTML dashboard saved",
                "messages": [
                    AIMessage(
                        content=f"Email skipped. HTML dashboard saved: {html_path}"
                    )
                ],
            }
        return {
            "email_result": "Email skipped for this run",
            "messages": [AIMessage(content="Email step skipped.")],
        }
    updates = await run_in_thread(execute_email_report, _state_as_dict(state))
    email_result = updates.get("email_result", "Email step completed.")
    return {**updates, "messages": [AIMessage(content=email_result)]}


async def call_model(state: State) -> dict[str, Any]:
    """LLM path for general chat and dynamic tool selection."""
    messages, _ = _prepare_messages(state)

    has_system_message = any(
        getattr(message, "type", None) == "system" for message in messages
    )
    llm_messages = (
        [SystemMessage(content=SYSTEM_PROMPT), *messages]
        if not has_system_message
        else messages
    )

    model_with_tools = get_model().bind_tools(llm_tools)
    response = await model_with_tools.ainvoke(llm_messages)

    if isinstance(response, AIMessage) and is_empty_ai_message(response):
        if response.tool_calls:
            tool_names = ", ".join(
                tc.get("name", "tool")
                if isinstance(tc, dict)
                else getattr(tc, "name", "tool")
                for tc in response.tool_calls
            )
            response.content = f"Calling tools: {tool_names}"
        else:
            response.content = (
                "I can scan your WhatsApp inbox for read conversations, generate contextual "
                "replies, send them on WhatsApp Web, and email an HTML report."
            )

    return {"messages": [response]}


def route_after_decision(state: State) -> AgentRoute:
    """Route from decide_agent to the chosen execution node."""
    return state.get("agent_route", "call_model")


def route_after_generate_replies(
    state: State,
) -> Literal["send_replies", "generate_html_report"]:
    """Skip browser reply sending when disabled."""
    apply_runtime_overrides(_state_as_dict(state))
    config = get_whatsapp_config()
    replies = state.get("generated_replies") or []
    if state.get("enable_message_replies") is not None:
        enable_replies = bool(state.get("enable_message_replies"))
    else:
        enable_replies = config["enable_message_replies"]
    if enable_replies and replies:
        return "send_replies"
    return "generate_html_report"


def route_after_model(state: State) -> Literal["tools", END]:
    """Route from call_model to tools or end."""
    messages = state.get("messages") or []
    if not messages:
        return END

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


graph_builder = StateGraph(State)

graph_builder.add_node("prepare_agent", prepare_input)
graph_builder.add_node("decide_agent", decision_agent)
graph_builder.add_node("execute_workflow", execute_workflow)
graph_builder.add_node("login_whatsapp", login_whatsapp)
graph_builder.add_node("scan_read_conversations", scan_read_conversations)
graph_builder.add_node("analyze_messages", analyze_messages)
graph_builder.add_node("select_reply_targets", select_reply_targets)
graph_builder.add_node("generate_replies", generate_replies)
graph_builder.add_node("send_replies", send_replies)
graph_builder.add_node("generate_html_report", generate_html_report)
graph_builder.add_node("generate_pdf_report", generate_pdf_report)
graph_builder.add_node("email_report", email_report)
graph_builder.add_node("call_tool", call_model)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "prepare_agent")
graph_builder.add_edge("prepare_agent", "decide_agent")
graph_builder.add_conditional_edges(
    "decide_agent",
    route_after_decision,
    {
        "whatsapp_workflow": "login_whatsapp",
        "execute_workflow": "execute_workflow",
        "call_model": "call_tool",
    },
)
graph_builder.add_edge("login_whatsapp", "scan_read_conversations")
graph_builder.add_edge("scan_read_conversations", "analyze_messages")
graph_builder.add_edge("analyze_messages", "select_reply_targets")
graph_builder.add_edge("select_reply_targets", "generate_replies")
graph_builder.add_conditional_edges(
    "generate_replies",
    route_after_generate_replies,
    {
        "send_replies": "send_replies",
        "generate_html_report": "generate_html_report",
    },
)
graph_builder.add_edge("send_replies", "generate_html_report")
graph_builder.add_edge("generate_html_report", "generate_pdf_report")
graph_builder.add_edge("generate_pdf_report", "email_report")
graph_builder.add_edge("email_report", END)
graph_builder.add_edge("execute_workflow", END)
graph_builder.add_conditional_edges("call_tool", route_after_model)
graph_builder.add_edge("tools", "call_tool")

graph = graph_builder.compile(name="WhatsApp Messaging Agent")
