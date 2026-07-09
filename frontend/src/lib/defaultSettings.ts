import type { AgentRunSettings } from "../types";

function envBool(key: string, fallback: boolean): boolean {
  const raw = import.meta.env[key];
  if (raw == null || String(raw).trim() === "") return fallback;
  const value = String(raw).trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(value);
}

function envInt(key: string, fallback: number): number {
  const raw = import.meta.env[key];
  if (raw == null || String(raw).trim() === "") return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function envStr(key: string, fallback: string): string {
  const raw = import.meta.env[key];
  return raw != null && String(raw).trim() !== "" ? String(raw).trim() : fallback;
}

export function defaultRunSettings(): AgentRunSettings {
  return {
    contactFilter: envStr("VITE_DEFAULT_CONTACT_FILTER", ""),
    maxChatsToProcess: envInt("VITE_DEFAULT_MAX_CHATS_TO_PROCESS", 5),
    maxMessagesPerChat: envInt("VITE_DEFAULT_MAX_MESSAGES_PER_CHAT", 10),
    maxReplies: envInt("VITE_DEFAULT_MAX_REPLIES", 5),
    replyPersonality: envStr("VITE_DEFAULT_REPLY_PERSONALITY", "friendly"),
    enableMessageReplies: envBool("VITE_DEFAULT_ENABLE_MESSAGE_REPLIES", true),
    replyOnlyUnreadChats: envBool("VITE_DEFAULT_REPLY_ONLY_UNREAD_CHATS", true),
    keepBrowserOpen: envBool("VITE_DEFAULT_KEEP_BROWSER_OPEN", true),
    replyToPositive: envBool("VITE_DEFAULT_REPLY_TO_POSITIVE", true),
    replyToNegative: envBool("VITE_DEFAULT_REPLY_TO_NEGATIVE", true),
    replyToNeutral: envBool("VITE_DEFAULT_REPLY_TO_NEUTRAL", true),
    replyToQuestions: envBool("VITE_DEFAULT_REPLY_TO_QUESTIONS", true),
    replyToSuggestions: envBool("VITE_DEFAULT_REPLY_TO_SUGGESTIONS", true),
    replyToSpam: envBool("VITE_DEFAULT_REPLY_TO_SPAM", false),
    emailReports: envBool("VITE_DEFAULT_EMAIL_REPORTS", true),
    emailRecipient:
      envStr("VITE_DEFAULT_EMAIL_RECIPIENT", "") ||
      envStr("VITE_GMAIL_DEFAULT_RECIPIENT", ""),
  };
}

export const REPLY_PERSONALITY_OPTIONS = [
  "friendly",
  "humorous",
  "professional",
  "enthusiastic",
] as const;
