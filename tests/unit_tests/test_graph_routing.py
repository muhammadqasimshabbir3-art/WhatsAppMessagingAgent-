"""Tests for graph routing with inbox defaults."""

from langchain_core.messages import HumanMessage

from agent.graph import _pick_route


def test_general_chat_not_routed_to_whatsapp_with_contact_filter_in_state():
    messages = [HumanMessage(content="Hello there")]
    state = {"contact_filter": "Alice"}
    assert _pick_route(state, messages, "Hello there") == "call_model"


def test_workflow_action_routes_to_whatsapp():
    messages = [HumanMessage(content="run analysis")]
    state = {"workflow_action": "analyze", "contact_filter": "Alice"}
    assert _pick_route(state, messages, "run analysis") == "whatsapp_workflow"
