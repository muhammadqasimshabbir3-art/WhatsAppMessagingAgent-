/**
 * Local / deployed connection settings.
 *
 * Local dev (root .env via Vite envDir):
 *   VITE_LANGGRAPH_API_URL=http://127.0.0.1:2024
 *
 * Vercel production — set in Project → Environment Variables:
 *   VITE_LANGGRAPH_API_URL=https://<your-northflank-service-public-url>
 */

function readApiUrl(): string {
  const candidates = [
    import.meta.env.VITE_LANGGRAPH_API_URL,
    import.meta.env.VITE_API_URL,
    import.meta.env.NEXT_PUBLIC_API_URL,
  ];
  for (const value of candidates) {
    const trimmed = value?.trim();
    if (trimmed) return trimmed;
  }
  return "";
}

function normalizeApiBase(raw: string): string {
  const trimmed = raw.trim().replace(/\/$/, "");
  if (!trimmed) return "";

  try {
    const parsed = new URL(trimmed);
    return `${parsed.origin}${parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "")}`;
  } catch {
    if (typeof window !== "undefined" && window.location?.origin) {
      return new URL(trimmed, window.location.origin).href.replace(/\/$/, "");
    }
  }
  return "";
}

function resolveLangGraphApiUrl(): string {
  const fromEnv = normalizeApiBase(readApiUrl());
  if (fromEnv) return fromEnv;

  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}/api`;
  }

  const port = import.meta.env.VITE_LANGGRAPH_PORT?.trim() || "2024";
  return `http://127.0.0.1:${port}`;
}

export const LANGGRAPH_API_URL = resolveLangGraphApiUrl();

export const ASSISTANT_ID =
  import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID?.trim() || "agent";

export const UI_URL =
  import.meta.env.VITE_UI_URL?.trim() || "http://localhost:5173";

export const GRAPH_RUN_CONFIG = { recursion_limit: 100 };

function resolveBrowserApiUrl(): string {
  const fromEnv = import.meta.env.VITE_BROWSER_API_URL?.trim();
  if (fromEnv) {
    try {
      const parsed = new URL(fromEnv);
      return `${parsed.origin}${parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "")}`;
    } catch {
      return fromEnv.replace(/\/$/, "");
    }
  }

  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}/browser-api`;
  }

  return "http://127.0.0.1:2025";
}

export const BROWSER_API_URL = resolveBrowserApiUrl();
