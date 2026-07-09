import { Loader2, RefreshCw, Wifi, WifiOff } from "lucide-react";
import type { ServerStatus } from "../hooks/useServerHealth";

interface ConnectionPanelProps {
  status: ServerStatus;
  latencyMs: number | null;
  assistantId: string;
  threadId: string | null;
  runId: string | null;
  loggedIn: boolean | null;
  onRefresh: () => void;
}

export function ConnectionPanel({
  status,
  latencyMs,
  assistantId,
  threadId,
  runId,
  loggedIn,
  onRefresh,
}: ConnectionPanelProps) {
  return (
    <aside className="panel connection-panel">
      <div className="panel-heading compact">
        <h3>Status</h3>
        <button type="button" className="icon-btn" onClick={onRefresh} title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="connection-grid">
        <div className="connection-row">
          <span>Backend</span>
          <span className={`health ${status}`}>
            {status === "checking" && <Loader2 size={14} className="spin" />}
            {status === "online" && <Wifi size={14} />}
            {status === "offline" && <WifiOff size={14} />}
            {status}
            {latencyMs != null ? ` · ${latencyMs}ms` : ""}
          </span>
        </div>
        <div className="connection-row">
          <span>Graph</span>
          <code className="mono">{assistantId}</code>
        </div>
        <div className="connection-row">
          <span>WhatsApp</span>
          <span className={`health ${loggedIn === true ? "online" : loggedIn === false ? "offline" : ""}`}>
            {loggedIn === true && "Connected"}
            {loggedIn === false && "Needs QR scan"}
            {loggedIn == null && "—"}
          </span>
        </div>
        {threadId && (
          <div className="connection-row">
            <span>Thread</span>
            <code className="mono">{threadId.slice(0, 10)}…</code>
          </div>
        )}
        {runId && (
          <div className="connection-row">
            <span>Run</span>
            <code className="mono">{runId.slice(0, 10)}…</code>
          </div>
        )}
      </div>
    </aside>
  );
}
