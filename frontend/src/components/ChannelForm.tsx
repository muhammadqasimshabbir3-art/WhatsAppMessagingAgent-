import type { AgentRunSettings } from "../types";
import { REPLY_PERSONALITY_OPTIONS } from "../lib/defaultSettings";

interface AgentConfigFormProps {
  settings: AgentRunSettings;
  onChange: <K extends keyof AgentRunSettings>(key: K, value: AgentRunSettings[K]) => void;
  disabled?: boolean;
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="toggle-row">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span>
        <strong>{label}</strong>
        {hint && <small>{hint}</small>}
      </span>
    </label>
  );
}

export function AgentConfigForm({ settings, onChange, disabled }: AgentConfigFormProps) {
  return (
    <section className="panel channel-form">
      <div className="panel-title">
        <span>💬 WhatsApp Inbox Agent</span>
      </div>
      <p className="panel-desc">
        Playwright opens a <strong>persistent Chrome profile</strong> at{" "}
        <code>./data/chrome_profile</code> and navigates to{" "}
        <code>https://web.whatsapp.com/</code>. Scan the QR code once — later runs stay
        logged in. Email reports use Gmail SMTP separately (
        <code>GMAIL_SMTP_USER</code> / <code>GMAIL_APP_PASSWORD</code>).
        <strong>unread</strong> chats, extracts conversations, generates contextual replies,
        sends them, captures screenshots, and emails an HTML report.
      </p>

      <h3 className="form-section-title">Inbox scan</h3>
      <div className="form-grid">
        <label>
          <span>Contact filter (optional)</span>
          <input
            type="text"
            value={settings.contactFilter}
            onChange={(e) => onChange("contactFilter", e.target.value)}
            placeholder="e.g. John Smith — leave empty for all unread chats"
            disabled={disabled}
          />
        </label>
        <label>
          <span>Max chats to process</span>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.maxChatsToProcess}
            onChange={(e) =>
              onChange("maxChatsToProcess", Math.max(1, Number(e.target.value) || 1))
            }
            disabled={disabled}
          />
        </label>
        <label>
          <span>Max messages per chat</span>
          <input
            type="number"
            min={1}
            max={100}
            value={settings.maxMessagesPerChat}
            onChange={(e) =>
              onChange("maxMessagesPerChat", Math.max(1, Number(e.target.value) || 1))
            }
            disabled={disabled}
          />
        </label>
        <label>
          <span>Max replies per run</span>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.maxReplies}
            onChange={(e) => onChange("maxReplies", Math.max(1, Number(e.target.value) || 1))}
            disabled={disabled}
          />
        </label>
        <label>
          <span>Reply personality</span>
          <select
            value={settings.replyPersonality}
            onChange={(e) => onChange("replyPersonality", e.target.value)}
            disabled={disabled}
          >
            {REPLY_PERSONALITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="toggle-grid">
        <ToggleRow
          label="Only unread chats"
          hint="Reply only to contacts with unread messages (REPLY_ONLY_UNREAD_CHATS)"
          checked={settings.replyOnlyUnreadChats}
          onChange={(v) => onChange("replyOnlyUnreadChats", v)}
          disabled={disabled}
        />
        <ToggleRow
          label="Enable message replies"
          hint="Send AI replies on WhatsApp Web (ENABLE_MESSAGE_REPLIES)"
          checked={settings.enableMessageReplies}
          onChange={(v) => onChange("enableMessageReplies", v)}
          disabled={disabled}
        />
        <ToggleRow
          label="Keep browser open"
          hint="Reuse browser through scan, send, and screenshots"
          checked={settings.keepBrowserOpen}
          onChange={(v) => onChange("keepBrowserOpen", v)}
          disabled={disabled}
        />
      </div>

      <h3 className="form-section-title">Email report</h3>
      <div className="toggle-grid">
        <ToggleRow
          label="Email HTML report"
          hint="Send inbox reply log via Gmail SMTP"
          checked={settings.emailReports}
          onChange={(v) => onChange("emailReports", v)}
          disabled={disabled}
        />
      </div>
      <div className="form-grid">
        <label>
          <span>Email recipient</span>
          <input
            type="email"
            value={settings.emailRecipient}
            onChange={(e) => onChange("emailRecipient", e.target.value)}
            placeholder="you@example.com"
            disabled={disabled || !settings.emailReports}
          />
        </label>
      </div>
    </section>
  );
}

interface RunControlsProps {
  running: boolean;
  serverOnline: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function RunControls({ running, serverOnline, onStart, onStop }: RunControlsProps) {
  return (
    <section className="panel run-controls">
      <div className="panel-title">
        <span>🤖 Run Agent</span>
      </div>
      <div className="button-row">
        {!running ? (
          <button
            type="button"
            className="btn primary start-btn"
            disabled={!serverOnline}
            onClick={onStart}
          >
            ▶️ Start Agent
          </button>
        ) : (
          <button type="button" className="btn danger stop-btn" onClick={onStop}>
            ⏹️ Stop Agent
          </button>
        )}
      </div>
      {!serverOnline && (
        <p className="hint warn">
          Start the LangGraph server first: <code>./start.sh both</code>
        </p>
      )}
      {running && (
        <p className="hint running-hint">🔄 Scanning inbox and processing read conversations…</p>
      )}
    </section>
  );
}
