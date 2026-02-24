# Multi-Sport Fantasy Federation Dashboard

A data scraper and dashboard for running **multi-sport dynasty fantasy leagues** on [Fantrax](https://www.fantrax.com). Supports NFL, NBA, NHL, and MLB with combined federation standings, interactive playoff brackets, team profiles, transaction logs, and more.

Run four simultaneous Fantrax leagues with 12 teams where each owner manages a franchise across all four major North American sports. The **Federation** standings combine performance across all sports by awarding federation points per league based on final rank.

> **Built with:** Python 3.9+ (scraper) | Vanilla HTML/CSS/JS (dashboard) | No frameworks, no build step

---

![Dashboard Screenshot](https://via.placeholder.com/1200x600.png?text=Add+your+own+screenshot+here)

*Add your own screenshot here -- replace this placeholder with a screenshot of your dashboard.*

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration Guide](#configuration-guide)
  - [Setting Up Your Fantrax Leagues](#setting-up-your-fantrax-leagues)
  - [Configuring Your Teams](#configuring-your-teams)
  - [Google Sheets Setup (Optional)](#google-sheets-setup-optional)
  - [Season Configuration](#season-configuration)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Deployment Guide](#deployment-guide)
  - [Local Development](#local-development)
  - [cPanel Deployment](#cpanel-deployment)
  - [Other Hosting](#other-hosting)
- [Customization Guide](#customization-guide)
  - [Changing Team Count](#changing-team-count)
  - [Changing Sports](#changing-sports)
  - [Theming](#theming)
  - [Adding Your Constitution](#adding-your-constitution)
- [Federation Points](#federation-points)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Federation Standings
- Combined rankings across all 4 leagues (NFL, NBA, NHL, MLB)
- Federation points awarded 1--12 per league based on final rank
- Tiebreaker resolution: championships, then combined win percentage, then average points for, then head-to-head record
- Toggle between "active leagues only" and "all leagues" modes
- Season badge and overall championship tracking

### Per-League Dashboards
- Full standings table with W/L/T record, points for, win percentage, and games back
- Stat cards showing league-wide summaries (top scorer, best record, etc.)
- Current week/scoring period indicator
- Playoff-adjusted rankings (asterisk marks positions determined by playoffs)
- When a season's playoffs are complete, final standings reflect playoff results

### Team Profiles
- Click any team row to expand a full detail view
- Complete roster sorted by position in sport-standard order (e.g., NFL: QB, RB, WR, TE, Flex, D/ST, K)
- Head-to-head record against every other team in the league
- Season schedule with week-by-week results (W/L/T, scores, opponent)
- Draft capital tracker showing picks for up to 8 future seasons across all leagues
- Traded pick highlighting (visual indicator for picks acquired via trade)

### Interactive Playoff Brackets
- Bracket visualization for completed and in-progress playoffs
- Championship round, semifinals, and first round
- Consolation rounds for 3rd place and 5th place
- Supports 6-team playoff format (top 6 qualify; seeds 1 and 2 receive first-round byes)
- Score display for completed matchups with winner highlighting
- Final standings summary (1st through 6th place with reason labels)

### Transaction Log
- Chronological list of all trades, adds, drops, and waiver claims across all leagues
- Sidebar filters: season, league, team, transaction type
- Free-text search across player names
- Separate page (`transactions.html`) with its own navigation
- Mobile-responsive with collapsible filter sidebar

### Schedule Viewer
- Week-by-week matchup grid for each league
- Color-coded results (green for wins, red for losses, gold for ties)
- Rivalry week markers pulled from Google Sheets metadata (red dot indicator)
- Current week highlighting with a "Jump to Current" button
- Period date ranges shown for each week
- Status badges: Final, Live, Upcoming

### Constitution / Rules Page
- Fully customizable league rules, bylaws, and amendments
- Real-time searchable with match highlighting
- Auto-generated table of contents with section links
- Separate page (`constitution.html`) linked from the main dashboard navigation

### Navigation and UX
- Sticky top nav with league tabs and per-league logo icons
- Mobile hamburger menu with responsive layout
- Dark theme using CSS custom properties throughout
- "Last updated" timestamp from the most recent scraper run
- Smooth animations and transitions (fade-in on expand, hover states)
- Three Google Fonts: Oswald (headings), Source Sans 3 (body), JetBrains Mono (data/numbers)

### Automated Data Scraping
- Python scraper fetches all data from Fantrax APIs and Google Sheets
- Generates a self-contained `dashboard_live.html` with all data embedded (no API calls at runtime)
- Cron job support for automated updates (every 30 minutes recommended)
- Manual trigger endpoint (`trigger.php`) for on-demand refresh
- Lock file prevents overlapping scraper runs
- Log rotation keeps cron logs manageable

---

## Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **A Fantrax account** with 4 leagues (NFL, NBA, NHL, MLB), each set to **Public** visibility
- A modern web browser

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/federation-dashboard.git
cd federation-dashboard

# 2. Copy the example environment file and fill in your league IDs
cp .env.example .env
# Edit .env with your Fantrax league IDs (see Configuration Guide below)

# 3. Edit the CONFIG section in scrape_fantrax.py with your team names,
#    owners, abbreviations, and colors (see Configuration Guide below)

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run the scraper
python scrape_fantrax.py --verbose

# 6. Open the generated dashboard in your browser
# macOS:
open dashboard_live.html
# Windows:
start dashboard_live.html
# Linux:
xdg-open dashboard_live.html
```

The scraper will connect to all 4 of your Fantrax leagues, fetch standings, rosters, matchups, and transactions, compute federation standings, and generate:

- `data/fed_fl.json`, `data/fed_ba.json`, `data/fed_hl.json`, `data/fed_lb.json` (per-league data)
- `data/fed_combined.json` (combined federation data)
- `dashboard_live.html` (self-contained HTML dashboard with all data embedded)

### Scraper Command-Line Options

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Show detailed progress output with timestamps |
| `--output-dir PATH` | Write JSON output files to a custom directory (used for server deployment) |

---

## Configuration Guide

### Setting Up Your Fantrax Leagues

1. **Create 4 leagues on Fantrax** -- one for each sport (NFL, NBA, NHL, MLB). Each league should have the same set of team owners.

2. **Set each league to Public visibility.** This is required for the scraper to access data without authentication.
   - In Fantrax: Commissioner --> League Setup --> Misc --> League Visibility --> **Public**

3. **Find your league IDs.** When you open a league on Fantrax, the URL will contain the league ID:
   ```
   https://www.fantrax.com/fantasy/league/XXXXXXXXXXXXXXXXXX/home
                                          ^^^^^^^^^^^^^^^^^^
                                          This is your league ID
   ```

4. **Enter your league IDs** in the `LEAGUES` dictionary in `scrape_fantrax.py`:

```python
LEAGUES = {
    "fed_fl": {
        "league_id": "YOUR_NFL_LEAGUE_ID_HERE",
        "name": "FedFL",        # Display name for your NFL league
        "sport": "NFL",
        "sport_code": "NFL",
        "method": "direct"       # NFL must use "direct" (library has bugs)
    },
    "fed_ba": {
        "league_id": "YOUR_NBA_LEAGUE_ID_HERE",
        "name": "FedBA",
        "sport": "NBA",
        "sport_code": "NBA",
        "method": "library"      # NBA works well with the fantraxapi library
    },
    "fed_hl": {
        "league_id": "YOUR_NHL_LEAGUE_ID_HERE",
        "name": "FedHL",
        "sport": "NHL",
        "sport_code": "NHL",
        "method": "library"      # NHL works with library (rosters fall back to API)
    },
    "fed_lb": {
        "league_id": "YOUR_MLB_LEAGUE_ID_HERE",
        "name": "FedLB",
        "sport": "MLB",
        "sport_code": "MLB",
        "method": "library"      # MLB works well with the fantraxapi library
    },
}
```

**About the `method` field:**
- `"library"` -- Uses the `fantraxapi` Python package. Cleaner interface but has known bugs with NFL leagues (the "Week" bug causes period/week data to fail).
- `"direct"` -- Uses raw HTTP requests to the Fantrax API. More reliable for NFL. The scraper will automatically fall back to direct API if the library fails for any sport.

### Configuring Your Teams

The scraper needs to map Fantrax team names to internal IDs. There are two key dictionaries to configure:

#### 1. `TEAM_NAME_MAP` -- Maps Fantrax display names to internal team IDs

Fantrax teams can have different display names (full name vs. abbreviated). Add all variations:

```python
TEAM_NAME_MAP = {
    # Full names (as they appear in Fantrax standings)
    "Alpha Wolves FC":      "alpha",
    "Bravo Storm United":   "bravo",
    "Charlie Raptors SC":   "charlie",
    "Delta Knights AC":     "delta",
    # ... all 12 teams

    # Abbreviated names (as they sometimes appear in matchups)
    "Alpha Wolves":         "alpha",
    "Bravo Storm":          "bravo",
    "Charlie Raptors":      "charlie",
    "Delta Knights":        "delta",
    # ... abbreviated versions
}
```

**Tip:** Run the scraper with `--verbose` the first time. If a team name can't be mapped, it will print a warning showing the unrecognized Fantrax name. Add that exact string to the map.

#### 2. `FED_TEAMS` -- Team metadata (displayed in the dashboard)

```python
FED_TEAMS = {
    "alpha": {
        "owner": "Owner Name",          # Team owner's display name
        "name": "Alpha Wolves F.C.",    # Official team name
        "abbr": "AWF",                  # 2-4 character abbreviation
        "color": "#1a5276",             # Primary team color (hex)
        "logo": "alpha.svg"             # Logo filename (in logos/teams/)
    },
    "bravo": {
        "owner": "Owner Name",
        "name": "Bravo Storm United",
        "abbr": "BSU",
        "color": "#922b21",
        "logo": "bravo.svg"
    },
    # ... all 12 teams
}
```

**Logo requirements:**
- Place SVG files in `logos/teams/`
- SVG format is recommended for crisp rendering at any size
- Logos display at 22px--48px in the dashboard depending on context
- If a logo file is missing, the dashboard gracefully hides the image element

### Google Sheets Setup (Optional)

The scraper can pull supplementary data from two Google Sheets. These are optional -- the dashboard works without them, you just won't have draft pick tracking or rivalry week markers.

#### Draft Picks Sheet

Track draft capital across future seasons for all leagues.

1. **Create a Google Sheet** and make it public (Share --> Anyone with the link --> Viewer)

2. **Structure:** Create one tab per future season (e.g., "2026-27", "2027-28", ...). Each tab should have this layout:

```
| FedFL          | Team A Name | Team B Name | Team C Name | ... |
| Round 1        | Team A Name | Team B Name | Team C Name | ... |
| Round 2        | Team A Name | Team D Name | Team C Name | ... |
| Round 3        | Team A Name | Team B Name | Team E Name | ... |
|                |             |             |             |     |
| FedBA          | Team A Name | Team B Name | Team C Name | ... |
| Round 1        | Team A Name | Team B Name | Team F Name | ... |
| ...            |             |             |             |     |
```

- Column A: League name (matches `SHEET_LEAGUE_MAP` keys) or "Round N"
- Columns B+: Team names as column headers (original pick owners)
- Round rows: Current owner of that pick. If the name differs from the column header, the pick is marked as traded.
- Blank rows separate leagues.

3. **Configure in `scrape_fantrax.py`:**

```python
DRAFT_SHEET_ID = "YOUR_GOOGLE_SHEET_ID_HERE"
# The sheet ID is in the URL: https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit

DRAFT_SEASONS = ["2026-27", "2027-28", "2028-29", "2029-30"]
# Tab names in your sheet (one tab per season)

SHEET_LEAGUE_MAP = {
    "FedFL": "fed_fl",
    "FedBA": "fed_ba",
    "FedHL": "fed_hl",
    "FedLB": "fed_lb",
}
```

#### Schedule Metadata Sheet

Track rivalry weeks and other special schedule labels.

1. **Create a Google Sheet** (can be the same workbook, different tab) and make it public.

2. **Structure:** One row per league with week labels in columns:

```
| FedFL | Week 1 | Week 2 | ... | Week 8 (Rivalry Week) | ... |
| FedBA | SP 1   | SP 2   | ... | SP 12 (Rivalry Week)  | ... |
```

Any cell containing "Rivalry" (case-insensitive) marks that week as the rivalry week for that league. The dashboard shows a red dot on rivalry weeks in the schedule viewer.

3. **Configure in `scrape_fantrax.py`:**

```python
SCHEDULE_SHEET_ID = "YOUR_SCHEDULE_SHEET_ID_HERE"
SCHEDULE_SHEET_NAME = "All-Time Schedule"    # Tab name
```

### Season Configuration

```python
# In the main() function of scrape_fantrax.py:
current_season = "2025-26"    # Update this each year
```

#### Handling the NFL Previous Season

NFL seasons span two calendar years (September to February), so they overlap with the NBA/NHL/MLB seasons. When the current NFL season hasn't started yet (all W-L records are 0-0), the scraper automatically uses previous season data for federation standings calculations.

The previous NFL season data is stored in `data/fed_fl_prev.json`. To generate this file:

1. At the end of each NFL season (after playoffs), run `tools/scrape_last_nfl.py` to archive the data.
2. Or manually save the `data/fed_fl.json` from the completed season as `data/fed_fl_prev.json`.

```python
NFL_PREV_FILE = "fed_fl_prev.json"
NFL_PREV_LEAGUE_ID = "YOUR_PREVIOUS_NFL_LEAGUE_ID"
# This is the league ID for last year's NFL league on Fantrax
```

---

## Project Structure

```
federation-dashboard/
├── scrape_fantrax.py          # Main scraper (~1300 lines)
│                               #   Connects to all 4 Fantrax league APIs
│                               #   Fetches standings, rosters, matchups, transactions
│                               #   Scrapes draft picks & schedule from Google Sheets
│                               #   Computes federation standings & playoff brackets
│                               #   Generates dashboard_live.html with embedded data
│
├── dashboard.html             # Dashboard template (~800 lines)
│                               #   Single-file static site (HTML + CSS + JS)
│                               #   Renders federation standings, league tabs,
│                               #   team profiles, playoff brackets, schedules
│                               #   Uses CSS custom properties for dark theme
│
├── transactions.html          # Transaction log page
│                               #   Sidebar filters (season, league, team, type)
│                               #   Free-text player search
│                               #   Loads data from data/transactions_YYYY-YY.json
│
├── constitution.html          # League rules page (customize with your rules)
│                               #   Searchable with real-time match highlighting
│                               #   Table of contents with section links
│
├── requirements.txt           # Python dependencies: fantraxapi, requests
│
├── .env.example               # Environment configuration template
│
├── logos/                     # SVG logo assets
│   ├── federation.svg         #   Your federation logo (used in nav bar)
│   ├── leagues/               #   Per-league logos (4 SVGs)
│   │   ├── fed_fl.svg         #     NFL league logo
│   │   ├── fed_ba.svg         #     NBA league logo
│   │   ├── fed_hl.svg         #     NHL league logo
│   │   └── fed_lb.svg         #     MLB league logo
│   └── teams/                 #   Team logos (12 SVGs, one per franchise)
│       ├── alpha.svg
│       ├── bravo.svg
│       └── ...
│
├── deploy/                    # Server deployment files
│   ├── run_scraper.sh         #   cPanel cron wrapper script
│   │                          #     Activates virtualenv, runs scraper,
│   │                          #     copies output to web root,
│   │                          #     lock file & log rotation
│   ├── run_scraper.bat        #   Windows Task Scheduler alternative
│   ├── trigger.php            #   Manual scraper trigger (web endpoint)
│   │                          #     Token-protected, rate-limited (2 min)
│   │                          #     Shows spinner, auto-redirects to dashboard
│   └── htaccess               #   Apache config (rename to .htaccess)
│                               #     HTTPS redirect, asset caching,
│                               #     security headers, compression,
│                               #     blocks access to .py/.sh/.log files
│
├── tools/                     # Development utilities & diagnostics
│   ├── diagnose.py            #   Tests all Fantrax API endpoints
│   ├── diagnose_api.py        #   Fantrax API response diagnostics
│   ├── scrape_direct.py       #   Alternative scraper (direct HTTP only)
│   ├── scrape_selenium.py     #   Selenium scraper (for auth-protected leagues)
│   ├── scrape_last_nfl.py     #   Archives previous NFL season data
│   ├── save_nfl_prev_scores.py#   Saves NFL matchup scores locally
│   ├── test_matchup_scores.py #   Tests matchup scoring logic
│   └── test_nfl_api.py        #   Tests NFL API endpoint availability
│
└── data/                      # Generated output (gitignored except prev season)
    └── fed_fl_prev.json       #   Previous NFL season data (tracked in git)
```

---

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                            │
│  Fantrax API (4 leagues)  ·  Google Sheets  ·  Previous NFL     │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│    scrape_fantrax.py         │
│    (Python 3.9+ scraper)     │
│                              │
│  1. Pull standings, rosters, │
│     matchups, transactions   │
│  2. Resolve player names     │
│  3. Compute federation pts   │
│  4. Build playoff brackets   │
│  5. Fetch draft picks &      │
│     schedule from Sheets     │
│  6. Output JSON + live HTML  │
└──────────┬───────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
  data/*.json   dashboard_live.html
  (raw JSON)    (self-contained HTML
     │           with embedded JSON)
     ▼
  dashboard.html  ◄── template
     Loads JSON via fetch() in dev mode
     OR uses embedded window.FED_DATA in production
```

### Data Modes

The dashboard supports two data loading modes:

1. **Embedded data (production):** The scraper reads `dashboard.html` as a template, injects all JSON data into a `<script>` tag via a placeholder comment, and writes `dashboard_live.html`. This file is completely self-contained -- no API calls needed at runtime. This is what gets deployed to your server as `index.html`.

2. **Fetched data (development):** When you open `dashboard.html` directly (without the scraper injecting data), it detects that `window.FED_DATA` is undefined and falls back to fetching `data/fed_combined.json` via `fetch()`. This requires running a local HTTP server (see [Local Development](#local-development)).

### Federation Points Calculation

Each league awards federation points based on final rank:

```
Federation Points = (Number of Teams + 1) - Rank
```

For a 12-team league: 1st place = 12 pts, 2nd = 11 pts, ..., 12th = 1 pt.

The scraper sums each team's federation points across all active leagues. When an NFL season is between seasons (all records are 0-0), the scraper automatically substitutes the previous NFL season's data so federation standings remain meaningful.

### Scraper Pipeline

The scraper processes each league through this pipeline:

1. **Fetch standings** via Fantrax API (W-L-T, points for, win %)
2. **Fetch rosters** with player IDs, positions, and injury status
3. **Resolve player names** using league-specific and sport-wide player ID databases
4. **Fetch matchup scores** for all scoring periods (regular season + playoffs)
5. **Build playoff bracket** from matchup data (determines seeds, tracks rounds, computes final standings 1st through 6th)
6. **Fetch transactions** (trades, adds, drops, waiver claims)
7. **Sort rosters** by sport-standard position order
8. **Map team names** from Fantrax display names to internal IDs

Then globally:

9. **Fetch draft picks** from Google Sheets
10. **Fetch schedule extras** (rivalry week labels) from Google Sheets
11. **Compute federation standings** (sum points, apply tiebreakers)
12. **Generate combined JSON** and **dashboard_live.html**

---

## Deployment Guide

### Local Development

The simplest way to develop is to run the scraper and open the generated file:

```bash
# Run the scraper to generate dashboard_live.html
python scrape_fantrax.py --verbose

# Open the self-contained dashboard
open dashboard_live.html
```

If you want to use the template mode (fetching JSON dynamically), serve the project with Python's built-in HTTP server:

```bash
python -m http.server 8090
# Visit http://localhost:8090/dashboard.html
```

This is useful for development because you can edit `dashboard.html` without re-running the scraper. Just refresh the page after making changes.

### cPanel Deployment

This section covers deploying to a cPanel shared hosting environment, which is the deployment model the project was built for.

#### Server Layout

```
/home/USERNAME/
├── scraper/                            # Scraper code (not web-accessible)
│   ├── scrape_fantrax.py
│   ├── dashboard.html                  # Template (scraper reads this)
│   ├── deploy/run_scraper.sh           # Cron wrapper (copy here)
│   ├── data/
│   │   └── fed_fl_prev.json            # Previous NFL season data
│   └── cron.log                        # Auto-rotated scraper log
│
└── yourdomain.com/                     # Public web root
    ├── .htaccess                       # From deploy/htaccess (renamed)
    ├── index.html                      # Generated by scraper (embedded data)
    ├── constitution.html
    ├── transactions.html
    ├── trigger.php                     # Manual scraper trigger
    ├── data/                           # JSON files (written by scraper)
    │   ├── fed_combined.json
    │   ├── fed_fl.json
    │   ├── fed_ba.json
    │   ├── fed_hl.json
    │   ├── fed_lb.json
    │   └── transactions_2025-26.json
    └── logos/                          # Full logo directory tree
        ├── federation.svg
        ├── leagues/
        └── teams/
```

#### Step-by-Step Deploy Instructions

1. **Create a Python app** in cPanel:
   - Go to "Setup Python App" in cPanel
   - Choose Python 3.9 or newer
   - Set the application root to `scraper`
   - Install dependencies:
     ```bash
     pip install fantraxapi requests
     ```

2. **Upload scraper files** to `/home/USERNAME/scraper/`:
   - `scrape_fantrax.py`
   - `dashboard.html`
   - `requirements.txt`
   - `data/fed_fl_prev.json` (if you have previous NFL season data)

3. **Upload web files** to the domain's public web root (`/home/USERNAME/yourdomain.com/`):
   - `constitution.html`
   - `transactions.html`
   - `deploy/trigger.php` (copy to web root)
   - `deploy/htaccess` --> rename to `.htaccess`
   - `logos/` directory (entire directory tree)

4. **Copy and configure `run_scraper.sh`:**
   ```bash
   cp deploy/run_scraper.sh /home/USERNAME/scraper/run_scraper.sh
   chmod +x /home/USERNAME/scraper/run_scraper.sh
   ```
   Edit the variables at the top of the script:
   ```bash
   USERNAME="your_cpanel_username"
   PYTHON_VERSION="3.9"                # Match your cPanel Python app version
   DOMAIN_DIR="yourdomain.com"          # Your site's root directory name
   ```

5. **Configure `trigger.php`:**
   - Edit `$SECRET` to a random string (e.g., generate with `openssl rand -hex 16`)
   - Edit `$SCRIPT` to point to your `run_scraper.sh` path:
     ```php
     $SECRET = 'your_random_secret_token_here';
     $SCRIPT = '/home/USERNAME/scraper/run_scraper.sh';
     ```

6. **Set up the cron job** in cPanel (Cron Jobs section):
   ```
   */30 * * * * bash /home/USERNAME/scraper/run_scraper.sh >> /home/USERNAME/scraper/cron.log 2>&1
   ```
   This runs the scraper every 30 minutes. Adjust the interval as needed (during active game days, you might want every 15 minutes; during the offseason, once per hour is fine).

7. **Test the trigger URL:**
   ```
   https://yourdomain.com/trigger.php?token=your_random_secret_token_here
   ```
   Bookmark this URL on your phone for one-tap data refresh. It's rate-limited to once per 2 minutes and shows a spinner page that auto-redirects to the dashboard after 90 seconds.

#### Lock File

The scraper creates a `.scraper.lock` file to prevent overlapping runs (e.g., if a cron run is still in progress when the next one triggers). If a run crashes and leaves a stale lock, it auto-expires after 10 minutes.

#### Log Rotation

The cron wrapper script automatically rotates `cron.log` when it exceeds 5000 lines, keeping the last 2000 lines.

### Other Hosting

#### Static Hosting (Vercel, Netlify, GitHub Pages)

Since the dashboard is a static HTML file, you can host it on any static hosting provider:

1. Run the scraper locally (or via GitHub Actions) to generate `dashboard_live.html`
2. Deploy the generated file along with `constitution.html`, `transactions.html`, `logos/`, and `data/`
3. Set up a GitHub Actions workflow to run the scraper on a schedule and commit the output

**Note:** You won't have `trigger.php` on static hosts. Use GitHub Actions' `workflow_dispatch` for manual triggers.

#### VPS (DigitalOcean, Linode, AWS EC2)

On a VPS, replace cron with a systemd timer:

```ini
# /etc/systemd/system/federation-scraper.timer
[Unit]
Description=Run federation scraper every 30 minutes

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/federation-scraper.service
[Unit]
Description=Federation Dashboard Scraper

[Service]
Type=oneshot
WorkingDirectory=/opt/federation-dashboard
ExecStart=/opt/federation-dashboard/venv/bin/python scrape_fantrax.py --verbose --output-dir /var/www/html/data
User=www-data
```

```bash
sudo systemctl enable --now federation-scraper.timer
```

---

## Customization Guide

### Changing Team Count

The default configuration is 12 teams. To adjust:

1. **Update `FED_TEAMS`** to have the correct number of entries (one per team)

2. **Update `TEAM_NAME_MAP`** to include all Fantrax name variants for each team

3. **Update the federation points formula** in `compute_federation()`:
   ```python
   # For N teams, points = (N + 1) - rank
   fp = (NUMBER_OF_TEAMS + 1) - rank
   ```
   The default formula is `13 - rank` (for 12 teams). For 10 teams, use `11 - rank`. For 8 teams, use `9 - rank`.

4. **Update the playoff bracket** if your league uses a different playoff format. The default assumes 6 teams qualify (top 2 get byes). Modify `build_playoff_bracket()` in the scraper if your format differs.

5. **Update the dashboard table columns.** The CSS classes `.c1`, `.c2`, `.c3`, `.ct`, `.cm`, `.cb` color-code ranks (gold/silver/bronze for 1-3, green for 4-6, gray for 7-9, red for 10-12). Adjust the `cc()` function in `dashboard.html` for your team count.

### Changing Sports

To add or remove leagues:

1. **Add/remove entries in `LEAGUES`:**
   ```python
   # Example: Adding a soccer league
   "fed_sc": {
       "league_id": "YOUR_SOCCER_LEAGUE_ID",
       "name": "FedSC",
       "sport": "MLS",        # Or whatever sport name you want
       "sport_code": "MLS",
       "method": "direct"
   },
   ```

2. **Add position orders** for the new sport in `POS_ORDER`:
   ```python
   POS_ORDER = {
       "NFL": ["QB","RB","WR","TE","Flex","D/ST","K"],
       "NBA": ["PG","SG","SF","PF","C","Flx","Utility","Util"],
       "NHL": ["LW","C","RW","D","G","Skaters","Sk"],
       "MLB": ["C","1B","2B","SS","3B","OF","SP","RP","Utility","Util","DH"],
       "MLS": ["GK","D","M","F","Util"],  # Your new sport
   }
   ```

3. **Add a nav tab** in `dashboard.html`:
   ```html
   <button class="nav-tab" data-page="mls">
       <img src="logos/leagues/fed_sc.svg" alt="Soccer"> MLS
   </button>
   ```

4. **Add the league mapping** in the JavaScript section of `dashboard.html`:
   ```javascript
   const LM = {
       // ... existing leagues ...
       fed_sc: {code:'MLS', sport:'MLS', logo:'logos/leagues/fed_sc.svg', color:'#00b140'},
   };
   const LO = ['fed_fl','fed_ba','fed_hl','fed_lb','fed_sc'];
   const P2L = { /* ... */ mls:'fed_sc' };
   ```

5. **Update federation points** if the number of leagues changes (the formula per-league stays the same, but maximum possible points increases).

6. **Create a league logo** SVG and place it in `logos/leagues/`.

### Theming

The dashboard uses CSS custom properties defined in `:root`. To change the theme:

```css
:root {
    --bg: #0b1120;           /* Page background */
    --surface: #111827;       /* Card/panel background */
    --surface2: #1a2438;      /* Nested surface (e.g., stat cards) */
    --surface3: #243044;      /* Deeply nested (e.g., position badges) */
    --border: #2d3a50;        /* Border color */
    --text: #e4e8f0;          /* Primary text */
    --text-dim: #8892a8;      /* Secondary text */
    --text-muted: #556078;    /* Tertiary/muted text */
    --accent: #f0c040;        /* Accent color (gold) */
    --gold: #ffd700;          /* 1st place */
    --silver: #c0c0c0;        /* 2nd place */
    --bronze: #cd7f32;        /* 3rd place */
}
```

**To switch to a light theme**, override these properties:

```css
:root {
    --bg: #f5f5f5;
    --surface: #ffffff;
    --surface2: #f0f0f0;
    --surface3: #e5e5e5;
    --border: #d0d0d0;
    --text: #1a1a2e;
    --text-dim: #555555;
    --text-muted: #888888;
    --accent: #c09020;
    --gold: #daa520;
    --silver: #808080;
    --bronze: #a0522d;
}
```

You will also want to adjust the `body::before` radial gradient and the `nav` background `rgba` values for light mode.

### Adding Your Constitution

The `constitution.html` file is a customizable league rules page:

1. Open `constitution.html` in a text editor
2. Find the `<body>` section with `<section>` elements
3. Replace the content with your own league rules using this structure:

```html
<section id="general">
    <h1>Article I -- General Provisions</h1>
    <h2>1.1 League Name</h2>
    <p>Your league description here...</p>

    <h2>1.2 Purpose</h2>
    <p>The purpose of the Federation is to...</p>
</section>

<section id="roster">
    <h1>Article II -- Roster Rules</h1>
    <h2>2.1 Roster Size</h2>
    <p>Each team shall maintain a roster of...</p>
    <!-- Add tables, lists, etc. -->
</section>
```

The search functionality and table of contents are automatically generated from the `<section>`, `<h1>`, and `<h2>` elements in the page. No JavaScript changes needed.

---

## Federation Points

### Points Table (12-team league)

| Final Rank | Federation Points |
|:----------:|:-----------------:|
| 1st | 12 |
| 2nd | 11 |
| 3rd | 10 |
| 4th | 9 |
| 5th | 8 |
| 6th | 7 |
| 7th | 6 |
| 8th | 5 |
| 9th | 4 |
| 10th | 3 |
| 11th | 2 |
| 12th | 1 |

### Formula

```
Federation Points = (Number of Teams + 1) - Final Rank
```

For a 12-team league: `13 - rank`

**Maximum possible:** 48 points (1st place in all 4 leagues)

### Tiebreakers (in order)

1. **Most league championships** -- number of 1st-place finishes across all leagues
2. **Highest combined win percentage** -- total wins / (total wins + total losses) across all active leagues
3. **Highest average points per game** -- sum of points-for across all leagues
4. **Head-to-head record** -- if still tied, compare H2H results across shared opponents

### Playoff Impact

For completed seasons, **playoff results** determine final league standings (positions 1--6). The dashboard marks playoff-determined rankings with an asterisk. Non-playoff teams (positions 7--12) retain their regular-season rank.

---

## API Reference

### Fantrax API

The scraper uses two interfaces to communicate with Fantrax:

#### `fantraxapi` Python Library

```bash
pip install fantraxapi
```

Used for NBA, NHL, and MLB leagues. Provides a clean Pythonic interface:

```python
from fantraxapi import League

league = League("YOUR_LEAGUE_ID")
print(league.name)           # League name
print(league.standings())    # Standings object
roster = league.team_roster(team_id)  # Roster object
results = league.scoring_period_results(season=True, playoffs=False)
```

**Known limitations:**
- NFL leagues fail with a "Week" bug during initialization
- NHL roster player IDs sometimes return as "137" instead of real IDs
- The library doesn't expose transaction details or schedule metadata

#### Direct HTTP API

Base URL: `https://www.fantrax.com/fxea/general`

| Endpoint | Parameters | Returns |
|----------|-----------|---------|
| `getStandings` | `leagueId` | Array of team standings (rank, W-L-T, PF, win%, GB) |
| `getTeamRosters` | `leagueId` | Dict of team rosters keyed by team ID |
| `getPlayerIds` | `leagueId` or `sport` | Player ID to name/position/team mapping |
| `getLeagueInfo` | `leagueId` | League metadata including matchup pairings |

**POST API** (used for matchup scores and transactions):

URL: `https://www.fantrax.com/fxpa/req?leagueId=YOUR_LEAGUE_ID`

```json
{
    "msgs": [{
        "method": "getStandings",
        "data": {
            "leagueId": "YOUR_LEAGUE_ID",
            "view": "SCHEDULE"
        }
    }]
}
```

Views: `"SCHEDULE"` for regular season, `"PLAYOFFS"` for playoff matchups.

Transaction history:
```json
{
    "msgs": [{
        "method": "getTransactionDetailsHistory",
        "data": {
            "leagueId": "YOUR_LEAGUE_ID",
            "maxResultsPerPage": "500"
        }
    }]
}
```

#### Rate Limiting

Fantrax does not publish official rate limits, but from experience:
- Keep requests to roughly 1 per second
- The scraper processes leagues sequentially, which naturally throttles requests
- If you get HTTP 429 or 403 errors, wait 5 minutes and retry
- Excessive parallel requests may result in temporary IP blocks

### Google Sheets CSV Export API

Used to read draft pick and schedule data from public Google Sheets:

```
https://docs.google.com/spreadsheets/d/SHEET_ID/gviz/tq?tqx=out:csv&sheet=TAB_NAME
```

- No authentication required for public sheets
- Returns CSV data that the scraper parses with Python's `csv` module
- If the sheet is private or the tab name is wrong, returns HTTP 400 or 404

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `fantraxapi not installed` | Missing Python dependency | Run `pip install fantraxapi` |
| `Could not map Fantrax team names` | Team was renamed on Fantrax | Add the new Fantrax display name to `TEAM_NAME_MAP` in the scraper config. Run with `--verbose` to see the unrecognized name. |
| `403 Forbidden` or `Not logged in` | League is set to Private on Fantrax | Go to Fantrax: Commissioner --> League Setup --> Misc --> set visibility to **Public** |
| `dashboard.html template not found` | Scraper running from wrong directory | Run the scraper from the repo root, or use `--output-dir` to specify the output path |
| `Playoff bracket: not_started` | Previous NFL season data is missing | Ensure `data/fed_fl_prev.json` exists. Generate it with `tools/scrape_last_nfl.py` |
| Scraper lock stuck | Previous scraper run crashed | Delete the `.scraper.lock` file in the scraper directory. It auto-clears after 10 minutes. |
| Player names showing as numeric IDs | Player ID resolution failed | The scraper tries league-specific IDs first, then sport-wide. Check that `getPlayerIds` returns data. Some newly added players may not be in the ID database yet. |
| JSON files are empty or tiny | Fantrax API rate limiting or outage | Wait 5 minutes, then retry with `--verbose` to identify which API call is failing |
| Dashboard shows blank page | No data loaded | Check browser console (F12). Ensure `data/fed_combined.json` exists (for template mode) or that `dashboard_live.html` was generated (for embedded mode). |
| `trigger.php` returns 403 | Token mismatch | Verify the `$SECRET` value in `trigger.php` matches the `?token=` parameter in your URL |
| Cron job not running | Path or permission issue | Check `cron.log` for errors. Ensure `run_scraper.sh` is executable: `chmod +x run_scraper.sh`. Verify the Python path exists. |
| NHL rosters show "137" for player IDs | Known `fantraxapi` library bug | The scraper automatically falls back to direct API for rosters when >50% fail. No action needed. |
| NFL matchup scores missing | NFL uses direct API which requires POST | Check that the Fantrax `fxpa/req` endpoint is accessible. The scraper handles this automatically. |
| Draft picks not showing | Google Sheet is private or sheet IDs are wrong | Verify the sheet is shared as "Anyone with the link". Check `DRAFT_SHEET_ID` and tab names match `DRAFT_SEASONS`. |
| Schedule rivalry weeks not appearing | Schedule sheet misconfigured | Ensure the sheet tab name matches `SCHEDULE_SHEET_NAME` and cells contain the word "Rivalry" |
| Transaction log page is empty | Transaction JSON file missing | Ensure the scraper has run at least once. Check that `data/transactions_YYYY-YY.json` exists. |
| Dashboard shows stale data | Cron job stopped or scraper is failing silently | Check `cron.log`. Visit `trigger.php` to force a refresh. Verify the scraper completes without errors via `--verbose`. |

---

## Contributing

Contributions are welcome. Here is how to get started:

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test locally:
   ```bash
   python scrape_fantrax.py --verbose
   # Open dashboard_live.html and verify your changes
   ```
4. **Commit** with a clear message describing your change
5. **Push** to your fork and open a **Pull Request**

### Development Tips

- The dashboard is vanilla HTML/CSS/JS with no build step. Edit `dashboard.html` directly and refresh.
- Use `python -m http.server 8090` for local development with JSON fetching.
- Run the scraper with `--verbose` to see detailed progress and catch issues early.
- The `tools/` directory contains diagnostic scripts for testing individual API endpoints.

### Code Style

- Python: Standard PEP 8, with compact formatting for config dictionaries
- HTML/CSS/JS: Compact single-file style. CSS uses BEM-inspired short class names for minimal file size.
- No external JavaScript frameworks or CSS preprocessors

### Areas for Contribution

- Additional sports support (MLS, PGA, etc.)
- Light theme option
- Push notification integration for live score updates
- Historical season comparison views
- Mobile app wrapper (PWA)
- Automated testing for scraper output

---

## License & Attribution

This project is licensed under the **MIT License** -- see [LICENSE](LICENSE) for details.

### Required Attribution

If you use this project (in whole or in part) for your own fantasy league dashboard, you **must** include visible attribution to the original creators. Add one of the following to your site's footer or an "About" page:

```
Built with the Fantasy Federation Dashboard — originally created by the ySF Commission
(www.ysffantasy.com)
```

Or at minimum, include a link back to the original repository in your site footer. This is a condition of use -- we put a lot of work into building this, and a shout-out is the least we ask in return.

### Full MIT License Text

Copyright (c) 2025 Fantasy Sports Federation Dashboard Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software. **Additionally, any public-facing
deployment must include visible attribution to the original project as described above.**

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
