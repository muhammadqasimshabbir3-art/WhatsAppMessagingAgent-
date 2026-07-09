import type { AgentRunSettings } from "../types";
import { REPLY_PERSONALITY_OPTIONS } from "../lib/defaultSettings";

interface AgentConfigFormProps {
  settings: AgentRunSettings;
  onChange: <K extends keyof AgentRunSettings>(key: K, value: AgentRunSettings[K]) => void;
  disabled?: boolean;
}

function ToggleRow({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
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
      <span>{label}</span>
    </label>
  );
}

export function AgentConfigForm({ settings, onChange, disabled }: AgentConfigFormProps) {
  return (
    <section className="panel channel-form">
      <div className="panel-heading">
        <div>
          <h2>Inbox settings</h2>
          <p className="panel-subtitle">Configure scan limits and reply behavior.</p>
        </div>
      </div>

      <div className="form-grid">
        <label>
          <span>Contact filter</span>
          <input
            type="text"
            value={settings.contactFilter}
            onChange={(e) => onChange("contactFilter", e.target.value)}
            placeholder="Optional — leave empty for all unread"
            disabled={disabled}
          />
        </label>
        <label>
          <span>Max chats</span>
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
          <span>Context messages per chat</span>
          <input
            type="number"
            min={1}
            max={50}
            value={settings.maxMessagesPerChat}
            onChange={(e) =>
              onChange("maxMessagesPerChat", Math.max(1, Number(e.target.value) || 1))
            }
            disabled={disabled}
          />
        </label>
        <label>
          <span>Max replies</span>
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
          <span>Reply tone</span>
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
        <label>
          <span>Report recipient</span>
          <input
            type="email"
            value={settings.emailRecipient}
            onChange={(e) => onChange("emailRecipient", e.target.value)}
            placeholder="you@example.com"
            disabled={disabled || !settings.emailReports}
          />
        </label>
      </div>

      <div className="toggle-grid compact">
        <ToggleRow
          label="Unread chats only"
          checked={settings.replyOnlyUnreadChats}
          onChange={(v) => onChange("replyOnlyUnreadChats", v)}
          disabled={disabled}
        />
        <ToggleRow
          label="Send AI replies"
          checked={settings.enableMessageReplies}
          onChange={(v) => onChange("enableMessageReplies", v)}
          disabled={disabled}
        />
        <ToggleRow
          label="Email HTML report"
          checked={settings.emailReports}
          onChange={(v) => onChange("emailReports", v)}
          disabled={disabled}
        />
      </div>
    </section>
  );
}

interface RunControlsProps {
  running: boolean;
  serverOnline: boolean;
  whatsappReady: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function RunControls({
  running,
  serverOnline,
  whatsappReady,
  onStart,
  onStop,
}: RunControlsProps) {
  const canStart = serverOnline && whatsappReady;

  return (
    <section className="panel run-controls">
      <div className="run-controls-row">
        {!running ? (
          <button
            type="button"
            className="btn primary start-btn"
            disabled={!canStart}
            onClick={onStart}
          >
            Start agent
          </button>
        ) : (
          <button type="button" className="btn danger stop-btn" onClick={onStop}>
            Stop agent
          </button>
        )}
        {!serverOnline && (
          <p className="hint warn inline-hint">LangGraph server offline — run ./start.sh both</p>
        )}
        {serverOnline && !whatsappReady && (
          <p className="hint warn inline-hint">Connect WhatsApp in Setup Your Profile first</p>
        )}
        {running && <p className="hint running-hint inline-hint">Processing inbox…</p>}
      </div>
    </section>
  );
}
