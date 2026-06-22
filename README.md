# WhatsApp Messaging Agent

**A LangGraph agent that scans your WhatsApp Web inbox, reads unread conversations, generates contextual AI replies, sends them, and emails an HTML report.**

The agent uses a **persistent Chrome profile** (`BROWSER_PROFILE_PATH`) so WhatsApp Web stays logged in after you scan the QR code once. It processes **unread** chats, generates Groq AI replies, sends them through WhatsApp Web, captures screenshots, and emails an HTML report via Gmail SMTP.

## Quick start

```bash
./setup.sh
cp .env.example .env
# Edit .env: GROQ_API_KEY, BROWSER_PROFILE_PATH, optional Gmail SMTP for email reports
./start.sh both
```

Open **http://localhost:5173** and click **Start Agent**.

### First-time WhatsApp Web login

Set in `.env`:

```env
BROWSER_PROFILE_PATH=./data/chrome_profile
BROWSER_CHANNEL=chrome
BROWSER_HEADLESS=false
```

Run the agent once. Chrome opens at [web.whatsapp.com](https://web.whatsapp.com/) — scan the QR code **once**. The profile is saved in `./data/chrome_profile` and reused on every run (no repeated QR).

## Workflow

```
Chrome profile → WhatsApp Web → Unread chats only → Extract conversations
  → Analyze sentiment → Select reply targets → Generate contextual AI replies
  → Send on WhatsApp + screenshot → HTML report → PDF (optional) → Email
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | — | **Required** — LLM for analysis and replies |
| `BROWSER_PROFILE_PATH` | `./data/chrome_profile` | Persistent Chrome profile (WhatsApp stays logged in) |
| `BROWSER_CHANNEL` | — | Set `chrome` to use installed Google Chrome |
| `BROWSER_HEADLESS` | `true` | Set `false` for first QR scan |
| `KEEP_BROWSER_OPEN` | `true` | Reuse browser through scan and send |
| `MAX_CHATS_TO_PROCESS` | `5` | Max unread chats to open per run |
| `MAX_MESSAGES_PER_CHAT` | `20` | Recent inbound messages per chat |
| `MAX_REPLIES_PER_RUN` | `5` | Max AI replies per run |
| `REPLY_ONLY_UNREAD_CHATS` | `true` | Reply only to chats with unread messages |
| `CONTACT_FILTER` | — | Optional name filter (partial match) |
| `ENABLE_MESSAGE_REPLIES` | `false` | Send replies via WhatsApp Web |
| `BROWSER_HEADLESS` | `true` | Set `false` for QR login |
| `KEEP_BROWSER_OPEN` | `true` | Reuse browser from login through send |

See `.env.example` for the full list.

## Project structure

```
src/agent/
  graph.py              # LangGraph workflow
  config.py             # Environment config
  workflow_executor.py  # Step handlers
  custom_tools/
    browser_tools.py    # WhatsApp Web session
    whatsapp_tools.py   # Inbox scan, read, send, screenshots
frontend/               # React agent dashboard
```

## Run commands

| Command | Description |
|---------|-------------|
| `./start.sh both` | LangGraph server + React UI |
| `./start.sh server` | LangGraph API only |
| `./start.sh ui` | Frontend only |

## License

MIT
