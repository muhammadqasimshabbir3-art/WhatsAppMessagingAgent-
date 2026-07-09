import { useEffect, useState } from "react";
import { Activity, Mail, MessageCircle, Radio } from "lucide-react";
import type { ServerStatus } from "../hooks/useServerHealth";
import { fetchAccountInfo } from "../lib/browserClient";

export type AppTab = "whatsapp" | "slack";

interface AgentHeaderProps {
  serverStatus: ServerStatus;
  latencyMs: number | null;
  running: boolean;
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
  whatsappConnected?: boolean;
}

export function AgentHeader({
  serverStatus,
  latencyMs,
  running,
  activeTab,
  onTabChange,
  whatsappConnected,
}: AgentHeaderProps) {
  const [gmailAccount, setGmailAccount] = useState<string | null>(null);

  useEffect(() => {
    void fetchAccountInfo()
      .then((info) => setGmailAccount(info.configured ? info.email : null))
      .catch(() => setGmailAccount(null));
  }, []);

  return (
    <header className="agent-header">
      <div className="header-top">
        <div className="brand">
          <div className="brand-icon">
            <MessageCircle size={22} />
          </div>
          <div>
            <h1>Messaging Agent</h1>
            <p>AI-powered inbox automation</p>
          </div>
        </div>

        <div className="header-meta">
          <div className={`status-pill ${serverStatus}`}>
            <Radio size={14} />
            <span>
              {serverStatus === "online"
                ? "Connected"
                : serverStatus === "offline"
                  ? "Offline"
                  : "Checking…"}
            </span>
            {latencyMs != null && <span className="muted">· {latencyMs}ms</span>}
          </div>
          {running && (
            <div className="status-pill running">
              <Activity size={14} className="spin" />
              <span>Running</span>
            </div>
          )}
          {gmailAccount && (
            <div className="status-pill neutral" title="Gmail account used for report emails">
              <Mail size={14} />
              <span className="truncate">{gmailAccount}</span>
            </div>
          )}
          {whatsappConnected && (
            <div className="status-pill online">
              <MessageCircle size={14} />
              <span>WhatsApp ready</span>
            </div>
          )}
        </div>
      </div>

      <nav className="app-nav" aria-label="Main navigation">
        <button
          type="button"
          className={`nav-tab ${activeTab === "whatsapp" ? "active" : ""}`}
          onClick={() => onTabChange("whatsapp")}
        >
          WhatsApp Messaging
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === "slack" ? "active" : ""}`}
          onClick={() => onTabChange("slack")}
        >
          Slack Agent
        </button>
      </nav>
    </header>
  );
}
