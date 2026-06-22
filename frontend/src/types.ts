export type StepStatus = "pending" | "running" | "completed" | "skipped" | "error";

export type WorkflowAction = "analyze" | "report" | "email";

export interface WorkflowStep {
  id: string;
  nodes: string[];
  label: string;
  description: string;
  optional?: boolean;
  emoji?: string;
}

export interface StepState {
  id: string;
  status: StepStatus;
  startedAt?: string;
  completedAt?: string;
  detail?: string;
}

export interface MessageRow {
  author?: string;
  contact_name?: string;
  text?: string;
  category?: string;
  engagement_priority?: string;
  sentiment_score?: number | string;
  timestamp?: string;
  replied?: boolean;
  reply_text?: string;
  posted?: boolean;
  post_error?: string;
  is_outgoing?: boolean;
  message_id?: string;
  screenshot_path?: string;
}

export interface ConversationRow {
  contact_name?: string;
  preview?: string;
  last_seen?: string;
  is_unread?: boolean;
  inbound_messages?: MessageRow[];
}

export interface AgentState {
  contact_filter?: string;
  conversations?: ConversationRow[];
  screenshots?: Array<Record<string, unknown>>;
  chats_scanned?: number;
  unread_chats_found?: number;
  read_chats_found?: number;
  gmail_logged_in?: boolean;
  whatsapp_logged_in?: boolean;
  login_detail?: string;
  chat_messages?: MessageRow[];
  analyzed_messages?: MessageRow[];
  positive_messages?: MessageRow[];
  negative_messages?: MessageRow[];
  neutral_messages?: MessageRow[];
  question_messages?: MessageRow[];
  suggestion_messages?: MessageRow[];
  spam_messages?: MessageRow[];
  unanswered_messages?: MessageRow[];
  reply_targets?: MessageRow[];
  generated_replies?: MessageRow[];
  failed_replies?: MessageRow[];
  reply_statistics?: Record<string, number>;
  reply_history?: Array<Record<string, unknown>>;
  pdf_path?: string;
  html_path?: string;
  llm_summary?: string;
  task_plan_summary?: string;
  agent_route?: string;
  logged_in?: boolean;
  whatsapp_login_detail?: string;
  inbound_messages_count?: number;
  email_result?: string;
  messages?: Array<{ content?: string; type?: string }>;
}

export interface LogEntry {
  id: string;
  time: string;
  level: "info" | "success" | "warn" | "error";
  message: string;
}

export interface RunRequest {
  contactFilter: string;
  maxChatsToProcess: number;
  maxMessagesPerChat: number;
  maxReplies: number;
  replyPersonality: string;
  enableMessageReplies: boolean;
  replyOnlyUnreadChats: boolean;
  keepBrowserOpen: boolean;
  replyToPositive: boolean;
  replyToNegative: boolean;
  replyToNeutral: boolean;
  replyToQuestions: boolean;
  replyToSuggestions: boolean;
  replyToSpam: boolean;
  emailReports: boolean;
  emailRecipient: string;
}

export type AgentRunSettings = Omit<RunRequest, never>;
