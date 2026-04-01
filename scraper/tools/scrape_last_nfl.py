"""
Federation — Scrape Last Year's NFL League (Private)
================================================
This league requires authentication. Here's how:

STEP 1: Open this URL in Chrome (make sure you're logged into Fantrax):
        https://www.fantrax.com/fantasy/league/YOUR_PREV_NFL_LEAGUE_ID/home

STEP 2: Press F12 to open DevTools

STEP 3: Click the "Network" tab at the top of DevTools

STEP 4: Refresh the page (Ctrl+R)

STEP 5: In the Network list, click the very first request (it will say
        "home" or "YOUR_PREV_NFL_LEAGUE_ID" or similar)

STEP 6: On the right side, scroll down in the "Headers" section until
        you see "Cookie:" under "Request Headers"

STEP 7: Click on the Cookie value and copy the ENTIRE thing (it's very long)

STEP 8: Paste it below between the triple quotes, replacing PASTE_YOUR_COOKIES_HERE

STEP 9: Save this file and run: python scrape_last_nfl.py
"""

import json, sys, requests
from pathlib import Path
from datetime import datetime

# ============================================================
# PASTE YOUR COOKIES HERE (between the triple quotes)
# ============================================================
COOKIES = """_ga=GA1.2.2092942570.1755206203; uig=ohqexrblmebwgec8; ui=ohqexrblmebwgec8; __cf_bm=JInbt11P7khtW5tGFv..d7VOmlayASLJXYb2QGtAxpg-1771633013-1.0.1.1-hzEb2dGj4B5E.USRZUcw04WM.IoH_j..w1IdREh6m7Xvl_JzbXDdOvph0NmIqsjkA.M7yOuuZcXPboGl4lswsTcOVbVPhEwY6x1I27iOQRs; _gid=GA1.2.2093961396.1771633015; cf_clearance=Cyw2kBddKx1KbyJ7Qh6_zokDBzYrXHH6dwp6xpZb_QA-1771633014-1.2.1.1-vjLB8nbxNPdKwFkcvhhTwSpVjvDGeQE_f39RDk0SS62R_i5zaSS71Wa3c8Fi7IMQnFnL7w9R2EwfK14LcbNG_N2kjngtguaBzMCmxi.4S2aPXAexodBdnPOrrcJ9SJifdoaXQjjV_4ahPsNlLJuM1KSpx0lu7lm1hekYS_a4AwocEesI1rLNdG5aSfh3dtptQuM8e2NpAb9hly.IKNKEATEomT2ZZO.DwmX9kjJFcvI; _gat=1; JSESSIONID=node0gqvhb8w1kmrm1aycap8ecn7tr27707.node0; FX_RM=_qpxzCx4CERMCWwMJHA1BWFpdAh4eVgRSCRJeBxsTGQ5dR0c=; _ga_DM2Q31JXYV=GS2.2.s1771633021$o5$g1$t1771633046$j35$l0$h0"""
# ============================================================

LEAGUE_ID = "YOUR_PREV_NFL_LEAGUE_ID"
FXEA = "https://www.fantrax.com/fxea/general"
OUTPUT_DIR = Path(__file__).parent / "data"

TEAM_NAME_MAP = {
    "Bravo United": "team_02", "Alpha FC": "team_01",
    "Charlie SC": "team_03", "Delta Athletic": "team_04",
    "Echo Rangers": "team_05", "Foxtrot City": "team_06",
    "Golf Town": "team_07", "Hotel FC": "team_08",
    "India United": "team_09", "Juliet SC": "team_10",
    "Kilo Athletic": "team_11", "Lima Rovers": "team_12",
}


def api_get(endpoint, params):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.fantrax.com/",
        "Cookie": COOKIES.strip(),
    }
    r = requests.get(f"{FXEA}/{endpoint}", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    if "PASTE_YOUR_COOKIES_HERE" in COOKIES:
        print("You need to paste your Fantrax cookies first!")
        print("Open this file and follow the instructions at the top.")
        print("Replace PASTE_YOUR_COOKIES_HERE with your actual cookies.")
        sys.exit(1)

    print(f"Scraping last year's FedFL (league: {LEAGUE_ID})...")
    print(f"Using cookie auth ({len(COOKIES.strip())} chars)\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "league_key": "fed_fl_prev",
        "league_id": LEAGUE_ID,
        "name": "FedFL (Previous Season)",
        "sport": "NFL",
        "scraped_at": datetime.now().isoformat(),
        "method": "direct_api_authenticated",
        "teams": [], "standings": [], "rosters": {}, "matchups": [],
    }

    # ---- TEST AUTH ----
    print("Testing authentication...")
    try:
        test = api_get("getStandings", {"leagueId": LEAGUE_ID})
        if isinstance(test, dict) and test.get("error"):
            print(f"Auth failed: {test.get('error')}")
            print("Your cookies may have expired. Try copying fresh ones.")
            sys.exit(1)
        print("Authentication working!\n")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (401, 403):
            print(f"Auth failed (HTTP {e.response.status_code})")
            print("Your cookies may have expired. Try copying fresh ones.")
            sys.exit(1)
        raise

    # ---- STANDINGS ----
    print("Fetching standings...")
    try:
        data = api_get("getStandings", {"leagueId": LEAGUE_ID})
        if isinstance(data, list):
            for row in data:
                wlt = str(row.get("points", "0-0-0")).split("-")
                tn = row.get("teamName", "")
                result["standings"].append({
                    "rank": row.get("rank", 0),
                    "team_name": tn,
                    "fed_id": TEAM_NAME_MAP.get(tn),
                    "fantrax_id": row.get("teamId", ""),
                    "w": int(wlt[0]) if len(wlt) >= 1 else 0,
                    "l": int(wlt[1]) if len(wlt) >= 2 else 0,
                    "t": int(wlt[2]) if len(wlt) >= 3 else 0,
                    "pf": row.get("totalPointsFor", 0),
                    "win_pct": row.get("winPercentage", 0),
                    "gb": row.get("gamesBack", 0),
                })
            print(f"  {len(result['standings'])} teams")
            for e in result["standings"]:
                print(f"    {e['rank']:>2}. {e['team_name']:<30} {e['w']}-{e['l']}-{e['t']}  PF:{e['pf']:.1f}")
        else:
            print(f"  Unexpected format: {type(data)}")
            result["standings_raw"] = data
    except Exception as e:
        print(f"  Error: {e}")

    # ---- MATCHUPS ----
    print("\nFetching matchups...")
    try:
        data = api_get("getLeagueInfo", {"leagueId": LEAGUE_ID})
        if isinstance(data, dict):
            result["full_name"] = data.get("name", "FedFL Previous")
            seen = {}
            for period in data.get("matchups", []):
                pn = period.get("period", 0)
                for mu in period.get("matchupList", []):
                    a, h = mu.get("away", {}), mu.get("home", {})
                    for t in [a, h]:
                        tid, tn = t.get("id",""), t.get("name","")
                        if tid and tid not in seen:
                            seen[tid] = {"fantrax_id":tid, "fantrax_name":tn,
                                         "short":t.get("shortName",""),
                                         "fed_id":TEAM_NAME_MAP.get(tn)}
                    result["matchups"].append({
                        "period": pn,
                        "away_name": a.get("name",""), "away_id": a.get("id",""),
                        "home_name": h.get("name",""), "home_id": h.get("id",""),
                    })
            result["teams"] = list(seen.values())
            print(f"  {len(result['teams'])} teams, {len(result['matchups'])} matchups")
    except Exception as e:
        print(f"  Error: {e}")

    # ---- ROSTERS ----
    print("\nFetching rosters...")
    try:
        data = api_get("getTeamRosters", {"leagueId": LEAGUE_ID})
        rosters_data = data.get("rosters", {}) if isinstance(data, dict) else {}

        player_names = {}
        try:
            print("  Loading player names...")
            pid_data = api_get("getPlayerIds", {"sport": "NFL"})
            if isinstance(pid_data, list):
                for p in pid_data:
                    if isinstance(p, dict):
                        player_names[p.get("fantraxId", p.get("id", ""))] = {
                            "name": p.get("name", ""), "team": p.get("team", ""),
                            "position": p.get("position", ""),
                        }
                print(f"  {len(player_names)} player names loaded")
        except Exception as e:
            print(f"  Player names error: {e}")

        for team_id, team_data in rosters_data.items():
            tn = team_data.get("teamName", "")
            players = []
            for item in team_data.get("rosterItems", []):
                pid = item.get("id", "")
                pinfo = player_names.get(pid, {})
                players.append({
                    "name": pinfo.get("name", pid),
                    "position": item.get("position", ""),
                    "real_team": pinfo.get("team", ""),
                    "status": item.get("status", ""),
                })
            result["rosters"][team_id] = {
                "fantrax_id": team_id, "fantrax_name": tn,
                "fed_id": TEAM_NAME_MAP.get(tn), "players": players,
            }
            print(f"  {tn}: {len(players)} players")
    except Exception as e:
        print(f"  Error: {e}")

    # ---- SAVE ----
    path = OUTPUT_DIR / "fed_fl_prev.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    total_players = sum(len(r.get("players",[])) for r in result.get("rosters",{}).values())
    print(f"\n{'='*60}")
    print(f"  Saved to {path}")
    print(f"  Standings: {len(result['standings'])} teams")
    print(f"  Players:   {total_players}")
    print(f"  Matchups:  {len(result['matchups'])}")
    print(f"  File size: {path.stat().st_size/1024:.1f} KB")
    print(f"{'='*60}")

    if result["standings"]:
        print(f"\n  Final FedFL Standings (Previous Season)")
        print(f"  {'Rk':>3}  {'Team':<30} {'W-L-T':>8}  {'PF':>8}  Fed Pts")
        print(f"  {'-'*68}")
        for e in result["standings"]:
            fed_pts = 13 - e["rank"]
            print(f"  {e['rank']:>3}  {e['team_name']:<30} {e['w']:>2}-{e['l']}-{e['t']}  {e['pf']:>8.1f}  {fed_pts:>4}")

    print(f"\nDone! Paste the output back to Claude and I'll integrate it into the federation standings.")


if __name__ == "__main__":
    main()
