"""
Federation Selenium Fallback Scraper
==============================
Uses Selenium + Firefox to scrape Fantrax pages directly.
Use this if the fantraxapi library doesn't return complete data
for a specific league.

Requirements:
    pip install selenium webdriver-manager beautifulsoup4

Firefox must be installed on your system.
geckodriver is auto-managed by webdriver-manager.

Usage:
    python scrape_selenium.py
    python scrape_selenium.py --league fed_fl    # Scrape only one league
"""

import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.firefox import GeckoDriverManager
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: pip install selenium webdriver-manager beautifulsoup4")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed.")
    print("Run: pip install beautifulsoup4")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
LEAGUES = {
    "fed_fl": {"league_id": "YOUR_NFL_LEAGUE_ID", "name": "FedFL", "sport": "NFL"},
    "fed_ba": {"league_id": "YOUR_NBA_LEAGUE_ID", "name": "FedBA", "sport": "NBA"},
    "fed_hl": {"league_id": "YOUR_NHL_LEAGUE_ID", "name": "FedHL", "sport": "NHL"},
    "fed_lb": {"league_id": "YOUR_MLB_LEAGUE_ID", "name": "FedLB", "sport": "MLB"},
}

OUTPUT_DIR = Path(__file__).parent / "data"
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv
TARGET_LEAGUE = None

# Parse --league argument
for i, arg in enumerate(sys.argv):
    if arg == "--league" and i + 1 < len(sys.argv):
        TARGET_LEAGUE = sys.argv[i + 1]


def create_driver():
    """Create a headless Firefox driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    # Reduce detection
    options.set_preference("general.useragent.override",
                           "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")

    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver


def wait_for_page(driver, timeout=15):
    """Wait for Fantrax's dynamic content to load."""
    time.sleep(3)  # Initial wait for JS framework
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(2)  # Extra wait for React/Angular rendering


def scrape_standings_page(driver, league_id):
    """Scrape the standings page for a league."""
    url = f"https://www.fantrax.com/fantasy/league/{league_id}/standings"
    print(f"    Loading {url}...")
    driver.get(url)
    wait_for_page(driver)

    standings = []
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Fantrax renders standings in a table - look for common patterns
    # The exact selectors depend on the current Fantrax UI version
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 3:  # Need header + at least 2 data rows
            continue

        # Check if this looks like a standings table
        header = rows[0]
        header_text = header.get_text().lower()
        if any(kw in header_text for kw in ["team", "w", "l", "pct", "pts", "record"]):
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue
                # Try to extract data from cells
                row_data = [cell.get_text(strip=True) for cell in cells]
                standings.append(row_data)

    # Also try to find data in divs (Fantrax sometimes uses div-based layouts)
    if not standings:
        # Look for team name elements
        team_elements = soup.select("[class*='team'], [class*='Team']")
        if team_elements:
            print(f"    Found {len(team_elements)} team elements (div-based layout)")

    return standings


def scrape_roster_page(driver, league_id):
    """Scrape all team rosters."""
    # First get the teams list
    url = f"https://www.fantrax.com/fantasy/league/{league_id}/teams"
    print(f"    Loading teams page...")
    driver.get(url)
    wait_for_page(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find team links
    team_links = []
    links = soup.find_all("a", href=True)
    for link in links:
        href = link.get("href", "")
        if "teamId=" in href or "/team/" in href:
            team_links.append({
                "name": link.get_text(strip=True),
                "url": href if href.startswith("http") else f"https://www.fantrax.com{href}",
            })

    rosters = {}
    for team_link in team_links:
        print(f"    Loading roster: {team_link['name']}...")
        try:
            driver.get(team_link["url"])
            wait_for_page(driver)

            roster_soup = BeautifulSoup(driver.page_source, "html.parser")
            tables = roster_soup.find_all("table")

            players = []
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        player_name = cells[0].get_text(strip=True) if cells else ""
                        if player_name and player_name not in ["", "Empty", "--"]:
                            players.append({
                                "name": player_name,
                                "cells": [c.get_text(strip=True) for c in cells],
                            })

            rosters[team_link["name"]] = players
        except Exception as e:
            print(f"    ERROR scraping {team_link['name']}: {e}")

    return rosters


def scrape_transactions_page(driver, league_id):
    """Scrape recent transactions."""
    url = f"https://www.fantrax.com/fantasy/league/{league_id}/transactions"
    print(f"    Loading transactions...")
    driver.get(url)
    wait_for_page(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    transactions = []

    # Look for transaction rows
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                txn_data = [c.get_text(strip=True) for c in cells]
                transactions.append(txn_data)

    return transactions


def scrape_league_selenium(league_key, config):
    """Full scrape of one league using Selenium."""
    print(f"\n🌐 Selenium scrape: {config['name']} ({config['sport']})")

    driver = create_driver()
    result = {
        "league_key": league_key,
        "name": config["name"],
        "sport": config["sport"],
        "scraped_at": datetime.now().isoformat(),
        "method": "selenium",
        "standings_raw": [],
        "rosters_raw": {},
        "transactions_raw": [],
    }

    try:
        # Standings
        print("  📊 Scraping standings...")
        result["standings_raw"] = scrape_standings_page(driver, config["league_id"])
        print(f"    Found {len(result['standings_raw'])} standings rows")

        # Rosters
        print("  👥 Scraping rosters...")
        result["rosters_raw"] = scrape_roster_page(driver, config["league_id"])
        print(f"    Found rosters for {len(result['rosters_raw'])} teams")

        # Transactions
        print("  📝 Scraping transactions...")
        result["transactions_raw"] = scrape_transactions_page(driver, config["league_id"])
        print(f"    Found {len(result['transactions_raw'])} transactions")

        # Save page source for debugging
        if VERBOSE:
            debug_dir = OUTPUT_DIR / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)

            driver.get(f"https://www.fantrax.com/fantasy/league/{config['league_id']}/standings")
            wait_for_page(driver)
            with open(debug_dir / f"{league_key}_standings.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"    Debug HTML saved to {debug_dir}/")

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

    return result


def main():
    print("=" * 60)
    print("  Federation Selenium Fallback Scraper")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    leagues_to_scrape = LEAGUES
    if TARGET_LEAGUE:
        if TARGET_LEAGUE in LEAGUES:
            leagues_to_scrape = {TARGET_LEAGUE: LEAGUES[TARGET_LEAGUE]}
        else:
            print(f"Unknown league: {TARGET_LEAGUE}")
            print(f"Available: {', '.join(LEAGUES.keys())}")
            sys.exit(1)

    for league_key, config in leagues_to_scrape.items():
        result = scrape_league_selenium(league_key, config)

        # Save raw data
        path = OUTPUT_DIR / f"{league_key}_selenium.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  ✅ Saved to {path}")

    print(f"\n✅ Done! Raw data saved to {OUTPUT_DIR}/")
    print("Review the _selenium.json files and the debug HTML to verify data quality.")
    print("If the data looks good, you can integrate it into the main scraper.")


if __name__ == "__main__":
    main()
