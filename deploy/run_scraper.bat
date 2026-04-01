@echo off
REM ============================================================
REM  Federation Fantrax Scraper - Daily Runner
REM  Schedule this in Windows Task Scheduler to run daily.
REM ============================================================

REM Navigate to the scraper directory (one level up from deploy/, then into scraper/)
cd /d "%~dp0..\scraper"

REM Run the scraper with verbose output and Excel export
python scrape_fantrax.py --verbose --xlsx

REM Log the run
echo [%date% %time%] Scrape completed >> scrape_log.txt

REM Pause if running manually (remove for scheduled runs)
if "%1"=="" pause
