"""
Test script to validate fantraxapi scoring_period_results() returns matchup scores.
Tests NBA (library) and NFL (raw POST API since library can't init NFL).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import requests
from fantraxapi import League

LEAGUES = {
    "NBA": "YOUR_NBA_LEAGUE_ID",
    "NFL": "YOUR_NFL_LEAGUE_ID",
}


def test_library(sport, lid):
    """Test using the fantraxapi library (works for NBA/NHL/MLB)."""
    print(f"\n{'='*60}")
    print(f"Testing {sport} via LIBRARY")
    print(f"{'='*60}")
    try:
        league = League(lid)
        print(f"Connected: {league.name} ({league.year})")
    except Exception as e:
        print(f"FAILED to connect: {e}")
        return

    print(f"\nFetching scoring_period_results(season=True, playoffs=False)...")
    try:
        results = league.scoring_period_results(season=True, playoffs=False)
        print(f"Got {len(results)} scoring periods")

        for period_num in sorted(results.keys())[:2]:
            spr = results[period_num]
            status = "COMPLETE" if spr.complete else "CURRENT" if spr.current else "FUTURE"
            print(f"\n  Period {period_num}: {spr.name} ({status})")
            print(f"    Dates: {spr.start} to {spr.end}")
            for mu in spr.matchups:
                away_name = mu.away.name if hasattr(mu.away, 'name') else str(mu.away)
                home_name = mu.home.name if hasattr(mu.home, 'name') else str(mu.home)
                print(f"      {away_name} ({mu.away_score}) vs {home_name} ({mu.home_score})")

        completed = {k: v for k, v in results.items() if v.complete}
        if completed:
            last_num = max(completed.keys())
            last = completed[last_num]
            print(f"\n  LAST COMPLETED - Period {last_num}: {last.name}")
            for mu in last.matchups:
                away_name = mu.away.name if hasattr(mu.away, 'name') else str(mu.away)
                home_name = mu.home.name if hasattr(mu.home, 'name') else str(mu.home)
                print(f"      {away_name} ({mu.away_score}) vs {home_name} ({mu.home_score})")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback; traceback.print_exc()

    print(f"\nFetching playoffs...")
    try:
        playoff_results = league.scoring_period_results(season=False, playoffs=True)
        print(f"Got {len(playoff_results)} playoff periods")
    except Exception as e:
        print(f"Playoffs not available yet: {type(e).__name__}")


def test_raw_api(sport, lid):
    """Test using raw POST API (for NFL where library can't init)."""
    print(f"\n{'='*60}")
    print(f"Testing {sport} via RAW API")
    print(f"{'='*60}")

    session = requests.Session()

    # SEASON schedule
    json_data = {"msgs": [{"method": "getStandings", "data": {"leagueId": lid, "view": "SCHEDULE"}}]}
    resp = session.post("https://www.fantrax.com/fxpa/req", params={"leagueId": lid}, json=json_data, timeout=30)
    print(f"Status: {resp.status_code}")
    data = resp.json()

    if "pageError" in data:
        print(f"API Error: {data['pageError']}")
        return

    response_data = data["responses"][0]["data"]

    # Team mapping
    team_map = {}
    if "fantasyTeamInfo" in response_data:
        for tid, tinfo in response_data["fantasyTeamInfo"].items():
            team_map[tid] = tinfo.get("name", "?")
        print(f"Teams: {len(team_map)}")

    # Schedule data
    table_list = response_data.get("tableList", [])
    print(f"Scoring periods: {len(table_list)}")

    for i, table in enumerate(table_list[:3]):
        caption = table.get("caption", "?")
        sub = table.get("subCaption", "")
        rows = table.get("rows", [])
        print(f"\n  [{i}] {caption} - {sub} ({len(rows)} matchups)")
        for row in rows:
            cells = row.get("cells", [])
            if isinstance(cells, dict):
                cells = [cells.get(k, {}) for k in sorted(cells.keys(), key=int)]
            if len(cells) >= 4:
                away_name = cells[0].get("content", "?")
                away_score = cells[1].get("content", "?")
                home_name = cells[2].get("content", "?")
                home_score = cells[3].get("content", "?")
                print(f"      {away_name} ({away_score}) vs {home_name} ({home_score})")

    # Last period
    if table_list:
        last = table_list[-1]
        caption = last.get("caption", "?")
        sub = last.get("subCaption", "")
        rows = last.get("rows", [])
        print(f"\n  LAST: {caption} - {sub} ({len(rows)} matchups)")
        for row in rows:
            cells = row.get("cells", [])
            if isinstance(cells, dict):
                cells = [cells.get(k, {}) for k in sorted(cells.keys(), key=int)]
            if len(cells) >= 4:
                away_name = cells[0].get("content", "?")
                away_score = cells[1].get("content", "?")
                home_name = cells[2].get("content", "?")
                home_score = cells[3].get("content", "?")
                print(f"      {away_name} ({away_score}) vs {home_name} ({home_score})")

    # PLAYOFFS
    print(f"\nTrying PLAYOFFS view...")
    playoff_json = {"msgs": [{"method": "getStandings", "data": {"leagueId": lid, "view": "PLAYOFFS"}}]}
    resp2 = session.post("https://www.fantrax.com/fxpa/req", params={"leagueId": lid}, json=playoff_json, timeout=30)
    pdata = resp2.json()
    if "pageError" not in pdata:
        presponse = pdata["responses"][0]["data"]
        ptables = presponse.get("tableList", [])
        print(f"Playoff entries: {len(ptables)}")
        for pt in ptables:
            cap = pt.get("caption", "?")
            if cap == "Standings":
                continue
            sub = pt.get("subCaption", "")
            rows = pt.get("rows", [])
            print(f"  {cap} - {sub} ({len(rows)} matchups)")
            for row in rows:
                cells = row.get("cells", [])
                if isinstance(cells, dict):
                    cells = [cells.get(k, {}) for k in sorted(cells.keys(), key=int)]
                if len(cells) < 4:
                    continue
                away_name = cells[0].get("content", "?")
                away_score = cells[1].get("content", "?")
                home_name = cells[2].get("content", "?")
                home_score = cells[3].get("content", "?")
                print(f"      {away_name} ({away_score}) vs {home_name} ({home_score})")
    else:
        print(f"Playoffs error: {pdata.get('pageError')}")


if __name__ == "__main__":
    test_library("NBA", LEAGUES["NBA"])
    test_raw_api("NFL", LEAGUES["NFL"])
    print("\nDone!")
