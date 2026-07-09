#!/bin/bash
# Open the reusable WhatsApp browser profile that the agent can attach to.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_DIR"

# shellcheck source=scripts/services.sh
source "${PROJECT_DIR}/scripts/services.sh"

if [ -f ".env" ]; then
    set -a
    load_dotenv ".env"
    set +a
fi

BROWSER_PROFILE_PATH="${BROWSER_PROFILE_PATH:-./data/chrome_profile}"
BROWSER_DEBUG_PORT="${BROWSER_DEBUG_PORT:-9222}"
WHATSAPP_URL="https://web.whatsapp.com/"

case "$BROWSER_PROFILE_PATH" in
    /*) PROFILE_PATH="$BROWSER_PROFILE_PATH" ;;
    *) PROFILE_PATH="${PROJECT_DIR}/${BROWSER_PROFILE_PATH}" ;;
esac

mkdir -p "$PROFILE_PATH"

find_chrome() {
    if [ "${BROWSER_CHANNEL:-}" = "chrome" ]; then
        for candidate in google-chrome google-chrome-stable; do
            if command -v "$candidate" >/dev/null 2>&1; then
                echo "$candidate"
                return 0
            fi
        done
    fi

    for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
        if command -v "$candidate" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

CHROME_BIN="$(find_chrome || true)"
if [ -z "$CHROME_BIN" ]; then
    echo "Could not find Chrome/Chromium. Install Chrome or set BROWSER_CHANNEL=chrome."
    exit 1
fi

if command -v curl >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:${BROWSER_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
    echo "Reusable browser is already running on debug port ${BROWSER_DEBUG_PORT}."
    echo "Open ${WHATSAPP_URL} in that browser window if it is not already open."
    exit 0
fi

echo "Opening reusable WhatsApp browser:"
echo "  Profile: ${PROFILE_PATH}"
echo "  Debug:   ${BROWSER_DEBUG_PORT}"
echo "  URL:     ${WHATSAPP_URL}"

nohup "$CHROME_BIN" \
    --remote-debugging-port="${BROWSER_DEBUG_PORT}" \
    --user-data-dir="${PROFILE_PATH}" \
    --disable-blink-features=AutomationControlled \
    "${WHATSAPP_URL}" >/tmp/whatsapp-agent-browser.log 2>&1 &

echo "Browser started. Scan WhatsApp QR once in this window — later runs reuse the saved profile."
