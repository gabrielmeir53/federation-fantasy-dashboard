"""
Diagnostic: Check player name resolution + discover matchup results endpoints.
Run: python diagnose_api.py
"""
import json, requests

FXEA = "https://www.fantrax.com/fxea/general"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

def api(endpoint, params):
    r = requests.get(f"{FXEA}/{endpoint}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

# === 1. CHECK PLAYER ID RESOLUTION FOR NHL ===
print("=" * 60)
print("  1. NHL PLAYER ID CHECK")
print("=" * 60)

# Get NHL rosters
nhl_id = "YOUR_NHL_LEAGUE_ID"
rosters = api("getTeamRosters", {"leagueId": nhl_id})
roster_data = rosters.get("rosters", {})

# Collect all player IDs from rosters
all_pids = set()
sample_team = None
for tid, td in roster_data.items():
    for item in td.get("rosterItems", []):
        all_pids.add(item.get("id", ""))
    if not sample_team:
        sample_team = td
        sample_items = td.get("rosterItems", [])[:5]

print(f"  Total unique player IDs in NHL rosters: {len(all_pids)}")
print(f"  Sample IDs: {list(all_pids)[:10]}")

# Get player IDs for NHL
print(f"\n  Fetching getPlayerIds for NHL...")
try:
    players = api("getPlayerIds", {"sport": "NHL"})
    if isinstance(players, list):
        player_map = {}
        for p in players:
            if isinstance(p, dict):
                fid = p.get("fantraxId", p.get("id", ""))
                player_map[fid] = p.get("name", "")
        print(f"  Players returned: {len(player_map)}")
        
        # Check how many roster IDs we can resolve
        resolved = sum(1 for pid in all_pids if pid in player_map)
        unresolved = [pid for pid in all_pids if pid not in player_map]
        print(f"  Resolved: {resolved}/{len(all_pids)}")
        if unresolved:
            print(f"  Unresolved IDs (first 10): {unresolved[:10]}")
        
        # Show sample resolutions
        print(f"\n  Sample roster items:")
        for item in sample_items:
            pid = item.get("id", "")
            name = player_map.get(pid, "??? NOT FOUND")
            print(f"    {pid} -> {name} ({item.get('position', '')})")
    else:
        print(f"  Unexpected format: {type(players)}")
        print(f"  First 500 chars: {str(players)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")


# === 2. CHECK FOR MATCHUP SCORES ENDPOINT ===
print(f"\n{'=' * 60}")
print("  2. MATCHUP SCORES DISCOVERY")
print("=" * 60)

nba_id = "YOUR_NBA_LEAGUE_ID"

# Try various possible endpoints
score_endpoints = [
    ("getMatchupScores", {"leagueId": nba_id, "period": 1}),
    ("getMatchupResults", {"leagueId": nba_id, "period": 1}),
    ("getScoreboard", {"leagueId": nba_id, "period": 1}),
    ("getMatchups", {"leagueId": nba_id, "period": 1}),
    ("getLeagueMatchups", {"leagueId": nba_id}),
    ("getBoxScore", {"leagueId": nba_id, "period": 1}),
    ("getLeagueScores", {"leagueId": nba_id}),
    ("getWeeklyResults", {"leagueId": nba_id, "period": 1}),
    ("getLeagueTransactions", {"leagueId": nba_id}),
    ("getDraftResults", {"leagueId": nba_id}),
    ("getPlayerScores", {"leagueId": nba_id, "period": 1, "scoringCategoryType": "5"}),
]

for endpoint, params in score_endpoints:
    try:
        data = api(endpoint, params)
        print(f"\n  ✅ {endpoint} -> WORKS!")
        pretty = json.dumps(data, indent=2, default=str)
        # Print first 800 chars
        print(f"     {pretty[:800]}")
        if len(pretty) > 800:
            print(f"     ... ({len(pretty)} total chars)")
    except requests.exceptions.HTTPError as e:
        print(f"  ❌ {endpoint} -> HTTP {e.response.status_code}")
    except Exception as e:
        print(f"  ❌ {endpoint} -> {e}")


# === 3. CHECK NBA PLAYER IDS (since that works) ===
print(f"\n{'=' * 60}")
print("  3. NBA PLAYER ID FORMAT CHECK")
print("=" * 60)

nba_rosters = api("getTeamRosters", {"leagueId": nba_id})
nba_rd = nba_rosters.get("rosters", {})
sample_nba = list(nba_rd.values())[0] if nba_rd else {}
print(f"  Sample NBA roster items (first 3):")
for item in sample_nba.get("rosterItems", [])[:3]:
    print(f"    {json.dumps(item)}")

nba_players = api("getPlayerIds", {"sport": "NBA"})
if isinstance(nba_players, list):
    nba_map = {p.get("fantraxId", p.get("id", "")): p.get("name", "") for p in nba_players if isinstance(p, dict)}
    print(f"  NBA player DB size: {len(nba_map)}")
    # Check resolution
    nba_pids = set()
    for td in nba_rd.values():
        for item in td.get("rosterItems", []):
            nba_pids.add(item.get("id", ""))
    resolved = sum(1 for pid in nba_pids if pid in nba_map)
    print(f"  NBA resolution: {resolved}/{len(nba_pids)}")
    unresolvedNba = [pid for pid in nba_pids if pid not in nba_map]
    if unresolvedNba:
        print(f"  Unresolved: {unresolvedNba[:5]}")

print(f"\n{'=' * 60}")
print("  Done! Paste output back to Claude.")
print(f"{'=' * 60}")
