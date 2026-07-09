import { CheckCircle2, Chrome, ExternalLink, Loader2, QrCode, Smartphone } from "lucide-react";

interface ProfileSetupProps {
  disabled?: boolean;
  loading: boolean;
  error: string | null;
  loggedIn: boolean;
  awaitingQr: boolean;
  isHostedUi: boolean;
  onOpenBrowser: () => void;
}

export function ProfileSetup({
  disabled,
  loading,
  error,
  loggedIn,
  awaitingQr,
  isHostedUi,
  onOpenBrowser,
}: ProfileSetupProps) {
  return (
    <section className="panel profile-setup">
      <div className="panel-heading">
        <div>
          <h2>Setup Your Profile</h2>
          <p className="panel-subtitle">
            {isHostedUi
              ? "Opens WhatsApp Web in a normal browser window (new tab) — not embedded in this page. Scan the QR code there once."
              : "Opens a real Chrome window on your machine — not embedded in this page. Scan the QR once; the profile is reused on every run."}
          </p>
        </div>
      </div>

      {error && !isHostedUi && (
        <p className="hint warn">
          Browser API offline. Run <code>./start.sh both</code> or <code>./start.sh browser</code>{" "}
          from the project folder.
        </p>
      )}

      <div className="setup-browser-area">
        {loggedIn ? (
          <div className="browser-success">
            <CheckCircle2 size={28} />
            <div>
              <strong>WhatsApp connected</strong>
              <p>
                Session saved in your Chrome profile. The browser opens automatically when you start
                the app.
              </p>
            </div>
          </div>
        ) : awaitingQr ? (
          <div className="browser-waiting">
            {isHostedUi ? (
              <ExternalLink size={32} className="browser-idle-icon" />
            ) : (
              <Chrome size={32} className="browser-idle-icon" />
            )}
            <strong>
              {isHostedUi
                ? "WhatsApp Web opened in a new tab — scan the QR code"
                : "Chrome is open — scan the QR code"}
            </strong>
            <p>
              {isHostedUi
                ? "Use the browser tab that just opened. On your phone: Settings → Linked devices → Link a device."
                : "Use the WhatsApp Web window on your desktop. On your phone: Settings → Linked devices → Link a device."}
            </p>
            {!isHostedUi && (
              <div className="browser-hint">
                <Smartphone size={16} />
                <span>Waiting for login… this page updates when the scan succeeds.</span>
              </div>
            )}
            {isHostedUi && (
              <button
                type="button"
                className="btn ghost small"
                onClick={onOpenBrowser}
                disabled={disabled}
              >
                <ExternalLink size={14} />
                Open again
              </button>
            )}
            {loading && (
              <div className="browser-hint">
                <Loader2 size={14} className="spin" />
                <span>Opening browser…</span>
              </div>
            )}
          </div>
        ) : (
          <div className="browser-idle">
            <QrCode size={36} className="browser-idle-icon" />
            <p>
              {isHostedUi
                ? "Connect WhatsApp by opening WhatsApp Web in a normal browser window."
                : "Connect WhatsApp by opening Chrome and scanning the QR code."}
            </p>
            <button
              type="button"
              className="btn primary"
              onClick={onOpenBrowser}
              disabled={disabled || loading}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Opening…
                </>
              ) : isHostedUi ? (
                <>
                  <ExternalLink size={16} />
                  Open WhatsApp Web
                </>
              ) : (
                <>
                  <Chrome size={16} />
                  Open WhatsApp browser
                </>
              )}
            </button>
            {!isHostedUi && (
              <p className="browser-cli-hint">
                Or run in terminal: <code>./start.sh browser</code>
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
