import { Hash } from "lucide-react";

export function SlackAgentTab() {
  return (
    <section className="panel empty-state">
      <div className="empty-state-icon">
        <Hash size={28} />
      </div>
      <h2>Slack Agent</h2>
      <p>Coming soon — monitor channels, analyze threads, and send AI replies from Slack.</p>
    </section>
  );
}
