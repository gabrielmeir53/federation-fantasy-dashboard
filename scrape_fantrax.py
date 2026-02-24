"""
Federation Fantrax Scraper v3.6
=========================
- NBA/MLB: fantraxapi library + direct API enrichment
- NHL: library + direct API (rosters via direct API for "137" bug)
- NFL: direct API (library has "Week" bug)
- NFL previous season: loaded from fed_fl_prev.json
- Draft picks: scraped from Google Sheets (all future seasons)
- Rosters: sorted by position (standard sport order)
- Player names: resolved via league-specific + sport-wide ID lookup
- Generates dashboard_live.html with embedded data

Requirements:  pip install fantraxapi requests
Usage:         python scrape_fantrax.py --verbose
"""

import json, re, sys, csv, io, traceback, requests
from datetime import datetime
from pathlib import Path

try:
    from fantraxapi import League
    HAS_LIB = True
except ImportError:
    HAS_LIB = False
    print("fantraxapi not installed — using direct API only. pip install fantraxapi")

# ============================================================
# CONFIG
# ============================================================
LEAGUES = {
    "fed_fl": {"league_id": "YOUR_NFL_LEAGUE_ID", "name": "FedFL", "sport": "NFL", "sport_code": "NFL", "method": "direct"},
    "fed_ba": {"league_id": "YOUR_NBA_LEAGUE_ID", "name": "FedBA", "sport": "NBA", "sport_code": "NBA", "method": "library"},
    "fed_hl": {"league_id": "YOUR_NHL_LEAGUE_ID", "name": "FedHL", "sport": "NHL", "sport_code": "NHL", "method": "library"},
    "fed_lb": {"league_id": "YOUR_MLB_LEAGUE_ID", "name": "FedLB", "sport": "MLB", "sport_code": "MLB", "method": "library"},
}

NFL_PREV_FILE = "fed_fl_prev.json"
NFL_PREV_LEAGUE_ID = "YOUR_PREV_NFL_LEAGUE_ID"
DRAFT_SHEET_ID = "YOUR_DRAFT_SHEET_ID"
DRAFT_SEASONS = ["2026-27", "2027-28", "2028-29", "2029-30", "2030-31", "2031-32", "2032-33", "2033-34"]

TEAM_NAME_MAP = {
    "Alpha FC": "team_01", "Bravo United": "team_02",
    "Charlie SC": "team_03", "Delta Athletic": "team_04",
    "Echo Rangers": "team_05", "Foxtrot City": "team_06",
    "Golf Town": "team_07", "Hotel FC": "team_08",
    "India United": "team_09", "Juliet SC": "team_10",
    "Kilo Athletic": "team_11", "Lima Rovers": "team_12",
}
SHEET_LEAGUE_MAP = {"FedBA": "fed_ba", "FedFL": "fed_fl", "FedHL": "fed_hl", "FedLB": "fed_lb"}

FED_TEAMS = {
    "team_01": {"owner": "Owner 1",  "name": "Alpha FC",       "abbr": "AFC", "color": "#00333f", "logo": "afc.svg"},
    "team_02": {"owner": "Owner 2",  "name": "Bravo United",   "abbr": "BRU", "color": "#004b41", "logo": "bru.svg"},
    "team_03": {"owner": "Owner 3",  "name": "Charlie SC",     "abbr": "CSC", "color": "#0d00b2", "logo": "csc.svg"},
    "team_04": {"owner": "Owner 4",  "name": "Delta Athletic", "abbr": "DAT", "color": "#12e0e5", "logo": "dat.svg"},
    "team_05": {"owner": "Owner 5",  "name": "Echo Rangers",   "abbr": "ERG", "color": "#19b9ee", "logo": "erg.svg"},
    "team_06": {"owner": "Owner 6",  "name": "Foxtrot City",   "abbr": "FXC", "color": "#036b08", "logo": "fxc.svg"},
    "team_07": {"owner": "Owner 7",  "name": "Golf Town",      "abbr": "GTN", "color": "#79253a", "logo": "gtn.svg"},
    "team_08": {"owner": "Owner 8",  "name": "Hotel FC",       "abbr": "HFC", "color": "#002868", "logo": "hfc.svg"},
    "team_09": {"owner": "Owner 9",  "name": "India United",   "abbr": "IUN", "color": "#7700b5", "logo": "iun.svg"},
    "team_10": {"owner": "Owner 10", "name": "Juliet SC",      "abbr": "JSC", "color": "#34302b", "logo": "jsc.svg"},
    "team_11": {"owner": "Owner 11", "name": "Kilo Athletic",  "abbr": "KAT", "color": "#eaaa00", "logo": "kat.svg"},
    "team_12": {"owner": "Owner 12", "name": "Lima Rovers",    "abbr": "LRV", "color": "#bc2e2e", "logo": "lrv.svg"},
}

POS_ORDER = {
    "NFL": ["QB","RB","WR","TE","Flex","D/ST","K"],
    "NBA": ["PG","SG","SF","PF","C","Flx","Utility","Util"],
    "NHL": ["LW","C","RW","D","G","Skaters","Sk"],
    "MLB": ["C","1B","2B","SS","3B","OF","SP","RP","Utility","Util","DH"],
}

OUTPUT_DIR = Path(__file__).parent / "data"
SCRIPT_DIR = Path(__file__).parent
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

# Support --output-dir for server deployment (writes JSON to public web dir)
for i, arg in enumerate(sys.argv):
    if arg == "--output-dir" and i + 1 < len(sys.argv):
        OUTPUT_DIR = Path(sys.argv[i + 1])
        break

def log(msg):
    if VERBOSE: print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def resolve(name):
    if not name: return None
    r = TEAM_NAME_MAP.get(name)
    if r: return r
    stripped = name.replace(".", "").strip()
    for k, v in TEAM_NAME_MAP.items():
        if k.replace(".", "").strip() == stripped: return v
    return None

def sort_roster(players, sport):
    order = POS_ORDER.get(sport, [])
    def pos_key(p):
        pos = (p.get("position") or "").strip()
        status = (p.get("status") or "").upper()
        if "IR" in status or "INJURED" in status: return (900, p.get("name", ""))
        if "RESERVE" in status: return (800, p.get("name", ""))
        pos_up = pos.upper()
        for i, o in enumerate(order):
            if o.upper() == pos_up or pos_up.startswith(o.upper()): return (i, p.get("name", ""))
        return (500, p.get("name", ""))
    return sorted(players, key=pos_key)

# ============================================================
# DIRECT FANTRAX API
# ============================================================
FXEA = "https://www.fantrax.com/fxea/general"
_PLAYER_CACHE = {}

def api_get(endpoint, params):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
    r = requests.get(f"{FXEA}/{endpoint}", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def _load_player_names(league_id, sport_code):
    """Load player ID -> name mapping. Tries league-specific first, then sport-wide."""
    cache_key = f"{league_id}_{sport_code}"
    if cache_key in _PLAYER_CACHE: return _PLAYER_CACHE[cache_key]
    player_names = {}

    def _parse(data, label):
        count = 0
        if isinstance(data, dict):
            for pid, pinfo in data.items():
                if isinstance(pinfo, dict):
                    player_names[str(pid)] = {"name": pinfo.get("name",""), "team": pinfo.get("team",""), "position": pinfo.get("position","")}
                    count += 1
                elif isinstance(pinfo, str):
                    player_names[str(pid)] = {"name": pinfo, "team": "", "position": ""}
                    count += 1
        elif isinstance(data, list):
            for p in data:
                if isinstance(p, dict):
                    fid = str(p.get("fantraxId", p.get("id", "")))
                    player_names[fid] = {"name": p.get("name",""), "team": p.get("team",""), "position": p.get("position","")}
                    count += 1
        log(f"    {label}: {count} entries")
        return count

    # Strategy 1: league-specific IDs (these should match getTeamRosters IDs)
    try:
        log(f"  Player names (league-specific)...")
        data = api_get("getPlayerIds", {"leagueId": league_id})
        _parse(data, "league")
    except Exception as e:
        log(f"    League-specific failed: {e}")

    # Strategy 2: sport-wide IDs (fills gaps)
    try:
        log(f"  Player names (sport-wide)...")
        before = len(player_names)
        data = api_get("getPlayerIds", {"sport": sport_code})
        _parse(data, "sport")
        log(f"    Net new from sport: {len(player_names) - before}")
    except Exception as e:
        log(f"    Sport-wide failed: {e}")

    log(f"  Total player names: {len(player_names)}")
    _PLAYER_CACHE[cache_key] = player_names
    return player_names

def _resolve_roster(roster_items, player_names, sport):
    """Resolve roster items to player dicts with robust name resolution."""
    players = []
    resolved = unresolved = 0
    sample_bad = []

    for item in roster_items:
        pid = str(item.get("id", ""))
        # Try direct name fields first
        name = item.get("name") or item.get("playerName") or item.get("displayName") or ""
        if not name:
            pinfo = player_names.get(pid, {})
            name = pinfo.get("name", "")
        if not name and " " in pid:
            name = pid
        if name:
            resolved += 1
        else:
            unresolved += 1
            name = pid
            if len(sample_bad) < 5: sample_bad.append(pid)

        pos = item.get("position") or item.get("pos") or ""
        if not pos:
            pos = player_names.get(pid, {}).get("position", "")

        # Fix unresolved D/ST entries (defenses aren't in player name DB)
        if name.isdigit() and pos.upper() in ("DST","D/ST","DEF"):
            name = (team + " D/ST") if team else "Defense/ST"

        team = item.get("team") or item.get("teamName") or ""
        if not team:
            team = player_names.get(pid, {}).get("team", "")

        players.append({"name": name, "position": pos, "real_team": team,
                         "status": item.get("status", ""), "fantrax_player_id": pid})

    if unresolved:
        log(f"    {unresolved}/{resolved+unresolved} unresolved. IDs: {sample_bad}")
        if roster_items:
            log(f"    Sample item keys: {list(roster_items[0].keys())}")
            log(f"    Sample: {json.dumps(roster_items[0], default=str)[:300]}")
    else:
        log(f"    All {resolved} names resolved")
    return sort_roster(players, sport)

def scrape_direct(league_key, cfg):
    lid, sport = cfg["league_id"], cfg["sport"]
    log(f"  Direct API for {cfg['name']}...")
    result = {"league_key": league_key, "league_id": lid, "name": cfg["name"],
              "sport": sport, "scraped_at": datetime.now().isoformat(),
              "method": "direct_api", "teams": [], "standings": [], "rosters": {}, "matchups": [],
              "schedule_meta": {}}

    log(f"  Fetching standings...")
    try:
        data = api_get("getStandings", {"leagueId": lid})
        if isinstance(data, list):
            for row in data:
                wlt = str(row.get("points", "0-0-0")).split("-")
                tn = row.get("teamName", "")
                result["standings"].append({
                    "rank": row.get("rank", 0), "team_name": tn,
                    "fed_id": resolve(tn), "fantrax_id": row.get("teamId", ""),
                    "w": int(wlt[0]) if len(wlt)>=1 else 0,
                    "l": int(wlt[1]) if len(wlt)>=2 else 0,
                    "t": int(wlt[2]) if len(wlt)>=3 else 0,
                    "pf": row.get("totalPointsFor", 0),
                    "win_pct": row.get("winPercentage", 0),
                    "gb": row.get("gamesBack", 0),
                })
            log(f"  {len(result['standings'])} standings")
    except Exception as e: log(f"  Standings error: {e}")

    log(f"  Fetching league info...")
    try:
        data = api_get("getLeagueInfo", {"leagueId": lid})
        if isinstance(data, dict):
            result["full_name"] = data.get("name", cfg["name"])
            seen = {}
            for period in data.get("matchups", []):
                for mu in period.get("matchupList", []):
                    a, h = mu.get("away", {}), mu.get("home", {})
                    for t in [a, h]:
                        tid, tn = t.get("id",""), t.get("name","")
                        if tid and tid not in seen:
                            seen[tid] = {"fantrax_id":tid, "fantrax_name":tn, "short":t.get("shortName",""), "fed_id":resolve(tn)}
                    result["matchups"].append({"period":period.get("period",0), "away_name":a.get("name",""), "home_name":h.get("name","")})
            result["teams"] = list(seen.values())
            log(f"  {len(result['teams'])} teams, {len(result['matchups'])} matchups")
    except Exception as e: log(f"  League info error: {e}")

    # Matchup scores via raw API (library can't init NFL)
    log(f"  Fetching matchup scores (raw API)...")
    try:
        scored_matchups, sched_meta = scrape_matchup_scores_raw(lid)
        if scored_matchups:
            result["matchups"] = scored_matchups
            result["schedule_meta"] = sched_meta
            log(f"  {len(scored_matchups)} matchups with scores")
    except Exception as e:
        log(f"  Matchup scores error: {e}")

    # Build playoff bracket and compute final standings
    if result["standings"] and result["matchups"]:
        bracket = build_playoff_bracket(result["matchups"], result["standings"])
        result["playoff_bracket"] = bracket
        if bracket["status"] == "complete":
            result["standings"] = compute_final_standings(result["standings"], bracket)
            log(f"  Playoff bracket: complete — final standings updated")
        else:
            log(f"  Playoff bracket: {bracket['status']}")

    log(f"  Fetching rosters...")
    try:
        data = api_get("getTeamRosters", {"leagueId": lid})
        rosters_data = data.get("rosters", {}) if isinstance(data, dict) else {}
        player_names = _load_player_names(lid, cfg.get("sport_code", sport))
        for team_id, team_data in rosters_data.items():
            tn = team_data.get("teamName", "")
            players = _resolve_roster(team_data.get("rosterItems", []), player_names, sport)
            result["rosters"][team_id] = {"fantrax_id": team_id, "fantrax_name": tn, "fed_id": resolve(tn), "players": players}
        log(f"  {len(result['rosters'])} team rosters")
    except Exception as e: log(f"  Rosters error: {e}"); traceback.print_exc()
    return result

# ============================================================
# LIBRARY + DIRECT API ENRICHMENT
# ============================================================
def scrape_library(league_key, cfg):
    lid, sport = cfg["league_id"], cfg["sport"]
    log(f"  Library + direct API enrichment...")
    league = League(lid)
    log(f"  Connected: '{league.name}' ({league.year})")
    result = {"league_key": league_key, "league_id": lid, "name": cfg["name"],
              "full_name": league.name, "year": league.year, "sport": sport,
              "scraped_at": datetime.now().isoformat(), "method": "library+direct",
              "teams": [], "standings": [], "rosters": {}, "matchups": [],
              "schedule_meta": {}}
    for team in league.teams:
        result["teams"].append({"fantrax_id": team.id, "fantrax_name": team.name,
            "short": team.short, "logo": team.logo, "fed_id": resolve(team.name)})

    log(f"  Library standings...")
    try:
        text = str(league.standings())
        for m in re.finditer(r"(\d+):\s+(.+?)\s+\((\d+)-(\d+)-(\d+)\)", text):
            result["standings"].append({"rank": int(m.group(1)), "team_name": m.group(2).strip(),
                "fed_id": resolve(m.group(2).strip()), "w": int(m.group(3)), "l": int(m.group(4)), "t": int(m.group(5))})
    except Exception as e: log(f"  Library standings error: {e}")

    log(f"  Enriching via direct API...")
    try:
        api_standings = api_get("getStandings", {"leagueId": lid})
        if isinstance(api_standings, list):
            lookup = {r.get("teamName",""): r for r in api_standings}
            for entry in result["standings"]:
                api_row = lookup.get(entry["team_name"], {})
                entry["pf"] = api_row.get("totalPointsFor", 0)
                entry["win_pct"] = api_row.get("winPercentage", 0)
                entry["gb"] = api_row.get("gamesBack", 0)
                entry["fantrax_id"] = api_row.get("teamId", "")
    except Exception as e: log(f"  Enrichment error: {e}")

    try:
        info = api_get("getLeagueInfo", {"leagueId": lid})
        if isinstance(info, dict):
            for period in info.get("matchups", []):
                for mu in period.get("matchupList", []):
                    result["matchups"].append({"period": period.get("period",0), "away_name": mu.get("away",{}).get("name",""), "home_name": mu.get("home",{}).get("name","")})
            log(f"  {len(result['matchups'])} matchup pairings")
    except Exception as e: log(f"  Matchups error: {e}")

    # Matchup scores via library
    log(f"  Fetching matchup scores (library)...")
    try:
        scored_matchups, sched_meta = scrape_matchup_scores_library(lid)
        if scored_matchups:
            result["matchups"] = scored_matchups
            result["schedule_meta"] = sched_meta
            log(f"  {len(scored_matchups)} matchups with scores")
    except Exception as e:
        log(f"  Matchup scores error: {e}")

    # Build playoff bracket and compute final standings
    if result["standings"] and result["matchups"]:
        bracket = build_playoff_bracket(result["matchups"], result["standings"])
        result["playoff_bracket"] = bracket
        if bracket["status"] == "complete":
            result["standings"] = compute_final_standings(result["standings"], bracket)
            log(f"  Playoff bracket: complete — final standings updated")
        else:
            log(f"  Playoff bracket: {bracket['status']}")

    log(f"  Fetching rosters via library...")
    lib_fails = 0
    for team in league.teams:
        try:
            roster_obj = league.team_roster(team.id)
            players = []
            if hasattr(roster_obj, 'rows') and roster_obj.rows:
                for row in roster_obj.rows:
                    p = {}
                    if hasattr(row, 'player') and row.player:
                        p["name"] = getattr(row.player, 'name', str(row.player))
                        p["real_team"] = getattr(row.player, 'team_name', getattr(row.player, 'team_short_name', ''))
                        p["positions"] = getattr(row.player, 'pos_short_name', '')
                    else:
                        s = str(row)
                        if ":" in s: p["slot"], p["name"] = s.split(":", 1)[0].strip(), s.split(":", 1)[1].strip()
                        else: p["name"] = s
                    if hasattr(row, 'position') and row.position:
                        raw_slot = str(row.position).strip()
                        # Clean [###:X format from library
                        sm = re.match(r'\[?(\d+):([A-Za-z/]+)', raw_slot)
                        if sm:
                            code = sm.group(2)
                            # Map single-letter codes to proper positions
                            POS_CODES = {
                                "NBA":{"P":"PG","S":"SG","F":"F","C":"C","U":"Util","G":"G"},
                                "MLB":{"C":"C","R":"RP","S":"SP","D":"DH","U":"Util","O":"OF","1":"1B","2":"2B","3":"3B"},
                                "NFL":{"Q":"QB","R":"RB","W":"WR","T":"TE","K":"K","D":"D/ST","F":"Flex"},
                                "NHL":{"C":"C","L":"LW","R":"RW","D":"D","G":"G","S":"Sk"},
                            }
                            sport_map = POS_CODES.get(sport, {})
                            p["slot"] = sport_map.get(code, code)
                        else:
                            p["slot"] = raw_slot
                    p["position"] = p.get("slot") or p.get("positions") or ""
                    p["status"] = getattr(row, 'status', '') or ''
                    if p.get("name") and p["name"].lower() not in ("empty", ""): players.append(p)
            result["rosters"][team.id] = {"fantrax_id": team.id, "fantrax_name": team.name,
                "fed_id": resolve(team.name), "players": sort_roster(players, sport)}
            log(f"    {team.short}: {len(players)} players")
        except Exception as e:
            lib_fails += 1
            log(f"    {team.short}: library failed ({e})")
            result["rosters"][team.id] = {"fantrax_id": team.id, "fantrax_name": team.name,
                "fed_id": resolve(team.name), "players": [], "error": str(e)}

    if lib_fails >= len(league.teams) // 2:
        log(f"  {lib_fails}/{len(league.teams)} failed — falling back to direct API rosters...")
        try:
            api_rosters = api_get("getTeamRosters", {"leagueId": lid})
            rosters_data = api_rosters.get("rosters", {}) if isinstance(api_rosters, dict) else {}
            if rosters_data:
                player_names = _load_player_names(lid, cfg.get("sport_code", sport))
                for team_id, team_data in rosters_data.items():
                    tn = team_data.get("teamName", "")
                    players = _resolve_roster(team_data.get("rosterItems", []), player_names, sport)
                    result["rosters"][team_id] = {"fantrax_id": team_id, "fantrax_name": tn, "fed_id": resolve(tn), "players": players}
                log(f"  Direct API rosters: {len(rosters_data)} teams")
                result["method"] = "library+direct (rosters via API)"
        except Exception as e: log(f"  Direct API rosters also failed: {e}")
    return result

# ============================================================
# MATCHUP SCORES
# ============================================================
def scrape_matchup_scores_library(lid):
    """Fetch matchup scores using fantraxapi library's scoring_period_results().
    Works for NBA, NHL, MLB (not NFL due to 'Week' init bug).
    Returns (matchups_list, schedule_meta_dict).
    """
    league = League(lid)
    matchups = []
    meta = {"periods": {}}

    # Season
    try:
        results = league.scoring_period_results(season=True, playoffs=False)
        for period_num in sorted(results.keys()):
            spr = results[period_num]
            meta["periods"][str(period_num)] = {
                "start": spr.start.isoformat(), "end": spr.end.isoformat(),
                "complete": spr.complete, "current": spr.current, "is_playoff": False, "name": spr.name,
            }
            if spr.current:
                meta["current_period"] = period_num
            elif not meta.get("current_period") and spr.complete:
                meta["last_completed"] = period_num
            for mu in spr.matchups:
                away_name = mu.away.name if hasattr(mu.away, 'name') else str(mu.away)
                home_name = mu.home.name if hasattr(mu.home, 'name') else str(mu.home)
                matchups.append({
                    "period": period_num, "away_name": away_name, "away_fed_id": resolve(away_name),
                    "away_score": mu.away_score, "home_name": home_name, "home_fed_id": resolve(home_name),
                    "home_score": mu.home_score, "complete": spr.complete, "is_playoff": False,
                })
    except Exception as e:
        log(f"    Season scoring_period_results error: {e}")

    # Playoffs
    try:
        playoff_results = league.scoring_period_results(season=False, playoffs=True)
        for period_num in sorted(playoff_results.keys()):
            spr = playoff_results[period_num]
            meta["periods"][str(period_num)] = {
                "start": spr.start.isoformat(), "end": spr.end.isoformat(),
                "complete": spr.complete, "current": spr.current, "is_playoff": True, "name": spr.name,
            }
            if spr.current:
                meta["current_period"] = period_num
            for mu in spr.matchups:
                away_name = mu.away.name if hasattr(mu.away, 'name') else str(mu.away)
                home_name = mu.home.name if hasattr(mu.home, 'name') else str(mu.home)
                matchups.append({
                    "period": period_num, "away_name": away_name, "away_fed_id": resolve(away_name),
                    "away_score": mu.away_score, "home_name": home_name, "home_fed_id": resolve(home_name),
                    "home_score": mu.home_score, "complete": spr.complete, "is_playoff": True,
                })
    except Exception as e:
        log(f"    Playoff scoring_period_results error (may not have started): {type(e).__name__}")

    return matchups, meta


def scrape_matchup_scores_raw(lid):
    """Fetch matchup scores via raw POST API (for NFL where library can't init).
    Returns (matchups_list, schedule_meta_dict).
    """
    matchups = []
    meta = {"periods": {}}
    session = requests.Session()
    max_regular_period = 0  # Track highest regular season period for playoff offset

    for view, is_playoff in [("SCHEDULE", False), ("PLAYOFFS", True)]:
        try:
            json_data = {"msgs": [{"method": "getStandings", "data": {"leagueId": lid, "view": view}}]}
            resp = session.post("https://www.fantrax.com/fxpa/req", params={"leagueId": lid},
                                json=json_data, timeout=30)
            data = resp.json()
            if "pageError" in data:
                log(f"    Raw API {view} error: {data.get('pageError', {}).get('title', 'unknown')}")
                continue
            response_data = data["responses"][0]["data"]

            # Build team name map from fantasyTeamInfo
            team_map = {}
            for tid, tinfo in response_data.get("fantasyTeamInfo", {}).items():
                team_map[tid] = tinfo.get("name", "")

            for table in response_data.get("tableList", []):
                caption = table.get("caption", "")
                if caption == "Standings":
                    continue
                sub_caption = table.get("subCaption", "")

                # Parse period number from caption:
                #   NFL:       "Week 1", "Playoffs - Round 1 (Week 15)"
                #   NBA/NHL:   "Scoring Period 3", "Playoffs - Round 1 (Scoring Period 19)"
                #   Fallback:  first number found, or offset from max regular period for playoffs
                sp_match = re.search(r'Scoring Period\s+(\d+)', caption)
                week_match = re.search(r'Week\s+(\d+)', caption)
                if sp_match:
                    period_num = int(sp_match.group(1))
                elif week_match:
                    period_num = int(week_match.group(1))
                elif is_playoff and max_regular_period > 0:
                    # Playoff round without explicit period/week number —
                    # number sequentially after last regular season period
                    round_match = re.search(r'(\d+)', caption)
                    round_num = int(round_match.group(1)) if round_match else 1
                    period_num = max_regular_period + round_num
                else:
                    pnum_match = re.search(r'(\d+)', caption)
                    period_num = int(pnum_match.group(1)) if pnum_match else 0

                # Track max regular season period for playoff offset
                if not is_playoff and period_num > max_regular_period:
                    max_regular_period = period_num

                # Parse dates from subCaption: "(Thu Sep 10, 2026 - Wed Sep 16, 2026)"
                date_match = re.search(r'\(.*?(\w+ \d+, \d{4})\s*-\s*.*?(\w+ \d+, \d{4})\)', sub_caption)
                start_str = end_str = ""
                if date_match:
                    from datetime import datetime as dt
                    try:
                        start_d = dt.strptime(date_match.group(1), "%b %d, %Y").date()
                        end_d = dt.strptime(date_match.group(2), "%b %d, %Y").date()
                        start_str = start_d.isoformat()
                        end_str = end_d.isoformat()
                        now = dt.today().date()
                        is_complete = now > end_d
                        is_current = start_d <= now <= end_d
                    except ValueError:
                        is_complete = False; is_current = False
                else:
                    is_complete = False; is_current = False

                meta["periods"][str(period_num)] = {
                    "start": start_str, "end": end_str,
                    "complete": is_complete, "current": is_current,
                    "is_playoff": is_playoff, "name": caption,
                }
                if is_current:
                    meta["current_period"] = period_num
                elif not meta.get("current_period") and is_complete:
                    meta["last_completed"] = period_num

                for row in table.get("rows", []):
                    cells = row.get("cells", [])
                    if isinstance(cells, dict):
                        cells = [cells.get(str(k), {}) for k in range(max(int(x) for x in cells.keys()) + 1)] if cells else []
                    if len(cells) < 4:
                        continue
                    away_tid = cells[0].get("teamId", "")
                    away_name = team_map.get(away_tid, cells[0].get("content", ""))
                    away_score_raw = cells[1].get("content", "0")
                    home_tid = cells[2].get("teamId", "")
                    home_name = team_map.get(home_tid, cells[2].get("content", ""))
                    home_score_raw = cells[3].get("content", "0")
                    try:
                        away_score = float(str(away_score_raw).replace(",", ""))
                    except (ValueError, TypeError):
                        away_score = 0.0
                    try:
                        home_score = float(str(home_score_raw).replace(",", ""))
                    except (ValueError, TypeError):
                        home_score = 0.0
                    matchups.append({
                        "period": period_num, "away_name": away_name, "away_fed_id": resolve(away_name),
                        "away_score": away_score, "home_name": home_name, "home_fed_id": resolve(home_name),
                        "home_score": home_score, "complete": is_complete, "is_playoff": is_playoff,
                    })
        except Exception as e:
            log(f"    Raw API {view} error: {e}")

    return matchups, meta


# ============================================================
# PLAYOFF BRACKET & FINAL STANDINGS
# ============================================================
def build_playoff_bracket(matchups, standings):
    """Analyze playoff matchups to build a structured bracket and determine final positions 1-6.
    Returns dict with status, seeds, rounds, and final_standings_1_to_6."""
    playoff_mus = [m for m in matchups if m.get("is_playoff") and not m.get("is_consolation")]
    consolation_mus = [m for m in matchups if m.get("is_playoff") and m.get("is_consolation")]
    if not playoff_mus:
        return {"status": "not_started", "seeds": {}, "rounds": [], "final_standings_1_to_6": None}

    # Build seed map from top 6 regular season standings
    seed_map = {}
    for s in sorted(standings, key=lambda x: x.get("rank", 99)):
        yid = s.get("fed_id")
        if s.get("rank", 99) <= 6 and yid:
            seed_map[yid] = s["rank"]

    # Group by period, sorted ascending
    periods = sorted(set(m["period"] for m in playoff_mus))
    by_period = {p: [m for m in playoff_mus if m["period"] == p] for p in periods}

    rounds = []
    r1_winners = []
    r1_losers = []
    semi_winners = []
    semi_losers = []
    bye_teams = []

    def winner_loser(mu):
        if not mu.get("complete"):
            return None, None
        if mu["away_score"] > mu["home_score"]:
            return mu["away_fed_id"], mu["home_fed_id"]
        elif mu["home_score"] > mu["away_score"]:
            return mu["home_fed_id"], mu["away_fed_id"]
        else:
            # Tie: higher seed advances (shouldn't happen in fantasy playoffs)
            sa = seed_map.get(mu["away_fed_id"], 99)
            sh = seed_map.get(mu["home_fed_id"], 99)
            if sa < sh:
                return mu["away_fed_id"], mu["home_fed_id"]
            return mu["home_fed_id"], mu["away_fed_id"]

    # Process rounds by period
    for pi, period in enumerate(periods):
        mus = by_period[period]
        round_matchups = []

        for mu in mus:
            is_bye = (mu.get("away_fed_id") is None or mu.get("away_name", "").startswith("None"))
            entry = {
                "away_fed_id": mu.get("away_fed_id"),
                "away_name": mu.get("away_name", ""),
                "away_seed": seed_map.get(mu.get("away_fed_id"), None),
                "away_score": mu.get("away_score", 0),
                "home_fed_id": mu.get("home_fed_id"),
                "home_name": mu.get("home_name", ""),
                "home_seed": seed_map.get(mu.get("home_fed_id"), None),
                "home_score": mu.get("home_score", 0),
                "winner_fed_id": None,
                "loser_fed_id": None,
                "complete": mu.get("complete", False),
                "is_bye": is_bye,
                "period": period,
            }

            if is_bye:
                bye_team = mu.get("home_fed_id") or mu.get("away_fed_id")
                if bye_team and bye_team not in bye_teams:
                    bye_teams.append(bye_team)
            elif mu.get("complete"):
                w, l = winner_loser(mu)
                entry["winner_fed_id"] = w
                entry["loser_fed_id"] = l

                if pi == 0:  # Round 1
                    if w: r1_winners.append(w)
                    if l: r1_losers.append(l)
                elif pi == 1:  # Semifinals
                    if w: semi_winners.append(w)
                    if l: semi_losers.append(l)

            round_matchups.append(entry)

        # Determine round name
        if pi == 0:
            rname = "Round 1"
        elif pi == 1:
            rname = "Semifinals"
        elif pi == 2:
            rname = "Championship"
        else:
            rname = f"Round {pi + 1}"

        rounds.append({"name": rname, "period": period, "matchups": round_matchups})

    # Championship result
    champion = runner_up = None
    if len(periods) >= 3:
        champ_mus = by_period[periods[2]]
        real_champ = [m for m in champ_mus if not (m.get("away_fed_id") is None or m.get("away_name", "").startswith("None"))]
        if real_champ and real_champ[0].get("complete"):
            w, l = winner_loser(real_champ[0])
            champion = w
            runner_up = l
            # Update the round entry
            for rd in rounds:
                if rd["name"] == "Championship":
                    for me in rd["matchups"]:
                        if not me["is_bye"]:
                            me["winner_fed_id"] = w
                            me["loser_fed_id"] = l

    # Determine status
    all_complete = champion is not None
    any_complete = any(m.get("complete") for m in playoff_mus if not (m.get("away_fed_id") is None or m.get("away_name", "").startswith("None")))
    status = "complete" if all_complete else ("in_progress" if any_complete else "not_started")

    # Compute final standings 1-6
    final_standings = None
    if all_complete:
        final_standings = [
            {"fed_id": champion, "final_rank": 1, "reason": "Championship winner"},
            {"fed_id": runner_up, "final_rank": 2, "reason": "Championship loser"},
        ]
        # 3rd/4th: semi losers, higher reg season seed gets 3rd
        if len(semi_losers) == 2:
            sl = sorted(semi_losers, key=lambda yid: seed_map.get(yid, 99))
            final_standings.append({"fed_id": sl[0], "final_rank": 3, "reason": "Semi-final loser (higher seed)"})
            final_standings.append({"fed_id": sl[1], "final_rank": 4, "reason": "Semi-final loser (lower seed)"})
        # 5th/6th: R1 losers, higher reg season seed gets 5th
        if len(r1_losers) == 2:
            rl = sorted(r1_losers, key=lambda yid: seed_map.get(yid, 99))
            final_standings.append({"fed_id": rl[0], "final_rank": 5, "reason": "Round 1 loser (higher seed)"})
            final_standings.append({"fed_id": rl[1], "final_rank": 6, "reason": "Round 1 loser (lower seed)"})

        # Add consolation rounds to bracket display
        # Look for real consolation matchup data first
        consol_3rd = [m for m in consolation_mus if m.get("consolation_name") == "3rd Place"]
        consol_5th = [m for m in consolation_mus if m.get("consolation_name") == "5th Place"]

        if len(semi_losers) == 2:
            sl = sorted(semi_losers, key=lambda yid: seed_map.get(yid, 99))
            if consol_3rd:
                cm = consol_3rd[0]
                w, l = winner_loser(cm) if cm.get("complete") else (None, None)
                rounds.append({"name": "3rd Place", "period": cm.get("period", periods[-1] if periods else 0), "matchups": [{
                    "away_fed_id": cm.get("away_fed_id"), "away_name": cm.get("away_name", ""),
                    "away_seed": seed_map.get(cm.get("away_fed_id")),
                    "away_score": cm.get("away_score", 0),
                    "home_fed_id": cm.get("home_fed_id"), "home_name": cm.get("home_name", ""),
                    "home_seed": seed_map.get(cm.get("home_fed_id")),
                    "home_score": cm.get("home_score", 0),
                    "winner_fed_id": w, "loser_fed_id": l,
                    "complete": cm.get("complete", False), "is_bye": False,
                }]})
                # Update final standings based on actual consolation result
                if w and l:
                    final_standings = [fs for fs in final_standings if fs["final_rank"] not in (3, 4)]
                    final_standings.append({"fed_id": w, "final_rank": 3, "reason": "3rd place game winner"})
                    final_standings.append({"fed_id": l, "final_rank": 4, "reason": "3rd place game loser"})
            else:
                rounds.append({"name": "3rd Place", "period": periods[-1] if periods else 0, "matchups": [{
                    "away_fed_id": sl[0], "away_name": "", "away_seed": seed_map.get(sl[0]),
                    "away_score": 0, "home_fed_id": sl[1], "home_name": "", "home_seed": seed_map.get(sl[1]),
                    "home_score": 0, "winner_fed_id": sl[0], "loser_fed_id": sl[1],
                    "complete": True, "is_bye": False, "source": "inferred",
                }]})
        if len(r1_losers) == 2:
            rl = sorted(r1_losers, key=lambda yid: seed_map.get(yid, 99))
            if consol_5th:
                cm = consol_5th[0]
                w, l = winner_loser(cm) if cm.get("complete") else (None, None)
                rounds.append({"name": "5th Place", "period": cm.get("period", periods[-1] if periods else 0), "matchups": [{
                    "away_fed_id": cm.get("away_fed_id"), "away_name": cm.get("away_name", ""),
                    "away_seed": seed_map.get(cm.get("away_fed_id")),
                    "away_score": cm.get("away_score", 0),
                    "home_fed_id": cm.get("home_fed_id"), "home_name": cm.get("home_name", ""),
                    "home_seed": seed_map.get(cm.get("home_fed_id")),
                    "home_score": cm.get("home_score", 0),
                    "winner_fed_id": w, "loser_fed_id": l,
                    "complete": cm.get("complete", False), "is_bye": False,
                }]})
                # Update final standings based on actual consolation result
                if w and l:
                    final_standings = [fs for fs in final_standings if fs["final_rank"] not in (5, 6)]
                    final_standings.append({"fed_id": w, "final_rank": 5, "reason": "5th place game winner"})
                    final_standings.append({"fed_id": l, "final_rank": 6, "reason": "5th place game loser"})
            else:
                rounds.append({"name": "5th Place", "period": periods[-1] if periods else 0, "matchups": [{
                    "away_fed_id": rl[0], "away_name": "", "away_seed": seed_map.get(rl[0]),
                    "away_score": 0, "home_fed_id": rl[1], "home_name": "", "home_seed": seed_map.get(rl[1]),
                    "home_score": 0, "winner_fed_id": rl[0], "loser_fed_id": rl[1],
                    "complete": True, "is_bye": False, "source": "inferred",
                }]})

    return {"status": status, "seeds": seed_map, "rounds": rounds, "final_standings_1_to_6": final_standings}


def compute_final_standings(standings, playoff_bracket):
    """Merge regular season standings with playoff results to produce final standings.
    Overwrites rank with final_rank for positions 1-6 when playoffs are complete."""
    result = []
    for s in standings:
        entry = dict(s)
        entry["reg_season_rank"] = s["rank"]
        entry["playoff_result"] = None
        result.append(entry)

    if playoff_bracket.get("status") != "complete" or not playoff_bracket.get("final_standings_1_to_6"):
        for entry in result:
            entry["final_rank"] = entry["rank"]
        return result

    # Build final rank map from playoff bracket for positions 1-6
    final_map = {}
    result_labels = {1: "Champion", 2: "Runner-up", 3: "3rd Place", 4: "4th Place", 5: "5th Place", 6: "6th Place"}
    for fs in playoff_bracket["final_standings_1_to_6"]:
        final_map[fs["fed_id"]] = fs["final_rank"]

    # Teams 7-12: non-playoff teams ranked by regular season rank
    non_playoff = sorted([e for e in result if e.get("fed_id") not in final_map], key=lambda e: e["rank"])
    for i, entry in enumerate(non_playoff):
        final_map[entry["fed_id"]] = 7 + i

    # Apply final ranks
    for entry in result:
        yid = entry.get("fed_id")
        if yid in final_map:
            entry["final_rank"] = final_map[yid]
            entry["rank"] = final_map[yid]
            if final_map[yid] <= 6:
                entry["playoff_result"] = result_labels.get(final_map[yid], "Playoff")

    return sorted(result, key=lambda e: e.get("final_rank", e.get("rank", 99)))


# ============================================================
# SCHEDULE EXTRAS FROM GOOGLE SHEETS
# ============================================================
SCHEDULE_SHEET_ID = "YOUR_SCHEDULE_SHEET_ID"
SCHEDULE_SHEET_NAME = "Federation All-Time Schedule"
SHEET_LEAGUE_NAMES = {"FedFL": "fed_fl", "FedHL": "fed_hl", "FedBA": "fed_ba", "FedLB": "fed_lb"}

def scrape_schedule_extras():
    """Read the Google Sheet schedule tab to extract rivalry week labels per league.
    Returns dict: {league_key: {"rivalry_week": int_or_None}}.
    """
    log(f"  Fetching schedule extras from Google Sheet...")
    result = {}
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SCHEDULE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SCHEDULE_SHEET_NAME}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            log(f"    Schedule sheet HTTP {r.status_code}")
            return result
        rows = list(csv.reader(io.StringIO(r.text)))
        current_league = None
        for row in rows:
            if not row:
                current_league = None
                continue
            first = row[0].strip() if row[0] else ""
            # Detect league header rows (FedFL, FedHL, etc.)
            lk = SHEET_LEAGUE_NAMES.get(first)
            if lk:
                current_league = lk
                result.setdefault(current_league, {"rivalry_week": None})
                # Scan this header row for "Rivalry Week" labels
                for i, cell in enumerate(row[1:], 1):
                    cell_str = str(cell).strip()
                    match = re.search(r'Week\s+(\d+).*Rivalry', cell_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r'Rivalry', cell_str, re.IGNORECASE)
                    if match:
                        # The column index maps to week number: col B=Week1, C=Week2, etc.
                        # But the header row has "Week N (Rivalry Week)" so parse from cell text
                        wk_match = re.search(r'Week\s+(\d+)', cell_str)
                        if wk_match:
                            result[current_league]["rivalry_week"] = int(wk_match.group(1))
                            log(f"    {current_league}: rivalry week = {result[current_league]['rivalry_week']}")
                continue
        log(f"    Schedule extras: {len(result)} leagues")
    except Exception as e:
        log(f"    Schedule extras error: {e}")
    return result


# ============================================================
# DRAFT PICKS FROM GOOGLE SHEETS
# ============================================================
def scrape_draft_picks():
    log(f"  Fetching draft picks (trying {len(DRAFT_SEASONS)} seasons by name)...")
    all_picks = {}
    for season in DRAFT_SEASONS:
        try:
            url = f"https://docs.google.com/spreadsheets/d/{DRAFT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={season}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                log(f"    {season}: HTTP {r.status_code}"); continue
            rows = list(csv.reader(io.StringIO(r.text)))
            if not rows or len(rows) < 2:
                log(f"    {season}: empty"); continue
            picks = parse_draft_tab(rows)
            if picks:
                all_picks[season] = picks
                total = sum(len(v) for v in picks.values())
                log(f"    {season}: {total} picks across {len(picks)} leagues")
        except Exception as e: log(f"    {season}: error {e}")
    return all_picks

def parse_draft_tab(rows):
    picks = {}; current_league = None; col_teams = []; i = 0
    while i < len(rows):
        row = [c.strip() if isinstance(c, str) else c for c in rows[i]]
        first = row[0] if row else ""
        lk = SHEET_LEAGUE_MAP.get(first)
        if lk:
            current_league = lk; col_teams = [c.strip() for c in row[1:] if c.strip()]; picks[current_league] = []; i += 1; continue
        if current_league and first.startswith("Round"):
            m = re.match(r"Round\s+(\d+)", first)
            if m:
                rn = int(m.group(1)); owners = [c.strip() for c in row[1:1+len(col_teams)]]
                for j, ot in enumerate(col_teams):
                    co = owners[j] if j < len(owners) and owners[j] else ot
                    picks[current_league].append({"round": rn, "original_team": ot, "original_fed_id": resolve(ot),
                        "current_owner": co, "current_fed_id": resolve(co), "traded": co != ot})
            i += 1; continue
        if not first: current_league = None; col_teams = []
        i += 1
    return picks

def organize_picks_by_team(all_picks):
    by_team = {tid: {} for tid in FED_TEAMS}
    for season, leagues in all_picks.items():
        for lk, picks in leagues.items():
            for p in picks:
                owner = p.get("current_fed_id")
                if owner and owner in by_team:
                    by_team[owner].setdefault(season, {}).setdefault(lk, []).append(
                        {"round": p["round"], "original_team": p["original_team"],
                         "original_fed_id": p["original_fed_id"], "traded": p["traded"]})
    return by_team

# ============================================================
# FEDERATION STANDINGS
# ============================================================
def is_league_active(data):
    if not data or not data.get("standings"): return False
    return any((s.get("w",0) or 0) + (s.get("l",0) or 0) > 0 for s in data["standings"])

def compute_federation(fed_data, mode="active"):
    pts = {}
    for tid, m in FED_TEAMS.items():
        pts[tid] = {"team_id":tid, "owner":m["owner"], "name":m["name"], "abbr":m["abbr"],
                     "color":m["color"], "logo":m.get("logo",""), "total_fed_pts":0, "by_league":{},
                     "championships":0, "combined_w":0, "combined_l":0, "active_leagues":0}
    for lk in LEAGUES:
        data = fed_data.get(lk)
        if not data or not data.get("standings"): continue
        active = is_league_active(data)
        if mode == "active" and not active: continue
        for e in data["standings"]:
            yid = e.get("fed_id")
            if yid and yid in pts:
                r, w, l = e["rank"], e.get("w",0) or 0, e.get("l",0) or 0
                fp = 13 - r
                pts[yid]["total_fed_pts"] += fp
                pts[yid]["by_league"][lk] = {"rank":r, "fed_pts":fp, "w":w, "l":l, "pf":e.get("pf",0)}
                if r == 1: pts[yid]["championships"] += 1
                pts[yid]["combined_w"] += w; pts[yid]["combined_l"] += l; pts[yid]["active_leagues"] += 1
    s = sorted(pts.values(), key=lambda t:(t["total_fed_pts"], t["championships"],
        t["combined_w"]/max(t["combined_w"]+t["combined_l"],1)), reverse=True)
    for i,t in enumerate(s): t["federation_rank"] = i+1
    return s

# ============================================================
# DASHBOARD GENERATOR
# ============================================================
def generate_dashboard(combined, output_dir=None):
    template_path = SCRIPT_DIR / "dashboard.html"
    if not template_path.exists():
        log(f"  dashboard.html template not found — skipping"); return None
    log(f"  Generating dashboard_live.html...")
    html = template_path.read_text(encoding="utf-8")
    data_script = f'<script>window.FED_DATA = {json.dumps(combined, default=str)};</script>'
    html = html.replace('<!-- FED_DATA_PLACEHOLDER -->', data_script)
    out_path = SCRIPT_DIR / "dashboard_live.html"
    out_path.write_text(html, encoding="utf-8")
    log(f"  dashboard_live.html ({out_path.stat().st_size/1024:.1f} KB)")
    # Also write index.html to web root when using --output-dir (server deployment)
    if output_dir and output_dir.parent != SCRIPT_DIR:
        web_root = output_dir.parent
        idx_path = web_root / "index.html"
        idx_path.write_text(html, encoding="utf-8")
        log(f"  index.html ({idx_path.stat().st_size/1024:.1f} KB) -> {web_root}")
    return out_path

# ============================================================
# TRANSACTIONS
# ============================================================
def _parse_transaction_group(rows, team_name_lookup):
    """Parse a group of raw transaction rows (same txSetId) into a transaction dict."""
    first = rows[0]
    tx_id = first.get("txSetId", "")

    # Find cells by their 'key' field (cells is a list, and subsequent rows have fewer cells)
    cells = first.get("cells", [])
    if isinstance(cells, dict):
        cells = list(cells.values())
    cells_by_key = {}
    for c in cells:
        if isinstance(c, dict) and "key" in c:
            cells_by_key[c["key"]] = c

    # Team name from cell with key="team"
    team_cell = cells_by_key.get("team", {})
    team_id = team_cell.get("teamId", "")
    team_name = team_name_lookup.get(team_id, "") or team_cell.get("content", "")
    fed_id = resolve(team_name)

    # Date from cell with key="date"
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
            parsed_date = date_str  # keep raw string if no format matches

    # Players from each row in the group
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
        "players": players,
    }


def scrape_transactions(league_key, league_id, count=500):
    """Scrape transaction history via direct Fantrax API (bypasses buggy library classes).
    Returns a list of transaction dicts."""
    session = requests.Session()
    payload = {
        "msgs": [{
            "method": "getTransactionDetailsHistory",
            "data": {"leagueId": league_id, "maxResultsPerPage": str(count)},
        }]
    }
    try:
        resp = session.post(
            "https://www.fantrax.com/fxpa/req",
            params={"leagueId": league_id},
            json=payload, timeout=30,
        )
        resp_json = resp.json()
    except Exception as e:
        print(f"  Transaction API request failed for {league_key}: {e}")
        return []

    # Handle API-level errors (e.g. "Not Logged in")
    if "pageError" in resp_json:
        err = resp_json["pageError"]
        print(f"  Transaction API error for {league_key}: {err.get('title', err.get('code', 'unknown'))}")
        return []

    # Extract rows from response
    try:
        data = resp_json["responses"][0]["data"]
        rows = data.get("table", {}).get("rows", [])
    except (KeyError, IndexError) as e:
        print(f"  Unexpected transaction response for {league_key}: {e}")
        return []

    if not rows:
        return []

    # Team name lookup from fantasyTeamInfo
    team_lookup = {}
    for tid, tinfo in data.get("fantasyTeamInfo", {}).items():
        team_lookup[tid] = tinfo.get("name", "")

    # Group rows by txSetId
    grouped = []
    current = []
    for row in rows:
        if current and row.get("txSetId") != current[0].get("txSetId"):
            grouped.append(current)
            current = []
        current.append(row)
    if current:
        grouped.append(current)

    # Parse each group
    txns = []
    for group in grouped:
        try:
            txn = _parse_transaction_group(group, team_lookup)
            if txn:
                txns.append(txn)
        except Exception as e:
            print(f"     Skipping malformed transaction: {e}")

    return txns


def scrape_all_transactions():
    """Scrape transactions for all leagues and the previous NFL season.
    Returns dict keyed by season with league transactions."""
    results = {}

    # Current season leagues
    current_season = "2025-26"
    results[current_season] = {}
    for lk, cfg in LEAGUES.items():
        print(f"  {cfg['name']} transactions...")
        txns = scrape_transactions(lk, cfg["league_id"])
        if txns:
            results[current_season][lk] = {
                "league_name": cfg["name"],
                "sport": cfg["sport"],
                "transactions": txns,
            }
            print(f"     {len(txns)} transactions")
        else:
            print(f"     No transactions returned")

    return results


# ============================================================
# MAIN
# ============================================================
def main():
    print("="*60); print("  Federation Scraper v3.6"); print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"); print("="*60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_data = {}

    for lk, cfg in LEAGUES.items():
        print(f"\n{cfg['name']} ({cfg['sport']})...")
        data = None; method = cfg.get("method", "library")
        if method == "library" and HAS_LIB:
            try: data = scrape_library(lk, cfg)
            except Exception as e: print(f"  Library failed: {e}"); traceback.print_exc(); method = "direct"
        if data is None or method == "direct":
            try: data = scrape_direct(lk, cfg)
            except Exception as e: print(f"  Failed: {e}"); traceback.print_exc()
        all_data[lk] = data
        if data:
            st, ro = data.get("standings", []), sum(len(r.get("players",[])) for r in data.get("rosters",{}).values())
            tag = "ACTIVE" if is_league_active(data) else "NOT STARTED"
            print(f"  {tag} | {len(st)} standings, {ro} players [{data.get('method','')}]")
            for e in st[:3]:
                pf_str = f"  PF:{e['pf']:.1f}" if e.get('pf') else ""
                print(f"     {e.get('rank','?')}. {e.get('team_name','?')} ({e.get('w','?')}-{e.get('l','?')}){pf_str}")
            if len(st) > 3: print(f"     ... +{len(st)-3} more")
            for tid, r in list(data.get("rosters",{}).items())[:1]:
                ps = r.get("players",[])[:3]
                print(f"  Sample roster ({r.get('fantrax_name','?')}): {', '.join(p.get('name','?') for p in ps)}")

    # Previous NFL
    print(f"\nLoading previous NFL season...")
    nfl_prev_path = OUTPUT_DIR / NFL_PREV_FILE
    local_prev_path = SCRIPT_DIR / "data" / NFL_PREV_FILE
    nfl_prev = None
    if nfl_prev_path.exists():
        with open(nfl_prev_path, "r", encoding="utf-8") as f: nfl_prev = json.load(f)
        print(f"  Loaded {len(nfl_prev.get('standings',[]))} standings")
    elif local_prev_path.exists():
        with open(local_prev_path, "r", encoding="utf-8") as f: nfl_prev = json.load(f)
        print(f"  Loaded {len(nfl_prev.get('standings',[]))} standings (from scraper/data/)")
    else: print(f"  {NFL_PREV_FILE} not found")

    # Fetch prior NFL season matchup scores if missing or lacking scores
    prev_has_scores = nfl_prev and nfl_prev.get("matchups") and "away_score" in (nfl_prev["matchups"][0] if nfl_prev["matchups"] else {})
    if nfl_prev and not prev_has_scores:
        print(f"\nFetching prior NFL season matchup scores...")
        try:
            prev_mus, prev_meta = scrape_matchup_scores_raw(NFL_PREV_LEAGUE_ID)
            if prev_mus:
                nfl_prev["matchups"] = prev_mus
                nfl_prev["schedule_meta"] = prev_meta
                save_path = nfl_prev_path if nfl_prev_path.exists() else local_prev_path
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(nfl_prev, f, indent=2, default=str)
                print(f"  Got {len(prev_mus)} matchups, saved to {NFL_PREV_FILE}")
            else:
                print(f"  No matchups returned (league may require auth)")
        except Exception as e:
            print(f"  Prior NFL scores failed: {e}")

    # Build playoff bracket for previous NFL season
    if nfl_prev and nfl_prev.get("matchups") and nfl_prev.get("standings"):
        bracket = build_playoff_bracket(nfl_prev["matchups"], nfl_prev["standings"])
        nfl_prev["playoff_bracket"] = bracket
        if bracket["status"] == "complete":
            nfl_prev["standings"] = compute_final_standings(nfl_prev["standings"], bracket)
            print(f"  Previous NFL playoff bracket: complete — final standings updated")
        else:
            print(f"  Playoff bracket: {bracket['status']}")

    # Schedule extras (rivalry week labels from Google Sheet)
    print(f"\nScraping schedule extras...")
    schedule_extras = {}
    try:
        schedule_extras = scrape_schedule_extras()
        for lk, extras in schedule_extras.items():
            if lk in all_data and all_data[lk]:
                sm = all_data[lk].get("schedule_meta", {})
                sm["rivalry_week"] = extras.get("rivalry_week")
                all_data[lk]["schedule_meta"] = sm
        if schedule_extras:
            rw_info = ", ".join(f"{lk}=Wk{e.get('rivalry_week')}" for lk, e in schedule_extras.items() if e.get("rivalry_week"))
            print(f"  Rivalry weeks: {rw_info or 'none found'}")
        else:
            print(f"  No schedule extras (sheet may be private)")
    except Exception as e: print(f"  Schedule extras failed: {e}")

    # Draft picks
    print(f"\nScraping draft picks ({len(DRAFT_SEASONS)} seasons)...")
    draft_picks = draft_by_team = {}
    try:
        draft_picks = scrape_draft_picks()
        if draft_picks:
            draft_by_team = organize_picks_by_team(draft_picks)
            total = sum(sum(len(v) for v in leagues.values()) for leagues in draft_picks.values())
            print(f"  {total} picks across {len(draft_picks)} seasons")
        else: print(f"  No picks (sheet may be private)")
    except Exception as e: print(f"  Draft picks failed: {e}")

    # Transactions
    print(f"\nScraping transactions...")
    transactions = {}
    try:
        transactions = scrape_all_transactions()
        for season, leagues in transactions.items():
            tx_path = OUTPUT_DIR / f"transactions_{season}.json"
            # Preserve one-time data (e.g., fed_fl_prev) from existing file
            if tx_path.exists():
                try:
                    with open(tx_path, "r", encoding="utf-8") as f:
                        existing_leagues = json.load(f).get("leagues", {})
                    for ek, ev in existing_leagues.items():
                        if ek not in leagues:
                            leagues[ek] = ev
                            print(f"  Preserved existing {ek} ({len(ev.get('transactions', []))} transactions)")
                except Exception:
                    pass
            tx_data = {"season": season, "scraped_at": datetime.now().isoformat(), "teams": FED_TEAMS, "leagues": leagues}
            with open(tx_path, "w", encoding="utf-8") as f:
                json.dump(tx_data, f, indent=2, default=str)
            total = sum(len(ld.get("transactions", [])) for ld in leagues.values())
            print(f"  {season}: {total} transactions saved to {tx_path.name}")
    except Exception as e:
        print(f"  Transactions failed: {e}")
        traceback.print_exc()

    # Federation
    fed_data = dict(all_data)
    if not is_league_active(all_data.get("fed_fl")) and nfl_prev and nfl_prev.get("standings"):
        fed_data["fed_fl"] = nfl_prev; print(f"\nUsing previous NFL season for federation")

    print(f"\nComputing Federation Standings...")
    fed_active = compute_federation(fed_data, mode="active")
    fed_all = compute_federation(fed_data, mode="all")
    active_leagues = [lk for lk in LEAGUES if is_league_active(fed_data.get(lk))]
    print(f"  Active: {', '.join(LEAGUES[lk]['sport'] for lk in active_leagues) or 'none'}")

    for lk, data in all_data.items():
        if data:
            with open(OUTPUT_DIR/f"{lk}.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=2, default=str)

    combined = {"scraped_at": datetime.now().isoformat(), "scraper_version": "3.6",
        "federation_season": "2025-26", "teams": FED_TEAMS, "team_name_map": TEAM_NAME_MAP,
        "leagues": {k:{"name":v["name"],"sport":v["sport"],"league_id":v["league_id"]} for k,v in LEAGUES.items()},
        "league_data": {k:v for k,v in all_data.items() if v}, "nfl_previous_season": nfl_prev,
        "federation_standings": fed_active, "federation_standings_all": fed_all,
        "draft_picks": draft_picks, "draft_picks_by_team": draft_by_team}
    with open(OUTPUT_DIR/"fed_combined.json", "w", encoding="utf-8") as f: json.dump(combined, f, indent=2, default=str)

    dash_path = generate_dashboard(combined, OUTPUT_DIR)
    print(f"\nSaved to {OUTPUT_DIR.resolve()}/")
    for fp in sorted(OUTPUT_DIR.glob("*.json")): print(f"   {fp.name} ({fp.stat().st_size/1024:.1f} KB)")
    if dash_path: print(f"   {dash_path.name} ({dash_path.stat().st_size/1024:.1f} KB)")

    print(f"\n{'='*72}"); print(f"  Federation Standings ({len(active_leagues)}/{len(LEAGUES)} active)"); print(f"{'='*72}")
    print(f"  {'Rk':>3}  {'Team':<26} {'Pts':>4}  {'NFL':>7} {'NBA':>7} {'NHL':>7} {'MLB':>7}  {'W':>3}-{'L':<3}")
    print(f"  {'-'*72}")
    for t in fed_active:
        ln = f"  {t['federation_rank']:>3}  {t['name']:<26} {t['total_fed_pts']:>4}"
        for lk in LEAGUES:
            bl = t["by_league"].get(lk,{})
            r = bl.get("rank")
            ln += f"  {bl['fed_pts']:>2}({r:>2})" if r else f"  {'---':>7}"
            ln += f"  {t['combined_w']:>3}-{t['combined_l']:<3}"
        print(ln)
    print(f"\nDone! Open dashboard_live.html in your browser.")

if __name__ == "__main__": main()
