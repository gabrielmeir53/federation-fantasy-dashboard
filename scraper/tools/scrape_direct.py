"""
Federation Direct Fantrax API Module
===============================
Hits the Fantrax internal API endpoints directly with requests.
This bypasses fantraxapi library bugs (NFL parsing, missing PF/PA, etc.)

These are the same endpoints the Fantrax website uses internally.
No auth needed for public leagues.

Usage (standalone):
    python scrape_direct.py --verbose

Usage (imported by scrape_fantrax.py):
    from scrape_direct import scrape_league_direct
    data = scrape_league_direct("YOUR_NFL_LEAGUE_ID", "FedFL", "NFL")
"""

import json
import sys
import requests
import traceback
from datetime import datetime
from pathlib import Path

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv
OUTPUT_DIR = Path(__file__).parent / "data"

# Fantrax internal API base
FXEA_BASE = "https://www.fantrax.com/fxea/general"

# Team name mapping (same as main scraper)
TEAM_NAME_MAP = {
    "Bravo United":       "team_02",
    "Alpha FC":      "team_01",
    "Charlie SC":              "team_03",
    "Delta Athletic":     "team_04",
    "Echo Rangers":        "team_05",
    "Foxtrot City":              "team_06",
    "Golf Town":           "team_07",
    "Hotel FC":                  "team_08",
    "India United":              "team_09",
    "Juliet SC":        "team_10",
    "Kilo Athletic":           "team_11",
    "Lima Rovers":        "team_12",
}


def log(msg):
    if VERBOSE:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def api_get(endpoint, params):
    """Call a Fantrax API endpoint."""
    url = f"{FXEA_BASE}/{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.fantrax.com/",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def scrape_league_direct(league_id, name, sport):
    """
    Scrape a Fantrax league using the direct API.
    Returns the same data structure as the main scraper.
    """
    result = {
        "league_key": None,  # caller sets this
        "league_id": league_id,
        "name": name,
        "sport": sport,
        "scraped_at": datetime.now().isoformat(),
        "method": "direct_api",
        "teams": [],
        "standings": [],
        "rosters": {},
    }

    # ===== STANDINGS =====
    log(f"  Fetching standings via direct API...")
    try:
        data = api_get("getStandings", {"leagueId": league_id})
        log(f"  Standings response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

        # The API returns different structures, let's handle them
        if isinstance(data, dict):
            # Look for standings data in the response
            standings_data = data.get("standings", data.get("rows", data.get("data", data)))

            # Try to find team records
            if "tableList" in data:
                log(f"  Found tableList format")
                for table in data["tableList"]:
                    rows = table.get("rows", [])
                    for i, row in enumerate(rows):
                        entry = parse_standings_row(row, i + 1)
                        if entry:
                            result["standings"].append(entry)

            elif "records" in data:
                log(f"  Found records format")
                for i, rec in enumerate(data["records"]):
                    entry = parse_standings_row(rec, i + 1)
                    if entry:
                        result["standings"].append(entry)

            elif isinstance(standings_data, list):
                log(f"  Found list format with {len(standings_data)} items")
                for i, row in enumerate(standings_data):
                    entry = parse_standings_row(row, i + 1)
                    if entry:
                        result["standings"].append(entry)

            else:
                # Dump the raw response for debugging
                log(f"  Unknown standings format, saving raw data...")
                result["standings_raw"] = data

        log(f"  Parsed {len(result['standings'])} standings entries")

    except requests.exceptions.HTTPError as e:
        log(f"  HTTP error: {e}")
        log(f"  (This endpoint may not be available for public leagues)")
    except Exception as e:
        log(f"  Standings error: {e}")
        traceback.print_exc() if VERBOSE else None

    # ===== ROSTERS =====
    log(f"  Fetching rosters via direct API...")
    try:
        data = api_get("getTeamRosters", {"leagueId": league_id})
        log(f"  Rosters response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

        if isinstance(data, dict):
            rosters = data.get("rosters", data.get("teamRosters", data.get("data", {})))

            if isinstance(rosters, dict):
                for team_id, roster_data in rosters.items():
                    team_name = ""
                    players = []

                    if isinstance(roster_data, dict):
                        team_name = roster_data.get("teamName", roster_data.get("name", ""))
                        player_list = roster_data.get("players", roster_data.get("roster", []))
                        if isinstance(player_list, list):
                            for p in player_list:
                                if isinstance(p, dict):
                                    players.append({
                                        "name": p.get("name", p.get("playerName", "")),
                                        "position": p.get("position", p.get("pos", "")),
                                        "real_team": p.get("team", p.get("teamName", "")),
                                        "status": p.get("status", ""),
                                    })
                                elif isinstance(p, str):
                                    players.append({"name": p})
                    elif isinstance(roster_data, list):
                        for p in roster_data:
                            if isinstance(p, dict):
                                players.append({
                                    "name": p.get("name", ""),
                                    "position": p.get("position", ""),
                                })

                    fed_id = TEAM_NAME_MAP.get(team_name)
                    result["rosters"][team_id] = {
                        "fantrax_id": team_id,
                        "fantrax_name": team_name,
                        "fed_id": fed_id,
                        "players": players,
                    }

            # Save raw for debugging if we got data but couldn't parse it well
            if not result["rosters"]:
                result["rosters_raw"] = data

        log(f"  Parsed rosters for {len(result['rosters'])} teams")

    except requests.exceptions.HTTPError as e:
        log(f"  HTTP error: {e}")
    except Exception as e:
        log(f"  Rosters error: {e}")
        traceback.print_exc() if VERBOSE else None

    # ===== LEAGUE INFO =====
    log(f"  Fetching league info...")
    try:
        data = api_get("getLeagueInfo", {"leagueId": league_id})
        if isinstance(data, dict):
            result["league_info"] = {
                "name": data.get("name", data.get("leagueName", "")),
                "sport": data.get("sport", ""),
                "season": data.get("season", ""),
                "num_teams": data.get("numTeams", ""),
            }
            # Extract teams list if present
            teams_data = data.get("teams", data.get("teamList", []))
            if isinstance(teams_data, list):
                for t in teams_data:
                    if isinstance(t, dict):
                        team_name = t.get("name", t.get("teamName", ""))
                        result["teams"].append({
                            "fantrax_id": t.get("id", t.get("teamId", "")),
                            "fantrax_name": team_name,
                            "short": t.get("short", t.get("shortName", "")),
                            "fed_id": TEAM_NAME_MAP.get(team_name),
                        })
            elif isinstance(teams_data, dict):
                for tid, t in teams_data.items():
                    team_name = t.get("name", t.get("teamName", "")) if isinstance(t, dict) else str(t)
                    result["teams"].append({
                        "fantrax_id": tid,
                        "fantrax_name": team_name,
                        "fed_id": TEAM_NAME_MAP.get(team_name),
                    })
            log(f"  League info: {result.get('league_info', {}).get('name', 'unknown')}")
    except Exception as e:
        log(f"  League info error: {e}")

    return result


def parse_standings_row(row, default_rank):
    """Parse a single standings row from various API formats."""
    if not isinstance(row, dict):
        return None

    entry = {"rank": default_rank}

    # Team name
    for key in ["teamName", "name", "team", "teamLabel"]:
        if key in row:
            entry["team_name"] = str(row[key])
            entry["fed_id"] = TEAM_NAME_MAP.get(entry["team_name"])
            break

    # Record
    for key in ["wins", "w", "W"]:
        if key in row:
            try:
                entry["w"] = int(row[key])
            except (ValueError, TypeError):
                pass
            break

    for key in ["losses", "l", "L"]:
        if key in row:
            try:
                entry["l"] = int(row[key])
            except (ValueError, TypeError):
                pass
            break

    for key in ["ties", "t", "T"]:
        if key in row:
            try:
                entry["t"] = int(row[key])
            except (ValueError, TypeError):
                pass
            break

    # Record string format "10-4-0"
    for key in ["record", "wlt"]:
        if key in row and "-" in str(row[key]):
            parts = str(row[key]).split("-")
            if len(parts) >= 2:
                try:
                    entry.setdefault("w", int(parts[0]))
                    entry.setdefault("l", int(parts[1]))
                    if len(parts) >= 3:
                        entry.setdefault("t", int(parts[2]))
                except ValueError:
                    pass

    # Points for/against
    for key in ["pointsFor", "pf", "PF", "fPts", "fPtsF", "fantasyPtsFor"]:
        if key in row:
            try:
                entry["pf"] = float(row[key])
            except (ValueError, TypeError):
                pass
            break

    for key in ["pointsAgainst", "pa", "PA", "fPtsA", "fantasyPtsAgainst"]:
        if key in row:
            try:
                entry["pa"] = float(row[key])
            except (ValueError, TypeError):
                pass
            break

    # Rank
    for key in ["rank", "Rank", "rk"]:
        if key in row:
            try:
                entry["rank"] = int(row[key])
            except (ValueError, TypeError):
                pass
            break

    return entry if "team_name" in entry or "w" in entry else None


# ============================================================
# STANDALONE MODE
# ============================================================
LEAGUES = {
    "fed_fl": {"league_id": "YOUR_NFL_LEAGUE_ID", "name": "FedFL", "sport": "NFL"},
    "fed_ba": {"league_id": "YOUR_NBA_LEAGUE_ID", "name": "FedBA", "sport": "NBA"},
    "fed_hl": {"league_id": "YOUR_NHL_LEAGUE_ID", "name": "FedHL", "sport": "NHL"},
    "fed_lb": {"league_id": "YOUR_MLB_LEAGUE_ID", "name": "FedLB", "sport": "MLB"},
}

if __name__ == "__main__":
    VERBOSE = True
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None

    leagues = {target: LEAGUES[target]} if target and target in LEAGUES else LEAGUES

    for lk, cfg in leagues.items():
        print(f"\n📡 Direct API scrape: {cfg['name']} ({cfg['sport']})...")
        try:
            result = scrape_league_direct(cfg["league_id"], cfg["name"], cfg["sport"])
            result["league_key"] = lk

            path = OUTPUT_DIR / f"{lk}_direct.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"  ✅ Saved to {path}")
            print(f"     Teams: {len(result['teams'])}, Standings: {len(result['standings'])}, "
                  f"Rosters: {len(result['rosters'])}")

            if result["standings"]:
                for e in result["standings"][:3]:
                    print(f"     {e.get('rank', '?')}. {e.get('team_name', '?')} ({e.get('w', '?')}-{e.get('l', '?')})")

        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()

    print("\nDone!")
