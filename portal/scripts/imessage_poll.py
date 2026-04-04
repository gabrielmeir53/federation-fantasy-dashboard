#!/usr/bin/env python3
"""
iMessage Trade Announcer
Polls the federation portal API for approved trades and sends iMessage announcements
via AppleScript. Run on your Mac via launchd or cron.

Usage:
    python imessage_poll.py

Environment:
    YSF_IMESSAGE_API_KEY  - API key matching IMESSAGE_API_KEY in config.php
    YSF_IMESSAGE_GROUP    - iMessage group chat name (e.g. "League Owners")
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

API_URL = "https://yourdomain.com/portal/api/trade_imessage.php"
API_KEY = os.environ.get("YSF_IMESSAGE_API_KEY", "")
GROUP_CHAT = os.environ.get("YSF_IMESSAGE_GROUP", "League Owners")
POLL_INTERVAL = 60  # seconds


def send_imessage(message: str, group: str) -> bool:
    """Send an iMessage to a group chat via AppleScript."""
    script = f'''
    tell application "Messages"
        set targetChat to a reference to chat "{group}"
        send "{message}" to targetChat
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"AppleScript error: {e.stderr.decode()}", file=sys.stderr)
        return False


def mark_sent(trade_id: int) -> None:
    """Tell the API this trade's iMessage has been sent."""
    data = json.dumps({"trade_id": trade_id}).encode()
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "X-Api-Key": API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)


def poll() -> None:
    """Fetch unsent trades and announce them."""
    req = urllib.request.Request(
        f"{API_URL}?key={API_KEY}",
        headers={"X-Api-Key": API_KEY},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read())
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        return

    for trade in body.get("trades", []):
        tid = trade["trade_id"]
        summary = trade["summary"]
        msg = f"Trade #{tid} Approved\\n\\n{summary}"
        # Escape quotes for AppleScript
        msg = msg.replace('"', '\\"')

        print(f"Sending iMessage for trade #{tid}...")
        if send_imessage(msg, GROUP_CHAT):
            mark_sent(tid)
            print(f"  Sent and marked trade #{tid}.")
        else:
            print(f"  Failed to send iMessage for trade #{tid}.")


def main():
    if not API_KEY:
        print("Set YSF_IMESSAGE_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    print(f"Polling {API_URL} every {POLL_INTERVAL}s for group '{GROUP_CHAT}'...")
    while True:
        poll()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
