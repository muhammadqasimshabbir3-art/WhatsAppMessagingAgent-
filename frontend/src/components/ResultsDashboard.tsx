import { useMemo, useState } from "react";
import { Download, FileText, MessageSquare } from "lucide-react";
import type { AgentState, ConversationRow, MessageRow } from "../types";

function messageRows(messages: MessageRow[], includeReply = false) {
  return messages.map((m) => ({
    Contact: m.contact_name ?? m.author ?? "",
    Category: m.category ?? "",
    Priority: m.engagement_priority ?? "",
    Message: m.text ?? "",
    ...(includeReply
      ? {
          "AI Reply": m.reply_text ?? "",
          Sent: m.posted ? "Yes" : "No",
          Error: m.post_error ?? "",
        }
      : {}),
  }));
}

function conversationRows(conversations: ConversationRow[]) {
  return conversations.map((c) => ({
    Contact: c.contact_name ?? "",
    Preview: c.preview ?? "",
    "Last seen": c.last_seen ?? "",
    Unread: c.is_unread ? "Yes" : "No",
    Messages: c.inbound_messages?.length ?? 0,
  }));
}

interface ResultsDashboardProps {
  result: AgentState | null;
  error: string | null;
}

export function ResultsDashboard({ result, error }: ResultsDashboardProps) {
  const [tab, setTab] = useState("overview");

  const analyzed = result?.analyzed_messages ?? result?.chat_messages ?? [];
  const total = analyzed.length;
  const stats = result?.reply_statistics ?? {};
  const conversations = result?.conversations ?? [];
  const screenshots = result?.screenshots ?? [];
  const hasData =
    total > 0 ||
    conversations.length > 0 ||
    (result?.generated_replies?.length ?? 0) > 0 ||
    Boolean(result?.html_path);

  const tabs = useMemo(
    () => [
      { id: "overview", label: "Overview" },
      { id: "conversations", label: `Chats (${conversations.length})` },
      { id: "replies", label: `AI Replies (${result?.generated_replies?.length ?? 0})` },
      { id: "screenshots", label: `Screenshots (${screenshots.length})` },
      { id: "failed", label: `Failed (${result?.failed_replies?.length ?? 0})` },
      { id: "all", label: `All (${total})` },
    ],
    [result, total, conversations.length, screenshots.length],
  );

  if (error) {
    return (
      <section className="panel results-panel error-panel">
        <h3>Workflow Error</h3>
        <p>{error}</p>
      </section>
    );
  }

  if (!result || !hasData) {
    return (
      <section className="panel results-panel empty-panel">
        <MessageSquare size={28} />
        <h3>Results will appear here</h3>
        <p>Start an agent run to see inbox scan results, replies, screenshots, and report links.</p>
      </section>
    );
  }

  return (
    <section className="panel results-panel">
      <div className="results-header">
        <div>
          <h3>WhatsApp Inbox Dashboard</h3>
          <p>
            {(result.unread_chats_found ?? result.read_chats_found) != null && (
              <>
                <strong>{result.unread_chats_found ?? result.read_chats_found}</strong> unread
                chat(s) processed
              </>
            )}
            {result.chats_scanned != null && <> · {result.chats_scanned} scanned</>}
            {result.contact_filter && <> · filter: {result.contact_filter}</>}
          </p>
        </div>
        <div className="report-links">
          {result.html_path && (
            <span className="btn small path-chip" title={result.html_path}>
              <FileText size={14} /> HTML saved
            </span>
          )}
          {result.pdf_path && (
            <span className="btn small path-chip" title={result.pdf_path}>
              <Download size={14} /> PDF saved
            </span>
          )}
        </div>
      </div>

      <div className="metrics-grid">
        <Metric label="Chats scanned" value={String(result.chats_scanned ?? "—")} />
        <Metric
          label="Unread chats"
          value={String(result.unread_chats_found ?? result.read_chats_found ?? conversations.length)}
        />
        <Metric label="Messages" value={String(total)} />
        <Metric label="Replies sent" value={String(stats.replies_posted ?? 0)} />
        <Metric label="Replies failed" value={String(stats.replies_failed ?? result.failed_replies?.length ?? 0)} />
        <Metric label="Targets" value={String(result.reply_targets?.length ?? 0)} />
      </div>

      {result.llm_summary && (
        <div className="summary-box">
          <strong>Executive summary</strong>
          <p>{result.llm_summary}</p>
        </div>
      )}

      <div className="tab-bar">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === "overview" && (
          <div className="overview-grid">
            <dl className="meta-list">
              <dt>Inbound messages</dt>
              <dd>{result.inbound_messages_count ?? result.chat_messages?.length ?? "—"}</dd>
              <dt>Chats scanned</dt>
              <dd>{result.chats_scanned ?? "—"}</dd>
              <dt>Unread chats processed</dt>
              <dd>{result.unread_chats_found ?? result.read_chats_found ?? conversations.length}</dd>
              <dt>Contact filter</dt>
              <dd>{result.contact_filter || "All unread chats"}</dd>
              <dt>Login</dt>
              <dd>
                {result.login_detail ??
                  result.whatsapp_login_detail ??
                  (result.logged_in ? "WhatsApp OK" : "—")}
              </dd>
            </dl>
          </div>
        )}
        {tab === "conversations" && <DataTable rows={conversationRows(conversations)} />}
        {tab === "replies" && <DataTable rows={messageRows(result.generated_replies ?? [], true)} />}
        {tab === "screenshots" && (
          <div className="screenshot-grid">
            {screenshots.length === 0 ? (
              <p className="muted">No screenshots captured.</p>
            ) : (
              screenshots.map((shot, i) => (
                <div key={i} className="screenshot-card">
                  <strong>{String(shot.contact_name ?? `Chat ${i + 1}`)}</strong>
                  {shot.screenshot_path ? (
                    <code className="mono">{String(shot.screenshot_path)}</code>
                  ) : null}
                </div>
              ))
            )}
          </div>
        )}
        {tab === "failed" && <DataTable rows={messageRows(result.failed_replies ?? [], true)} />}
        {tab === "all" && <DataTable rows={messageRows(analyzed)} />}
      </div>

      {result.email_result && (
        <div className="email-result">
          <strong>Email:</strong> {result.email_result}
        </div>
      )}

      {(result.html_path || result.pdf_path) && (
        <div className="path-list">
          {result.html_path && (
            <p>
              <strong>HTML:</strong> <code className="mono">{result.html_path}</code>
            </p>
          )}
          {result.pdf_path && (
            <p>
              <strong>PDF:</strong> <code className="mono">{result.pdf_path}</code>
            </p>
          )}
          <p className="muted">Reports are written on the LangGraph server host (see <code>reports/</code> locally).</p>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <p className="muted">No data in this tab.</p>;
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c}>{String(row[c] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
