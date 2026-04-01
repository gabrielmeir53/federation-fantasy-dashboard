#!/bin/bash
# ============================================================
# Federation Scraper — Cron Wrapper
# ============================================================
# This script is called by cPanel cron job and by trigger.php.
# It activates the Python virtualenv, runs the scraper, and
# copies output to the public web directory.
#
# SETUP: Change USERNAME below to your cPanel username.
#        Change PYTHON_VERSION if your Python app uses a different version.
# ============================================================

# ── CONFIGURATION ──────────────────────────────────────────
USERNAME="YOUR_CPANEL_USERNAME"
PYTHON_VERSION="3.9"                      # ← Match your cPanel Python app version
DOMAIN_DIR="yourdomain.com"                # ← Site root folder for this domain
# ── EMAIL NOTIFICATION ─────────────────────────────────────
EMAIL_TO="your@email.com"
EMAIL_FROM="scraper@yourdomain.com"   # ← Workspace alias shown as From address
GMAIL_USER="your@email.com"                          # ← Your Workspace login (set on server, don't commit)
GMAIL_APP_PASSWORD="YOUR_GMAIL_APP_PASSWORD"                  # ← Gmail App Password, 16 chars (set on server, don't commit)
# ──────────────────────────────────────────────────────────

# Derived paths (don't change unless your layout differs)
HOME_DIR="/home/${USERNAME}"
SCRAPER_DIR="${HOME_DIR}/repo/scraper"
VENV_PYTHON="${HOME_DIR}/virtualenv/scraper/${PYTHON_VERSION}/bin/python"
OUTPUT_DIR="${HOME_DIR}/${DOMAIN_DIR}/data"
LOG_FILE="${SCRAPER_DIR}/cron.log"
LOCK_FILE="${SCRAPER_DIR}/.scraper.lock"
TEMP_LOG="${SCRAPER_DIR}/.scraper_run_$$.tmp"

# ── LOCK (prevent overlapping runs) ───────────────────────
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
    if [ "$LOCK_AGE" -lt 600 ]; then
        echo "[$(date)] Scraper already running (lock age: ${LOCK_AGE}s). Exiting."
        exit 0
    else
        echo "[$(date)] Stale lock detected (${LOCK_AGE}s old). Removing."
        rm -f "$LOCK_FILE"
    fi
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE $TEMP_LOG" EXIT

# ── LOG ROTATION (keep last 5000 lines) ──────────────────
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE" 2>/dev/null)" -gt 5000 ]; then
    tail -2000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    echo "[$(date)] Log rotated." >> "$LOG_FILE"
fi

# ── EMAIL NOTIFICATION FUNCTION ───────────────────────────
send_notification() {
    local exit_code="$1"
    local temp_log="$2"
    local run_date
    run_date=$(date '+%Y-%m-%d %H:%M')

    local leagues_ok leagues_failed total_players errors tx_line json_size
    leagues_ok=$(grep -c "ACTIVE\|NOT STARTED" "$temp_log" 2>/dev/null || echo 0)
    leagues_failed=$(grep -cE "Failed:" "$temp_log" 2>/dev/null || echo 0)
    total_players=$(grep -E "(ACTIVE|NOT STARTED).*players" "$temp_log" 2>/dev/null \
        | grep -oE '[0-9]+ players' | awk '{s+=$1} END {print s+0}')
    errors=$(grep -cE "ERROR:|Failed:" "$temp_log" 2>/dev/null || echo 0)
    tx_line=$(grep "transactions saved" "$temp_log" 2>/dev/null | tail -1 | sed 's/^[[:space:]]*//')
    json_size=""
    if [ -f "${OUTPUT_DIR}/fed_combined.json" ]; then
        json_size=$(du -h "${OUTPUT_DIR}/fed_combined.json" | cut -f1)
    fi

    local status_word subject
    if [ "$exit_code" -eq 0 ]; then
        status_word="OK"
        subject="[Federation] Scraper OK -- ${run_date} | ${leagues_ok}/4 leagues, ${total_players} players"
    else
        status_word="FAILED (exit ${exit_code})"
        subject="[Federation] Scraper FAILED -- ${run_date} | exit ${exit_code}, ${errors} errors"
    fi

    # Skip if credentials not set
    if [ -z "$GMAIL_USER" ] || [ -z "$GMAIL_APP_PASSWORD" ]; then
        echo "[$(date)] Email skipped: GMAIL_USER or GMAIL_APP_PASSWORD not set in run_scraper.sh."
        return
    fi

    # Pass all values as env vars so special characters can't break Python syntax
    FED_GMAIL_USER="$GMAIL_USER" \
    FED_GMAIL_PASS="$GMAIL_APP_PASSWORD" \
    FED_EMAIL_TO="$EMAIL_TO" \
    FED_EMAIL_FROM="$EMAIL_FROM" \
    FED_SUBJECT="$subject" \
    FED_RUN_DATE="$run_date" \
    FED_STATUS="$status_word" \
    FED_LEAGUES_OK="$leagues_ok" \
    FED_LEAGUES_FAILED="$leagues_failed" \
    FED_PLAYERS="$total_players" \
    FED_ERRORS="$errors" \
    FED_JSON_SIZE="${json_size:-n/a}" \
    FED_TX_LINE="${tx_line:-n/a}" \
    FED_TEMP_LOG="$temp_log" \
    "$VENV_PYTHON" - <<'PYEOF'
import smtplib, sys, os
from email.mime.text import MIMEText

e = os.environ
gmail_user = e['FED_GMAIL_USER']
gmail_pass = e['FED_GMAIL_PASS']
to_addr    = e['FED_EMAIL_TO']
from_addr  = e['FED_EMAIL_FROM']
subject    = e['FED_SUBJECT']
run_date   = e['FED_RUN_DATE']
status     = e['FED_STATUS']
leagues_ok = e['FED_LEAGUES_OK']
leagues_failed = e['FED_LEAGUES_FAILED']
total_players  = e['FED_PLAYERS']
errors     = e['FED_ERRORS']
json_size  = e['FED_JSON_SIZE']
tx_line    = e['FED_TX_LINE']
temp_log   = e['FED_TEMP_LOG']

try:
    with open(temp_log, "r", errors="replace") as f:
        log_content = f.read()
except Exception as ex:
    log_content = f"(could not read log: {ex})"

body = f"""================================================================
  Federation Scraper Notification -- {run_date}
================================================================
  Status        : {status}
  Leagues OK    : {leagues_ok} / 4
  Leagues Failed: {leagues_failed}
  Total Players : {total_players}
  Errors        : {errors}
  JSON Output   : {json_size}
  Transactions  : {tx_line}
================================================================

--- FULL RUN LOG ---

{log_content}

--- END OF LOG ---"""

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = subject
msg["From"]    = from_addr
msg["To"]      = to_addr

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)
    print("Email sent.")
except Exception as ex:
    print(f"Email failed: {ex}", file=sys.stderr)
    sys.exit(1)
PYEOF

    local py_rc=$?
    if [ $py_rc -ne 0 ]; then
        echo "[$(date)] WARNING: Email send failed (see above)."
    else
        echo "[$(date)] Email sent to ${EMAIL_TO}"
    fi
}

# ── RUN ───────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  Federation Scraper Run — $(date)"
echo "================================================================"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"
mkdir -p "${SCRAPER_DIR}/data"

# Check Python exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[ERROR] Python not found at: $VENV_PYTHON"
    echo "  Check PYTHON_VERSION and that the Python app is set up in cPanel."
    exit 1
fi

# Run scraper
cd "$SCRAPER_DIR"
"$VENV_PYTHON" scrape_fantrax.py --verbose --output-dir "$OUTPUT_DIR" 2>&1 | tee "$TEMP_LOG"
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "[$(date)] ✅ Scraper completed successfully."

    # Show output file info
    if [ -f "${OUTPUT_DIR}/fed_combined.json" ]; then
        SIZE=$(du -h "${OUTPUT_DIR}/fed_combined.json" | cut -f1)
        echo "  Output: ${OUTPUT_DIR}/fed_combined.json (${SIZE})"
    fi

    # Also keep individual league JSONs in scraper/data for backup
    for f in "${OUTPUT_DIR}/fed_fl.json" "${OUTPUT_DIR}/fed_ba.json" "${OUTPUT_DIR}/fed_hl.json" "${OUTPUT_DIR}/fed_lb.json"; do
        [ -f "$f" ] && cp "$f" "${SCRAPER_DIR}/data/" 2>/dev/null
    done
else
    echo ""
    echo "[$(date)] ❌ Scraper failed with exit code: $EXIT_CODE"
fi

echo "================================================================"
echo ""
send_notification "$EXIT_CODE" "$TEMP_LOG"
