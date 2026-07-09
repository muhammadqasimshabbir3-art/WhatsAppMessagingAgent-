# WhatsApp Messaging Agent

**A LangGraph agent that scans your WhatsApp Web inbox, reads unread conversations, generates contextual AI replies, sends them, and emails an HTML report.**

The agent uses a **persistent Chrome profile** (`BROWSER_PROFILE_PATH`) so WhatsApp Web stays logged in after you scan the QR code once. It processes **unread** chats, generates Groq AI replies, sends them through WhatsApp Web, captures screenshots, and emails an HTML report via Gmail SMTP.

## Quick start

```bash
./setup.sh
cp .env.example .env
# Edit .env: GROQ_API_KEY, BROWSER_PROFILE_PATH, optional Gmail SMTP for email reports
./start.sh browser
./start.sh both
```

Open **http://localhost:5173** and click **Start Agent**.

### First-time WhatsApp Web login

Set in `.env`:

```env
BROWSER_PROFILE_PATH=./data/chrome_profile
BROWSER_CHANNEL=chrome
BROWSER_HEADLESS=false
KEEP_BROWSER_OPEN=true
BROWSER_DEBUG_PORT=9222
```

Open the reusable browser first:

```bash
./start.sh browser
```

Chrome opens at [web.whatsapp.com](https://web.whatsapp.com/) using `./data/chrome_profile` and remote debugging port `9222`. Scan the QR code **once**, then leave that browser window open. Later agent runs attach to that same browser/profile, reuse the open WhatsApp Web session, and send replies there.

If you opened normal Chrome manually, the agent cannot attach to it unless Chrome was started with `--remote-debugging-port=9222` and the same `--user-data-dir`. Use `./start.sh browser` for the reliable reusable window.

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
| `BROWSER_DEBUG_PORT` | `9222` | Remote debugging port used to attach to the already-open reusable browser |
| `MAX_CHATS_TO_PROCESS` | `5` | Max unread chats to open per run |
| `MAX_MESSAGES_PER_CHAT` | `10` | Last N messages per chat used as reply context |
| `MAX_REPLIES_PER_RUN` | `5` | Max AI replies per run |
| `REPLY_ONLY_UNREAD_CHATS` | `true` | Reply only to chats with unread messages |
| `CONTACT_FILTER` | — | Optional name filter (partial match) |
| `ENABLE_MESSAGE_REPLIES` | `false` | Send replies via WhatsApp Web |

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
| `./start.sh browser` | Open the reusable WhatsApp Chrome profile the agent can attach to |
| `./start.sh both` | LangGraph server + React UI |
| `./start.sh server` | LangGraph API only |
| `./start.sh ui` | Frontend only |

## Production (Vercel UI + Fly.io backend)

**Yes, the agent works in production** — you do not need a browser embedded in the UI.

| Layer | Role | Browser needed? |
|-------|------|-----------------|
| **Vercel** | Hosts the React dashboard only | No |
| **Fly.io** | Runs LangGraph + Playwright (headless) | Yes — uses saved Chrome profile |

### One-time WhatsApp login (any of these)

1. **Local (simplest):** run `./start.sh browser`, scan QR once, then copy `./data/chrome_profile` to the Fly volume at `/data/chrome_profile`.
2. **On the server:** `fly ssh console`, then run the same browser launcher once if the machine has Chrome/display access.

After that, set `BROWSER_HEADLESS=true` on Fly. Every agent run reuses the profile — no QR scan, no visible window, no UI browser.

The **“Open WhatsApp browser”** button in the UI only works when the Browser API runs on your **local machine** (via `./start.sh both`). In production on Vercel, users trigger the agent; WhatsApp auth is already on the backend from the one-time setup above.

```bash
# Create persistent volume (once)
fly volumes create whatsapp_profile --region iad --size 1

# After local QR scan, upload profile (example)
fly ssh sftp shell
# put -r ./data/chrome_profile /data/chrome_profile
```

## License

MIT
