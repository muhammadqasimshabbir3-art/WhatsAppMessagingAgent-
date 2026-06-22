"""Tests for WhatsApp task planner."""

from agent.task_planner import is_whatsapp_workflow_request, plan_tasks


def test_whatsapp_workflow_plan():
    plan = plan_tasks("reply to whatsapp messages", contact_filter="Alice")
    assert plan.is_whatsapp_workflow
    assert "login" in plan.tasks
    assert "fetch_messages" in plan.tasks
    assert "analyze" in plan.tasks
    assert "select_reply_targets" in plan.tasks
    assert "generate_replies" in plan.tasks
    assert "send_replies" in plan.tasks
    assert "generate_html" in plan.tasks
    assert "email_report" in plan.tasks


def test_report_workflow_includes_pdf():
    plan = plan_tasks(
        "scan whatsapp inbox and generate pdf report",
        contact_filter="Alice",
        workflow_action="report",
    )
    assert "generate_pdf" in plan.tasks
    assert "generate_html" in plan.tasks


def test_email_workflow_includes_email():
    plan = plan_tasks(
        "scan whatsapp inbox and email report",
        contact_filter="Alice",
        workflow_action="email",
    )
    assert "generate_pdf" in plan.tasks
    assert "generate_html" in plan.tasks
    assert "email_report" in plan.tasks


def test_non_whatsapp_request():
    plan = plan_tasks("hello there")
    assert not plan.is_whatsapp_workflow
    assert not is_whatsapp_workflow_request("hello there")
