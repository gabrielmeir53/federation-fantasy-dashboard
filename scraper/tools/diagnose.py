"""
Federation Diagnostic Script
=====================
Run this FIRST to discover what attributes the fantraxapi objects
actually have on your installed version, then we'll fix the scraper.

Usage:
    python diagnose.py
"""

from fantraxapi import League
import json

# Test with one league that connected (NBA worked past the connection)
LEAGUES = {
    "fed_ba": "YOUR_NBA_LEAGUE_ID",   # NBA - connected OK
    "fed_hl": "YOUR_NHL_LEAGUE_ID",   # NHL
    "fed_lb": "YOUR_MLB_LEAGUE_ID",   # MLB
    "fed_fl": "YOUR_NFL_LEAGUE_ID",   # NFL - had parsing error
}

def safe_attrs(obj):
    """Get all non-dunder attributes of an object."""
    return {a: repr(getattr(obj, a, "N/A"))[:100] for a in dir(obj) if not a.startswith("_")}

def inspect_league(name, league_id):
    print(f"\n{'='*60}")
    print(f"  {name} (ID: {league_id})")
    print(f"{'='*60}")

    try:
        league = League(league_id)
        print(f"  ✅ Connected!")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return

    # --- League object ---
    print(f"\n  --- League attributes ---")
    for k, v in safe_attrs(league).items():
        print(f"    {k}: {v}")

    # --- Teams ---
    print(f"\n  --- Teams ---")
    print(f"    league.teams type: {type(league.teams)}")
    if hasattr(league, 'teams') and league.teams:
        team = league.teams[0]
        print(f"    First team type: {type(team)}")
        print(f"    First team repr: {repr(team)[:200]}")
        print(f"\n    All attributes of Team object:")
        for k, v in safe_attrs(team).items():
            print(f"      {k}: {v}")

        print(f"\n    All {len(league.teams)} teams:")
        for t in league.teams:
            # Try various ways to get the name and ID
            tid = getattr(t, 'team_id', getattr(t, 'id', getattr(t, 'key', '???')))
            tname = getattr(t, 'name', getattr(t, 'team_name', str(t)))
            print(f"      ID={tid}  Name={tname}")
    else:
        print("    No teams found or teams attribute missing")

    # --- Standings ---
    print(f"\n  --- Standings ---")
    try:
        standings = league.standings()
        print(f"    standings() type: {type(standings)}")
        if standings:
            if isinstance(standings, dict):
                print(f"    Dict with {len(standings)} keys: {list(standings.keys())[:5]}")
                first_key = list(standings.keys())[0]
                first_val = standings[first_key]
                print(f"    First value type: {type(first_val)}")
                print(f"    First value repr: {repr(first_val)[:200]}")
                if hasattr(first_val, '__dict__'):
                    print(f"    First value attrs:")
                    for k, v in safe_attrs(first_val).items():
                        print(f"      {k}: {v}")
            elif isinstance(standings, list):
                print(f"    List with {len(standings)} items")
                first = standings[0]
                print(f"    First item type: {type(first)}")
                print(f"    First item repr: {repr(first)[:200]}")
                if hasattr(first, '__dict__'):
                    print(f"    First item attrs:")
                    for k, v in safe_attrs(first).items():
                        print(f"      {k}: {v}")
            else:
                print(f"    Value: {repr(standings)[:500]}")
        else:
            print(f"    Empty or None")
    except Exception as e:
        print(f"    ❌ standings() failed: {e}")

    # --- Scoring Periods ---
    print(f"\n  --- Scoring Periods ---")
    try:
        periods = league.scoring_periods()
        print(f"    scoring_periods() type: {type(periods)}")
        if periods:
            print(f"    Count: {len(periods)}")
            first_key = list(periods.keys())[0]
            first_val = periods[first_key]
            print(f"    First key: {first_key}")
            print(f"    First value type: {type(first_val)}")
            if hasattr(first_val, '__dict__'):
                print(f"    First value attrs:")
                for k, v in safe_attrs(first_val).items():
                    print(f"      {k}: {v}")
    except Exception as e:
        print(f"    ❌ scoring_periods() failed: {e}")

    # --- Transactions ---
    print(f"\n  --- Transactions ---")
    try:
        txns = league.transactions()
        print(f"    transactions() type: {type(txns)}")
        if txns:
            print(f"    Count: {len(txns)}")
            first = txns[0]
            print(f"    First type: {type(first)}")
            if hasattr(first, '__dict__'):
                print(f"    First attrs:")
                for k, v in safe_attrs(first).items():
                    print(f"      {k}: {v}")
    except Exception as e:
        print(f"    ❌ transactions() failed: {e}")

    # --- Team Roster (first team) ---
    if hasattr(league, 'teams') and league.teams:
        print(f"\n  --- Roster (first team) ---")
        team = league.teams[0]
        tid = getattr(team, 'team_id', getattr(team, 'id', getattr(team, 'key', None)))
        if tid:
            try:
                roster = league.team_roster(tid)
                print(f"    team_roster() type: {type(roster)}")
                print(f"    roster repr: {repr(roster)[:200]}")
                if hasattr(roster, '__dict__'):
                    print(f"    roster attrs:")
                    for k, v in safe_attrs(roster).items():
                        print(f"      {k}: {v}")
            except Exception as e:
                print(f"    ❌ team_roster() failed: {e}")
        else:
            print(f"    Cannot get team ID to fetch roster")

    # --- Matchups ---
    print(f"\n  --- Matchups ---")
    try:
        matchups = league.matchups()
        print(f"    matchups() type: {type(matchups)}")
        if matchups:
            if isinstance(matchups, list):
                print(f"    Count: {len(matchups)}")
                first = matchups[0]
            elif isinstance(matchups, dict):
                first_key = list(matchups.keys())[0]
                first = matchups[first_key]
                print(f"    Dict keys: {list(matchups.keys())[:5]}")
            else:
                first = matchups
            print(f"    First type: {type(first)}")
            if hasattr(first, '__dict__'):
                print(f"    First attrs:")
                for k, v in safe_attrs(first).items():
                    print(f"      {k}: {v}")
    except Exception as e:
        print(f"    ❌ matchups() failed: {e}")

    # --- Trades ---
    print(f"\n  --- Trades ---")
    try:
        trades = league.trades()
        print(f"    trades() type: {type(trades)}")
        if trades:
            print(f"    Count: {len(trades)}")
            first = trades[0] if isinstance(trades, list) else list(trades.values())[0]
            print(f"    First type: {type(first)}")
            if hasattr(first, '__dict__'):
                print(f"    First attrs:")
                for k, v in safe_attrs(first).items():
                    print(f"      {k}: {v}")
    except Exception as e:
        print(f"    ❌ trades() failed: {e}")


if __name__ == "__main__":
    print("Federation Fantrax API Diagnostic")
    print("=" * 60)

    # Check version
    import fantraxapi
    print(f"fantraxapi version: {getattr(fantraxapi, '__version__', 'unknown')}")
    print(f"fantraxapi location: {fantraxapi.__file__}")

    # Try each league (start with ones that partially worked)
    for name, lid in LEAGUES.items():
        try:
            inspect_league(name, lid)
        except Exception as e:
            print(f"\n  💥 FATAL for {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("  DIAGNOSTIC COMPLETE")
    print("  Copy/paste this entire output and send it back!")
    print(f"{'='*60}")
