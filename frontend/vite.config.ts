import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const BACKEND_TO_VITE_DEFAULT: [string, string][] = [
  ["CONTACT_FILTER", "VITE_DEFAULT_CONTACT_FILTER"],
  ["MAX_CHATS_TO_PROCESS", "VITE_DEFAULT_MAX_CHATS_TO_PROCESS"],
  ["MAX_MESSAGES_PER_CHAT", "VITE_DEFAULT_MAX_MESSAGES_PER_CHAT"],
  ["MAX_REPLIES_PER_RUN", "VITE_DEFAULT_MAX_REPLIES"],
  ["REPLY_PERSONALITY", "VITE_DEFAULT_REPLY_PERSONALITY"],
  ["ENABLE_MESSAGE_REPLIES", "VITE_DEFAULT_ENABLE_MESSAGE_REPLIES"],
  ["REPLY_ONLY_READ_CHATS", "VITE_DEFAULT_REPLY_ONLY_READ_CHATS"],
  ["KEEP_BROWSER_OPEN", "VITE_DEFAULT_KEEP_BROWSER_OPEN"],
  ["REPLY_TO_POSITIVE", "VITE_DEFAULT_REPLY_TO_POSITIVE"],
  ["REPLY_TO_NEGATIVE", "VITE_DEFAULT_REPLY_TO_NEGATIVE"],
  ["REPLY_TO_NEUTRAL", "VITE_DEFAULT_REPLY_TO_NEUTRAL"],
  ["REPLY_TO_QUESTIONS", "VITE_DEFAULT_REPLY_TO_QUESTIONS"],
  ["REPLY_TO_SUGGESTIONS", "VITE_DEFAULT_REPLY_TO_SUGGESTIONS"],
  ["REPLY_TO_SPAM", "VITE_DEFAULT_REPLY_TO_SPAM"],
  ["EMAIL_REPORTS", "VITE_DEFAULT_EMAIL_REPORTS"],
  ["GMAIL_DEFAULT_RECIPIENT", "VITE_DEFAULT_EMAIL_RECIPIENT"],
];

function mirrorBackendEnvDefaults(env: Record<string, string>) {
  for (const [backendKey, viteKey] of BACKEND_TO_VITE_DEFAULT) {
    const backendValue = env[backendKey]?.trim();
    const viteValue = env[viteKey]?.trim();
    if (!viteValue && backendValue) {
      env[viteKey] = backendValue;
      process.env[viteKey] = backendValue;
    }
  }

  const langgraphPort = env.LANGGRAPH_PORT?.trim() || "2024";
  if (!env.VITE_LANGGRAPH_API_URL?.trim()) {
    const apiUrl = `http://127.0.0.1:${langgraphPort}`;
    env.VITE_LANGGRAPH_API_URL = apiUrl;
    process.env.VITE_LANGGRAPH_API_URL = apiUrl;
  }
  if (!env.VITE_LANGGRAPH_PORT?.trim()) {
    env.VITE_LANGGRAPH_PORT = langgraphPort;
    process.env.VITE_LANGGRAPH_PORT = langgraphPort;
  }

  const browserApiPort = env.BROWSER_API_PORT?.trim() || "2025";
  if (!env.VITE_BROWSER_API_URL?.trim()) {
    const browserApiUrl = `http://127.0.0.1:${browserApiPort}`;
    env.VITE_BROWSER_API_URL = browserApiUrl;
    process.env.VITE_BROWSER_API_URL = browserApiUrl;
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, rootDir, "");
  mirrorBackendEnvDefaults(env);
  const langgraphPort = env.LANGGRAPH_PORT || "2024";
  const browserApiPort = env.BROWSER_API_PORT || "2025";
  const frontendPort = Number(env.FRONTEND_PORT || "5173");

  return {
    envDir: rootDir,
    plugins: [react()],
    server: {
      port: frontendPort,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${langgraphPort}`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
        "/browser-api": {
          target: `http://127.0.0.1:${browserApiPort}`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/browser-api/, ""),
        },
      },
    },
    preview: {
      port: frontendPort,
    },
  };
});
