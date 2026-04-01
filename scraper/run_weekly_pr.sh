#!/bin/bash
# ── Federation Weekly Power Rankings Email ──────────────────────────
# Runs every Tuesday at 6am ET via cron.
# Uses the same Gmail credentials as run_scraper.sh.
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="${HOME}/virtualenv/scraper/3.9/bin/python"
OUTPUT_DIR="${HOME}/yourdomain.com/data"

# Gmail credentials (same as run_scraper.sh)
GMAIL_USER="your@email.com"
GMAIL_APP_PASSWORD="YOUR_GMAIL_APP_PASSWORD"
EMAIL_FROM="scraper@yourdomain.com"

echo "[$(date)] Starting weekly PR email..."

FED_GMAIL_USER="$GMAIL_USER" \
FED_GMAIL_PASS="$GMAIL_APP_PASSWORD" \
FED_EMAIL_FROM="$EMAIL_FROM" \
FED_OUTPUT_DIR="$OUTPUT_DIR" \
"$VENV_PYTHON" "$SCRIPT_DIR/send_weekly_pr.py"

echo "[$(date)] Done (exit $?)."
