/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LANGGRAPH_API_URL?: string;
  readonly VITE_LANGGRAPH_ASSISTANT_ID?: string;
  readonly VITE_UI_URL?: string;
  readonly VITE_API_URL?: string;
  readonly NEXT_PUBLIC_API_URL?: string;
  readonly VITE_DEFAULT_CONTACT_FILTER?: string;
  readonly VITE_DEFAULT_MAX_CHATS_TO_PROCESS?: string;
  readonly VITE_DEFAULT_MAX_MESSAGES_PER_CHAT?: string;
  readonly VITE_DEFAULT_MAX_REPLIES?: string;
  readonly VITE_DEFAULT_REPLY_PERSONALITY?: string;
  readonly VITE_DEFAULT_ENABLE_MESSAGE_REPLIES?: string;
  readonly VITE_DEFAULT_REPLY_ONLY_READ_CHATS?: string;
  readonly VITE_DEFAULT_KEEP_BROWSER_OPEN?: string;
  readonly VITE_DEFAULT_REPLY_TO_POSITIVE?: string;
  readonly VITE_DEFAULT_REPLY_TO_NEGATIVE?: string;
  readonly VITE_DEFAULT_REPLY_TO_NEUTRAL?: string;
  readonly VITE_DEFAULT_REPLY_TO_QUESTIONS?: string;
  readonly VITE_DEFAULT_REPLY_TO_SUGGESTIONS?: string;
  readonly VITE_DEFAULT_REPLY_TO_SPAM?: string;
  readonly VITE_DEFAULT_EMAIL_REPORTS?: string;
  readonly VITE_DEFAULT_EMAIL_RECIPIENT?: string;
  readonly VITE_GMAIL_DEFAULT_RECIPIENT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
