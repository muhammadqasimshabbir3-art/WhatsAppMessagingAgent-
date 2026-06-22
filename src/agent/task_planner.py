"""Decision agent: plan WhatsApp inbox reply tasks."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.routing import wants_email_report, wants_pdf_report, wants_whatsapp_messaging


@dataclass
class TaskPlan:
    """Ordered list of tasks the agent should perform."""

    tasks: list[str] = field(default_factory=list)
    user_text: str = ""
    contact_filter: str = ""
    workflow_action: str = "analyze"

    @property
    def is_whatsapp_workflow(self) -> bool:
        return bool(self.tasks)

    def summary(self) -> str:
        labels = {
            "login": "Verify WhatsApp Web session",
            "fetch_messages": "Scan inbox and read conversations",
            "analyze": "Analyze messages",
            "select_reply_targets": "Select contacts to reply to",
            "generate_replies": "Generate contextual AI replies",
            "send_replies": "Send replies + screenshot (if enabled)",
            "generate_pdf": "Generate PDF report",
            "generate_html": "Generate HTML report with message/reply log",
            "email_report": "Email HTML report",
        }
        steps = [labels.get(task, task) for task in self.tasks]
        return " → ".join(steps) if steps else "General conversation"


def plan_tasks(
    user_text: str,
    contact_filter: str = "",
    workflow_action: str = "",
) -> TaskPlan:
    """Decide which WhatsApp inbox tasks to run."""
    plan = TaskPlan(user_text=user_text, contact_filter=contact_filter.strip())
    plan.workflow_action = workflow_action or "analyze"

    explicit_intent = bool(workflow_action) or wants_whatsapp_messaging(user_text)
    if not explicit_intent:
        return plan

    plan.tasks = [
        "login",
        "fetch_messages",
        "analyze",
        "select_reply_targets",
        "generate_replies",
        "send_replies",
        "generate_html",
        "email_report",
    ]

    if wants_pdf_report(user_text) or workflow_action in ("report", "email"):
        plan.tasks.insert(-1, "generate_pdf")

    return plan


def is_whatsapp_workflow_request(user_text: str, contact_filter: str = "") -> bool:
    """Return True when the request should run the WhatsApp workflow."""
    return plan_tasks(user_text, contact_filter).is_whatsapp_workflow
