"""
Federation — Scrape Previous NFL Season Transactions (One-Time, Authenticated)
========================================================================
This league requires authentication. Here's how:

STEP 1: Open this URL in Chrome (make sure you're logged into Fantrax):
        https://www.fantrax.com/fantasy/league/YOUR_PREV_NFL_LEAGUE_ID/home

STEP 2: Press F12 to open DevTools

STEP 3: Click the "Network" tab at the top of DevTools

STEP 4: Refresh the page (Ctrl+R or F5)

STEP 5: In the Network request list, click the very first request
        (it will say "home" or similar)

STEP 6: On the right side, scroll down in the "Headers" section until
        you see "Cookie:" under "Request Headers"

STEP 7: Click on the Cookie value and copy the ENTIRE thing (it's very long)

STEP 8: Create a file called "cookies.txt" in the project root:
        C:\\path\\to\\your\\project\\cookies.txt

STEP 9: Paste the cookie string into that file and save

STEP 10: Run this script:
         cd C:\\path\\to\\your\\project
         set PYTHONIOENCODING=utf-8 && python tools/scrape_prev_nfl_transactions.py

This script merges the prior NFL transactions into the existing
data/transactions_2025-26.json file. It only needs to be run ONCE.
"""

import json, sys, requests
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
COOKIES_FILE = PROJECT_DIR / "cookies.txt"
TX_FILE = DATA_DIR / "transactions_2025-26.json"

LEAGUE_ID = "YOUR_PREV_NFL_LEAGUE_ID"
LEAGUE_KEY = "fed_fl_prev"
SEASON = "2025-26"

TEAM_NAME_MAP = {
    "Bravo United": "team_02", "Alpha FC": "team_01",
    "Charlie SC": "team_03", "Delta Athletic": "team_04",
    "Echo Rangers": "team_05", "Foxtrot City": "team_06",
    "Golf Town": "team_07", "Hotel FC": "team_08",
    "India United": "team_09", "Juliet SC": "team_10",
    "Kilo Athletic": "team_11", "Lima Rovers": "team_12",
    "Alpha FC": "team_01", "Bravo United": "team_02",
    "Charlie SC": "team_03", "Delta Athletic": "team_04",
    "Foxtrot City": "team_06", "Golf Town": "team_07",
    "India United": "team_09", "Lima Rovers": "team_12",
}

FED_TEAMS = {
    "team_01":    {"owner":"Owner 1",       "name":"Alpha FC",         "abbr":"AFC",  "color":"#00333f", "logo":"afc.svg"},
    "team_02":     {"owner":"Owner 2",         "name":"Bravo United",          "abbr":"BRU",  "color":"#004b41", "logo":"bru.svg"},
    "team_03":  {"owner":"Owner 3",  "name":"Charlie SC",        "abbr":"CSC", "color":"#0d00b2", "logo":"csc.svg"},
    "team_04":     {"owner":"Owner 4",        "name":"Delta Athletic",        "abbr":"DAT", "color":"#12e0e5", "logo":"dat.svg"},
    "team_05":      {"owner":"Owner 5",        "name":"Echo Rangers",  "abbr":"ECR",  "color":"#19b9ee", "logo":"ecr.svg"},
    "team_06":     {"owner":"Owner 6",      "name":"Foxtrot City",        "abbr":"FXC", "color":"#036b08", "logo":"fxc.svg"},
    "team_07":     {"owner":"Owner 7",         "name":"Golf Town",     "abbr":"GLT", "color":"#79253a", "logo":"glt.svg"},
    "team_08":  {"owner":"Owner 8", "name":"Hotel FC",            "abbr":"HFC",   "color":"#002868", "logo":"hfc.svg"},
    "team_09": {"owner":"Owner 9",  "name":"India United",        "abbr":"INU", "color":"#7700b5", "logo":"inu.svg"},
    "team_10":       {"owner":"Owner 10",           "name":"Juliet SC",  "abbr":"JSC",  "color":"#34302b", "logo":"jsc.svg"},
    "team_11":  {"owner":"Owner 11",     "name":"Kilo Athletic",     "abbr":"KAT",   "color":"#eaaa00", "logo":"kat.svg"},
    "team_12":      {"owner":"Owner 12",         "name":"Lima Rovers",  "abbr":"LMR", "color":"#bc2e2e", "logo":"lmr.svg"},
}


def resolve(name):
    if not name:
        return None
    r = TEAM_NAME_MAP.get(name)
    if r:
        return r
    stripped = name.replace(".", "").strip()
    for k, v in TEAM_NAME_MAP.items():
        if k.replace(".", "").strip() == stripped:
            return v
    return None


def _parse_transaction_group(rows, team_name_lookup):
    """Parse a group of raw transaction rows (same txSetId) into a transaction dict."""
    first = rows[0]
    tx_id = first.get("txSetId", "")

    cells = first.get("cells", [])
    if isinstance(cells, dict):
        cells = list(cells.values())
    cells_by_key = {}
    for c in cells:
        if isinstance(c, dict) and "key" in c:
            cells_by_key[c["key"]] = c

    team_cell = cells_by_key.get("team", {})
    team_id = team_cell.get("teamId", "")
    team_name = team_name_lookup.get(team_id, "") or team_cell.get("content", "")
    fed_id = resolve(team_name)

    date_cell = cells_by_key.get("date", {})
    date_str = (date_cell.get("content", "") or "").strip()
    parsed_date = ""
    if date_str:
        for fmt in ["%a %b %d, %Y, %I:%M%p", "%a %b %d, %Y, %I:%M %p",
                     "%a %b %d, %Y", "%b %d, %Y", "%Y-%m-%d"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt).isoformat()
                break
            except ValueError:
                continue
        if not parsed_date:
            parsed_date = date_str

    # FAAB cost from cell with key="cost" or "bid" or "amount"
    cost_cell = cells_by_key.get("cost") or cells_by_key.get("bid") or cells_by_key.get("amount") or {}
    faab_cost_str = (str(cost_cell.get("content", "")) or "").strip().replace("$", "").replace(",", "")
    faab_cost = 0
    if faab_cost_str:
        try:
            faab_cost = int(float(faab_cost_str))
        except (ValueError, TypeError):
            faab_cost = 0

    players = []
    for row in rows:
        scorer = row.get("scorer")
        if not scorer:
            continue
        tx_code = row.get("transactionCode", "")
        tx_type = row.get("claimType", tx_code) if tx_code == "CLAIM" else tx_code
        players.append({
            "name": scorer.get("name", "") or scorer.get("shortName", ""),
            "position": scorer.get("posShortNames", ""),
            "real_team": scorer.get("teamName", ""),
            "type": tx_type,
        })

    return {
        "id": tx_id,
        "date": parsed_date,
        "team_name": team_name,
        "fed_id": fed_id,
        "faab_cost": faab_cost,
        "players": players,
    }


def scrape_transactions_authenticated(league_id, cookies, count=500):
    """Scrape transaction history with cookie authentication."""
    payload = {
        "msgs": [{
            "method": "getTransactionDetailsHistory",
            "data": {"leagueId": league_id, "maxResultsPerPage": str(count)},
        }]
    }
    headers = {
        "Cookie": cookies,
        "Referer": "https://www.fantrax.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        resp = requests.post(
            "https://www.fantrax.com/fxpa/req",
            params={"leagueId": league_id},
            json=payload, headers=headers, timeout=30,
        )
        resp_json = resp.json()
    except Exception as e:
        print(f"  API request failed: {e}")
        return []

    if "pageError" in resp_json:
        err = resp_json["pageError"]
        title = err.get("title", err.get("code", "unknown"))
        print(f"  API error: {title}")
        if "logged in" in title.lower() or "auth" in title.lower():
            print("  Your cookies may have expired. Copy fresh ones from Chrome.")
        return []

    try:
        data = resp_json["responses"][0]["data"]
        rows = data.get("table", {}).get("rows", [])
    except (KeyError, IndexError) as e:
        print(f"  Unexpected response structure: {e}")
        return []

    if not rows:
        print("  No transaction rows returned.")
        return []

    team_lookup = {}
    for tid, tinfo in data.get("fantasyTeamInfo", {}).items():
        team_lookup[tid] = tinfo.get("name", "")

    grouped = []
    current = []
    for row in rows:
        if current and row.get("txSetId") != current[0].get("txSetId"):
            grouped.append(current)
            current = []
        current.append(row)
    if current:
        grouped.append(current)

    txns = []
    for group in grouped:
        try:
            txn = _parse_transaction_group(group, team_lookup)
            if txn:
                txns.append(txn)
        except Exception as e:
            print(f"  Skipping malformed transaction: {e}")

    return txns


def main():
    print("=" * 60)
    print("  Federation — Previous NFL Season Transaction Scraper")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load cookies
    if not COOKIES_FILE.exists():
        print(f"\nERROR: cookies.txt not found at {COOKIES_FILE}")
        print("Follow the instructions at the top of this file to create it.")
        sys.exit(1)

    cookies = COOKIES_FILE.read_text().strip()
    if not cookies:
        print("\nERROR: cookies.txt is empty. Paste your Fantrax cookie string into it.")
        sys.exit(1)

    print(f"\nUsing cookie auth ({len(cookies)} chars)")
    print(f"League: {LEAGUE_ID}")

    # Scrape transactions
    print(f"\nFetching transactions...")
    txns = scrape_transactions_authenticated(LEAGUE_ID, cookies)
    if not txns:
        print("\nNo transactions retrieved. Check your cookies and try again.")
        sys.exit(1)

    print(f"  Got {len(txns)} transactions")

    # Load existing transaction file (if any)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if TX_FILE.exists():
        with open(TX_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"\nLoaded existing {TX_FILE.name} ({len(existing.get('leagues', {}))} leagues)")

    # Merge
    if "leagues" not in existing:
        existing["leagues"] = {}
    if "season" not in existing:
        existing["season"] = SEASON
    if "teams" not in existing:
        existing["teams"] = {}
    existing["teams"].update(FED_TEAMS)

    existing["leagues"][LEAGUE_KEY] = {
        "league_name": "FedFL",
        "sport": "NFL",
        "transactions": txns,
    }
    existing["scraped_at"] = datetime.now().isoformat()

    # Save
    with open(TX_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, default=str)

    total_all = sum(len(ld.get("transactions", [])) for ld in existing["leagues"].values())
    print(f"\nSaved to {TX_FILE}")
    print(f"  {LEAGUE_KEY}: {len(txns)} transactions")
    print(f"  Total across all leagues: {total_all} transactions")
    print("\nDone! This data will be preserved by future scraper runs.")


if __name__ == "__main__":
    main()
