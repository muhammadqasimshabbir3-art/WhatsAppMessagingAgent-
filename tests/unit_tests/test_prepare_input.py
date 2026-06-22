"""Tests for env-driven graph input bootstrap."""

import pytest
from langchain_core.messages import HumanMessage

from agent.graph import _pick_route, prepare_input


@pytest.mark.anyio
async def test_prepare_input_bootstraps_inbox_workflow(monkeypatch):
    monkeypatch.setenv("CONTACT_FILTER", "Alice")
    from agent.config import get_whatsapp_config

    get_whatsapp_config.cache_clear()

    updates = await prepare_input({})

    get_whatsapp_config.cache_clear()
    assert updates["workflow_action"] == "analyze"
    assert updates["contact_filter"] == "Alice"
    assert updates["messages"]
    assert isinstance(updates["messages"][0], HumanMessage)
    assert "Alice" in updates["messages"][0].content


@pytest.mark.anyio
async def test_env_only_run_routes_to_whatsapp_workflow(monkeypatch):
    monkeypatch.delenv("CONTACT_FILTER", raising=False)
    from agent.config import get_whatsapp_config

    get_whatsapp_config.cache_clear()
    updates = await prepare_input({})
    get_whatsapp_config.cache_clear()

    state = {**updates}
    messages = state["messages"]
    user_text = messages[0].content
    route = _pick_route(state, messages, user_text)
    assert route == "whatsapp_workflow"
