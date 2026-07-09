import type { StepState, WorkflowStep } from "../types";

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: "prepare",
    nodes: ["prepare_agent", "decide_agent"],
    label: "🧠 Agent Planning",
    description: "Load inbox settings and build the task plan",
    emoji: "🧠",
  },
  {
    id: "login",
    nodes: ["login_whatsapp"],
    label: "🔐 WhatsApp login",
    description: "Verify WhatsApp Web session from saved profile",
    emoji: "🔐",
  },
  {
    id: "fetch",
    nodes: ["scan_read_conversations"],
    label: "📥 Scan Inbox",
    description: "Open WhatsApp Web, find unread chats, extract conversations",
    emoji: "📥",
  },
  {
    id: "analyze",
    nodes: ["analyze_messages"],
    label: "🔍 Analyze Sentiment",
    description: "Classify messages by sentiment and engagement priority",
    emoji: "🔍",
  },
  {
    id: "select",
    nodes: ["select_reply_targets"],
    label: "🎯 Select Reply Targets",
    description: "Pick messages that need a reply",
    emoji: "🎯",
  },
  {
    id: "generate_replies",
    nodes: ["generate_replies"],
    label: "✍️ Generate Replies",
    description: "Write AI replies for selected messages",
    emoji: "✍️",
  },
  {
    id: "send_replies",
    nodes: ["send_replies"],
    label: "💬 Send on WhatsApp",
    description: "Send replies through WhatsApp Web (when enabled)",
    optional: true,
    emoji: "💬",
  },
  {
    id: "html_report",
    nodes: ["generate_html_report"],
    label: "📊 HTML Dashboard",
    description: "Build interactive dashboard report and close browser",
    emoji: "📊",
  },
  {
    id: "pdf_report",
    nodes: ["generate_pdf_report"],
    label: "📄 PDF Report",
    description: "Export PDF messaging summary",
    optional: true,
    emoji: "📄",
  },
  {
    id: "email",
    nodes: ["email_report"],
    label: "📧 Email Delivery",
    description: "Send HTML + PDF via Gmail SMTP",
    optional: true,
    emoji: "📧",
  },
];

const NODE_TO_STEP = new Map<string, string>();
for (const step of WORKFLOW_STEPS) {
  for (const node of step.nodes) {
    NODE_TO_STEP.set(node, step.id);
  }
}
NODE_TO_STEP.set("execute_workflow", "prepare");

export function stepIdForNode(nodeName: string): string | undefined {
  return NODE_TO_STEP.get(nodeName);
}

export function initialStepStates(): StepState[] {
  return WORKFLOW_STEPS.map((step) => ({
    id: step.id,
    status: "pending" as const,
  }));
}

export function detailForNode(nodeName: string, payload: Record<string, unknown>): string {
  switch (nodeName) {
    case "prepare_agent":
      return "Preparing agent input…";
    case "scan_read_conversations": {
      const scraped = payload.inbound_messages_count ?? (payload.chat_messages as unknown[])?.length;
      const unread = payload.unread_chats_found ?? payload.read_chats_found;
      if (scraped != null && unread != null) return `${unread} unread chat(s), ${scraped} message(s)`;
      if (scraped != null) return `${scraped} messages extracted`;
      return "Inbox scanned";
    }
    case "analyze_messages": {
      const count = (payload.analyzed_messages as unknown[])?.length;
      return count != null ? `${count} messages analyzed` : "Analysis complete";
    }
    case "select_reply_targets": {
      const count = (payload.reply_targets as unknown[])?.length;
      return count != null ? `${count} reply target(s) selected` : "Targets selected";
    }
    case "generate_replies": {
      const stats = payload.reply_statistics as Record<string, number> | undefined;
      const n = stats?.replies_generated ?? (payload.generated_replies as unknown[])?.length;
      return n != null ? `${n} reply draft(s) ready` : "Replies generated";
    }
    case "send_replies": {
      const stats = payload.reply_statistics as Record<string, number> | undefined;
      const posted = stats?.replies_posted ?? 0;
      const failed = stats?.replies_failed ?? 0;
      return `${posted} sent, ${failed} failed`;
    }
    case "generate_html_report":
      return payload.html_path ? `Saved ${String(payload.html_path)}` : "HTML report ready";
    case "generate_pdf_report":
      return payload.pdf_path ? `Saved ${String(payload.pdf_path)}` : "PDF report ready";
    case "email_report":
      return payload.email_result ? String(payload.email_result) : "Email step finished";
    case "login_whatsapp": {
      const detail = payload.login_detail ?? payload.whatsapp_login_detail;
      if (detail) {
        const text = String(detail);
        if (payload.logged_in === true || payload.whatsapp_logged_in === true) return `✅ ${text}`;
        if (payload.logged_in === false && payload.whatsapp_logged_in === false) return `⏳ ${text}`;
      }
      if (payload.logged_in === true || payload.whatsapp_logged_in === true) {
        return "✅ WhatsApp Web session active";
      }
      if (payload.logged_in === false || payload.whatsapp_logged_in === false) {
        return "⏳ Complete QR scan in Setup Your Profile";
      }
      return "Checking WhatsApp session…";
    }
    case "decide_agent":
      return payload.task_plan_summary ? String(payload.task_plan_summary) : "Route selected";
    case "execute_workflow":
      return "Full workflow executed in batch mode";
    default:
      return "Done";
  }
}
