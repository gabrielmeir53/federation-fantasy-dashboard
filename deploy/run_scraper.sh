#!/bin/bash
# ============================================================
# Federation Dashboard Scraper — Cron Wrapper
# ============================================================
# This script is called by cPanel cron job and by trigger.php.
# It activates the Python virtualenv, runs the scraper, and
# copies output to the public web directory.
#
# SETUP: Change USERNAME below to your cPanel username.
#        Change PYTHON_VERSION if your Python app uses a different version.
#        Change DOMAIN_DIR to match your domain folder name.
# ============================================================

# ── CONFIGURATION ──────────────────────────────────────────
USERNAME="YOUR_CPANEL_USERNAME"
PYTHON_VERSION="3.9"                      # ← Match your cPanel Python app version
DOMAIN_DIR="yourdomain.com"               # ← Site root folder for this domain
# ──────────────────────────────────────────────────────────

# Derived paths (don't change unless your layout differs)
HOME_DIR="/home/${USERNAME}"
SCRAPER_DIR="${HOME_DIR}/scraper"
VENV_PYTHON="${HOME_DIR}/virtualenv/scraper/${PYTHON_VERSION}/bin/python"
OUTPUT_DIR="${HOME_DIR}/${DOMAIN_DIR}/data"
LOG_FILE="${SCRAPER_DIR}/cron.log"
LOCK_FILE="${SCRAPER_DIR}/.scraper.lock"

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
trap "rm -f $LOCK_FILE" EXIT

# ── LOG ROTATION (keep last 5000 lines) ──────────────────
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE" 2>/dev/null)" -gt 5000 ]; then
    tail -2000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    echo "[$(date)] Log rotated." >> "$LOG_FILE"
fi

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
"$VENV_PYTHON" scrape_fantrax.py --verbose --output-dir "$OUTPUT_DIR"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "[$(date)] Scraper completed successfully."

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
    echo "[$(date)] Scraper failed with exit code: $EXIT_CODE"
fi

echo "================================================================"
echo ""
