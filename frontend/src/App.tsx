import { useCallback, useState } from "react";
import { ASSISTANT_ID } from "./config";
import { AgentHeader } from "./components/AgentHeader";
import { ActivityLog } from "./components/ActivityLog";
import { AgentConfigForm, RunControls } from "./components/ChannelForm";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { ProfileSetup } from "./components/ProfileSetup";
import { ResultsDashboard } from "./components/ResultsDashboard";
import { SlackAgentTab } from "./components/SlackAgentTab";
import { WorkflowPipeline } from "./components/WorkflowPipeline";
import { useAgentRun } from "./hooks/useAgentRun";
import { useBrowserSession } from "./hooks/useBrowserSession";
import { useServerHealth } from "./hooks/useServerHealth";
import { loadRunSettings, saveRunSettings } from "./lib/settingsStorage";
import type { AgentRunSettings } from "./types";
import type { AppTab } from "./components/AgentHeader";

export default function App() {
  const health = useServerHealth();
  const agent = useAgentRun();
  const browser = useBrowserSession();
  const [settings, setSettings] = useState<AgentRunSettings>(loadRunSettings);
  const [activeTab, setActiveTab] = useState<AppTab>("whatsapp");

  const updateSetting = useCallback(
    <K extends keyof AgentRunSettings>(key: K, value: AgentRunSettings[K]) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value };
        saveRunSettings(next);
        return next;
      });
    },
    [],
  );

  const startAgent = () => void agent.run(settings);
  const whatsappConnected =
    browser.loggedIn ||
    agent.loggedIn === true ||
    (browser.isHostedUi && health.status === "online");

  return (
    <div className="app-shell">
      <AgentHeader
        serverStatus={health.status}
        latencyMs={health.latencyMs}
        running={agent.running}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        whatsappConnected={whatsappConnected}
      />

      {activeTab === "slack" ? (
        <SlackAgentTab />
      ) : (
        <div className="layout">
          <div className="main-column">
            <ProfileSetup
              disabled={agent.running}
              loading={browser.loading}
              error={browser.error}
              loggedIn={browser.loggedIn}
              awaitingQr={browser.awaitingQr}
              isHostedUi={browser.isHostedUi}
              onOpenBrowser={() => void browser.openBrowser()}
            />
            <AgentConfigForm
              settings={settings}
              onChange={updateSetting}
              disabled={agent.running}
            />
            <RunControls
              running={agent.running}
              serverOnline={health.status === "online"}
              whatsappReady={whatsappConnected}
              onStart={startAgent}
              onStop={agent.cancel}
            />
            <WorkflowPipeline
              steps={agent.steps}
              running={agent.running}
              reconnected={agent.reconnected}
              taskPlanSummary={agent.result?.task_plan_summary}
            />
            <ResultsDashboard result={agent.result} error={agent.error} />
          </div>

          <div className="side-column">
            <ConnectionPanel
              status={health.status}
              latencyMs={health.latencyMs}
              assistantId={ASSISTANT_ID}
              threadId={agent.threadId}
              runId={agent.runId}
              loggedIn={whatsappConnected ? true : browser.needsQr ? false : null}
              onRefresh={health.check}
            />
            <ActivityLog logs={agent.logs} />
          </div>
        </div>
      )}
    </div>
  );
}
