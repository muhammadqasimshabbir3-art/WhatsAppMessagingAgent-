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

## Production (Vercel UI + Northflank backend)

**Yes, the agent works in production** — you do not need a browser embedded in the UI. This repo uses **Northflank** for the backend (no credit card required on the free Developer Sandbox) and **Vercel** for the dashboard.

| Layer | Role | Browser needed? |
|-------|------|-----------------|
| **Vercel** | Hosts the React dashboard only | No |
| **Northflank** | Runs LangGraph + Playwright (headless) | Yes — uses saved Chrome profile on a volume |

Your Northflank project: [whatsappmessagingagent](https://app.northflank.com/t/muhammadqasimshabbir3s-team/project/whatsappmessagingagent)

### 1. Deploy the backend on Northflank

**Option A — UI (recommended first time)**

Open [whatsappmessagingagent](https://app.northflank.com/t/muhammadqasimshabbir3s-team/project/whatsappmessagingagent) → **Create service** → **Combined**, then fill:

| Field | Value |
|-------|--------|
| Name | `whatsapp-agent-api` |
| Repository | `muhammadqasimshabbir3-art/WhatsAppMessagingAgent-` |
| Branch | `main` |
| Build type | **Dockerfile** |
| Dockerfile path | `/Dockerfile` |
| Build context | `/` |
| Port | **8000**, protocol **HTTP**, **public** |
| Volume | name `whatsapp-chrome-profile`, mount **`/data`**, ~2 GB, ReadWriteOnce |
| Shared memory (`shm`) | **256 MB** or higher if the UI allows |
| Compute | highest RAM on free tier (Chromium often needs ≥1 GB) |

**Runtime env / secrets** (from `northflank.env.example`):

```env
GROQ_API_KEY=your_key
PORT=8000
BROWSER_HEADLESS=true
BROWSER_PROFILE_PATH=/data/chrome_profile
KEEP_BROWSER_OPEN=true
ENABLE_MESSAGE_REPLIES=false
```

Create the service → wait for build → copy the public HTTPS URL from **Ports & DNS**.

**Option B — Template**

Repo file [`northflank.json`](./northflank.json) defines the same Combined service + volume. In Northflank: **Templates** → create/import → point GitOps at `/northflank.json` → set argument override `GROQ_API_KEY` → **Run**.

Docs: [Build and deploy](https://northflank.com/docs/v1/application/getting-started/build-and-deploy-your-code), [Volumes](https://northflank.com/docs/v1/application/databases-and-persistence/add-a-volume), [Templates](https://northflank.com/docs/v1/application/infrastructure-as-code/write-a-template).

### 2. One-time WhatsApp login (local → upload profile)

1. Locally: set `BROWSER_HEADLESS=false`, run `./start.sh browser`, scan the QR once.
2. Upload `./data/chrome_profile` onto the Northflank volume at `/data/chrome_profile`.

Easiest upload (after [Northflank CLI](https://northflank.com/docs/v1/api/copy-files) login):

```bash
# Replace project/service ids with yours from the Northflank dashboard
northflank upload service file \
  --projectId whatsappmessagingagent \
  --service <your-backend-service-name> \
  --localPath ./data/chrome_profile \
  --remotePath /data/chrome_profile
```

Or use the service **Shell** / SSH proxy and `scp`/`rsync` — see [transfer data](https://northflank.com/docs/v1/application/run/transfer-data-to-and-from-containers) and [SSH access](https://northflank.com/docs/v1/application/run/access-services-with-ssh).

After the profile is on the volume, keep `BROWSER_HEADLESS=true`. Agent runs reuse the session — no QR in the UI.

### 3. Deploy the frontend on Vercel

1. Import the `frontend/` folder (or monorepo root with Root Directory = `frontend`).
2. Set environment variables (see `frontend/.env.example`):

```env
VITE_LANGGRAPH_API_URL=https://<your-northflank-public-url>
VITE_LANGGRAPH_ASSISTANT_ID=agent
VITE_UI_URL=https://<your-vercel-app>.vercel.app
```

3. Deploy. Open the Vercel URL and click **Start Agent**.

The **“Open WhatsApp browser”** button only works with the local Browser API (`./start.sh both`). On Vercel, auth comes from the Northflank Chrome profile you uploaded once.

### Free-tier notes

- Northflank [Developer Sandbox](https://northflank.com/pricing) can run without a card; compute is limited.
- If the service crashes or Playwright OOMs, try a larger compute plan or demo locally with `./start.sh both`.
- Volume storage / egress may still have usage costs outside pure free allowances — check Northflank billing for your plan.
- WhatsApp Web sessions can expire; re-scan QR locally and re-upload the profile when that happens.

## License

MIT
