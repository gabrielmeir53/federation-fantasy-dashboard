#!/usr/bin/env python3
"""Weekly Federation Power Rankings & Federation Standings email."""
import json, os, sys, smtplib
from email.mime.text import MIMEText
from datetime import datetime

SPORT_NAMES = {'fed_fl': 'FedFL', 'fed_ba': 'FedBA', 'fed_hl': 'FedHL', 'fed_lb': 'FedLB'}
LEAGUE_ORDER = ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb']

# Short team names (strip "F.C.", "A.C.", "S.C.", "B.J.C.", "Utd" etc.)
ABBREVS = {
    'Lima Rovers': 'Lima Rovers',
    'Delta Athletic': 'Delta Athletic',
    'Echo Rangers': 'Echo Rangers',
    'Juliet SC': 'Juliet SC',
    'Charlie SC': 'Charlie SC',
    'Foxtrot City': 'Foxtrot City',
    'Bravo United': 'Bravo United',
    'Kilo Athletic': 'Kilo Athletic',
    'India United': 'India United',
    'Hotel FC': 'Hotel FC',
    'Golf Town': 'Golf Town',
    'Alpha FC': 'Alpha FC',
}

def short_name(name):
    return ABBREVS.get(name, name)


def should_show_draft(league_data):
    """Show draft order if season is >75% done, playoffs started, or frozen."""
    if not league_data:
        return False
    meta = league_data.get('schedule_meta', {})
    periods = meta.get('periods', {})
    if not periods:
        return False

    reg_periods = [k for k, v in periods.items() if not v.get('is_playoff')]
    playoff_periods = [k for k, v in periods.items() if v.get('is_playoff')]

    # Check if frozen (all periods complete)
    all_complete = all(v.get('complete') for v in periods.values())
    if all_complete and len(periods) > 1:
        return True

    # Check if any playoff matchup is complete
    matchups = league_data.get('matchups', [])
    playoff_nums = set(int(k) for k, v in periods.items() if v.get('is_playoff'))
    if any(m.get('complete') and m.get('period') in playoff_nums for m in matchups):
        return True

    # Check if >75% of regular season is done
    if reg_periods:
        completed_reg = sum(1 for k in reg_periods if periods[k].get('complete'))
        if completed_reg / len(reg_periods) >= 0.75:
            return True

    return False


def get_draft_order(league_data, teams, year=2026):
    """Get draft order (reverse standings, bottom 6 + TBD for 7-12)."""
    standings = league_data.get('standings', [])
    if not standings:
        return None

    # Sort by rank descending (worst first)
    by_rank = sorted(standings, key=lambda s: -s.get('rank', 0))

    # Bottom 6 pick first
    order = []
    for i, s in enumerate(by_rank[:6]):
        yid = s.get('fed_id', '')
        name = teams.get(yid, {}).get('name', s.get('team_name', '?'))
        order.append((i + 1, short_name(name)))

    return order


def build_email(data):
    today = datetime.now().strftime('%m/%d/%y')
    lines = []

    # -- Power Rankings --
    pr = data.get('power_rankings')
    if pr and pr.get('federation'):
        lines.append(f'Federation Power Rankings through {today}:')
        for t in pr['federation']:
            lines.append(f'{t["rank"]}. {short_name(t["name"])} ({t["display"]:.1f})')
        lines.append('')

    # -- Federation Standings --
    fed = data.get('federation_standings') or data.get('federation_standings_all', [])
    if fed:
        lines.append('Federation Cup Standings if the season ended today:')
        for t in fed:
            rank = t.get('federation_rank', '?')
            name = short_name(t.get('name', '?'))
            pts = t.get('total_fed_pts', 0)
            lines.append(f'{rank}. {name} - {pts} Fed. Points')
        lines.append('')

    # -- Draft Order (conditional) --
    teams = data.get('teams', {})
    league_data = data.get('league_data', {})
    for lk in LEAGUE_ORDER:
        ld = league_data.get(lk)
        if not ld:
            continue
        if not should_show_draft(ld):
            continue

        sport = SPORT_NAMES.get(lk, lk)
        order = get_draft_order(ld, teams)
        if not order:
            continue

        year_str = ld.get('year', 2026)
        lines.append(f'{year_str} {sport} Rookie Draft Order')
        for pick, name in order:
            lines.append(f'{pick}. {name}')
        lines.append('7-12. TBD')
        lines.append('')

    return '\n'.join(lines).strip()


def send_email(subject, body, dry_run=False):
    gmail_user = os.environ.get('FED_GMAIL_USER', '')
    gmail_pass = os.environ.get('FED_GMAIL_PASS', '')
    from_addr = os.environ.get('FED_EMAIL_FROM', 'scraper@yourdomain.com')
    to_addrs = ['your@email.com', 'commissioner@email.com']

    if dry_run:
        print(f'Subject: {subject}')
        print(f'To: {", ".join(to_addrs)}')
        print(f'From: {from_addr}')
        print('---')
        print(body)
        return

    if not gmail_user or not gmail_pass:
        print('ERROR: Gmail credentials not set (FED_GMAIL_USER, FED_GMAIL_PASS)', file=sys.stderr)
        sys.exit(1)

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(from_addr, to_addrs, msg.as_string())
        print('Weekly PR email sent.')
    except Exception as e:
        print(f'Email failed: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    data_dir = os.environ.get('FED_OUTPUT_DIR', '/home/YOUR_CPANEL_USERNAME/yourdomain.com/data')

    # Allow passing data dir as argument
    for arg in sys.argv[1:]:
        if arg != '--dry-run' and os.path.isdir(arg):
            data_dir = arg

    json_path = os.path.join(data_dir, 'fed_combined.json')
    if not os.path.exists(json_path):
        print(f'ERROR: {json_path} not found', file=sys.stderr)
        sys.exit(1)

    with open(json_path, 'r') as f:
        data = json.load(f)

    body = build_email(data)
    today = datetime.now().strftime('%m/%d/%y')
    subject = f'[Federation] Weekly Power Rankings - {today}'

    send_email(subject, body, dry_run=dry_run)
