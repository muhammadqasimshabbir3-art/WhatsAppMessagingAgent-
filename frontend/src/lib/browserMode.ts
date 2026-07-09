export const WHATSAPP_WEB_URL = "https://web.whatsapp.com/";

/** True when the UI runs with a local Browser API (localhost dev). */
export function isLocalBrowserApi(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

/** Open WhatsApp Web in a normal browser tab/window (used on Vercel / production UI). */
export function openWhatsAppInNewWindow(): void {
  window.open(WHATSAPP_WEB_URL, "_blank", "noopener,noreferrer");
}
