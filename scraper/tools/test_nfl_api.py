"""
Quick test: Hit the Fantrax direct API for the NFL league
and print the raw JSON response so we can see the exact format.

Usage: python test_nfl_api.py
"""
import requests
import json

LEAGUE_ID = "YOUR_NFL_LEAGUE_ID"  # FedFL
BASE = "https://www.fantrax.com/fxea/general"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.fantrax.com/",
}

endpoints = [
    ("getLeagueInfo", {"leagueId": LEAGUE_ID}),
    ("getStandings",  {"leagueId": LEAGUE_ID}),
    ("getTeamRosters", {"leagueId": LEAGUE_ID}),
]

for name, params in endpoints:
    print(f"\n{'='*60}")
    print(f"  ENDPOINT: {name}")
    print(f"  URL: {BASE}/{name}?{'&'.join(k+'='+v for k,v in params.items())}")
    print(f"{'='*60}")
    try:
        resp = requests.get(f"{BASE}/{name}", params=params, headers=HEADERS, timeout=30)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Pretty print first 3000 chars
            pretty = json.dumps(data, indent=2, default=str)
            if len(pretty) > 3000:
                print(pretty[:3000])
                print(f"\n  ... ({len(pretty)} total chars, truncated)")
            else:
                print(pretty)
        else:
            print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")

print(f"\n{'='*60}")
print("  Done! Copy/paste the output back to Claude.")
print(f"{'='*60}")
