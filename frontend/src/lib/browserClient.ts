import { BROWSER_API_URL } from "../config";

export interface AccountInfo {
  email: string;
  configured: boolean;
}

export interface BrowserStatus {
  active: boolean;
  logged_in: boolean;
  needs_qr: boolean;
  browser_running?: boolean;
  profile_path?: string;
  url?: string;
  error?: string;
  message?: string;
  mode?: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function fetchAccountInfo(): Promise<AccountInfo> {
  const response = await fetch(`${BROWSER_API_URL}/account`);
  return parseJson<AccountInfo>(response);
}

export async function fetchBrowserStatus(): Promise<BrowserStatus> {
  const response = await fetch(`${BROWSER_API_URL}/browser/status`);
  return parseJson<BrowserStatus>(response);
}

export async function setupBrowser(): Promise<BrowserStatus> {
  const response = await fetch(`${BROWSER_API_URL}/browser/setup`, { method: "POST" });
  return parseJson<BrowserStatus>(response);
}
