#!/usr/bin/env python3
"""Compute FedPR v2 power rankings from fed_combined.json.
Revision 3: PR-based SOS (iterative), hybrid momentum, rebalanced weights."""
import json, statistics, sys, os

SPORT_NAMES = {
    'fed_fl': 'FedFL', 'fed_ba': 'FedBA', 'fed_hl': 'FedHL', 'fed_lb': 'FedLB'
}

BASE_WEIGHTS = {'win_pct': 0.35, 'ppg': 0.25, 'consistency': 0.05, 'mov': 0.20, 'sos': 0.10, 'momentum': 0.05}
COMPONENTS = ['win_pct', 'ppg', 'consistency', 'mov', 'sos', 'momentum']
SOS_ITERATIONS = 3


def z_normalize(results, key):
    """Z-normalize a key across results list. Writes z_{key} into each result."""
    vals = [r[key] for r in results]
    mu = statistics.mean(vals)
    sigma = statistics.stdev(vals) if len(vals) > 1 else 1
    for r in results:
        r['z_' + key] = (r[key] - mu) / sigma if sigma > 0 else 0


def effective_weights(W):
    """Compute effective weights with early-season ramp-in for CON and MOM."""
    mom_factor = min(1, (W - 1) / 4) if W > 1 else 0
    con_factor = min(1, (W - 1) / 3) if W > 1 else 0
    eff_mom = BASE_WEIGHTS['momentum'] * mom_factor
    eff_con = BASE_WEIGHTS['consistency'] * con_factor
    excess = (BASE_WEIGHTS['momentum'] - eff_mom) + (BASE_WEIGHTS['consistency'] - eff_con)
    return {
        'win_pct': BASE_WEIGHTS['win_pct'] + excess * 0.6,
        'ppg': BASE_WEIGHTS['ppg'] + excess * 0.4,
        'consistency': eff_con,
        'mov': BASE_WEIGHTS['mov'],
        'sos': BASE_WEIGHTS['sos'],
        'momentum': eff_mom
    }


def build_matchup_data(teams, matchups):
    """Parse matchups into per-team weekly scores and opponents."""
    team_scores = {t: {} for t in teams}
    team_opp = {t: {} for t in teams}
    for m in matchups:
        if not m.get('complete'):
            continue
        w = m['period']
        a, h = m.get('away_fed_id'), m.get('home_fed_id')
        a_s, h_s = float(m.get('away_score', 0)), float(m.get('home_score', 0))
        if a_s == 0 and h_s == 0:
            continue
        if not a or not h or a not in teams or h not in teams:
            continue
        team_scores[a][w] = a_s
        team_opp[a][w] = (h, h_s)
        team_scores[h][w] = h_s
        team_opp[h][w] = (a, a_s)
    return team_scores, team_opp


def compute_base_stats(teams, team_names, team_scores, team_opp):
    """Compute Win%, PPG, MOV, CON for each team (no SOS or MOM yet)."""
    results = []
    for t in teams:
        weeks = sorted(team_scores[t].keys())
        if not weeks:
            continue
        scores = [team_scores[t][w] for w in weeks]
        margins = [team_scores[t][w] - team_opp[t][w][1] for w in weeks]
        wins = sum(1 for m in margins if m > 0)
        losses = sum(1 for m in margins if m < 0)
        win_pct = wins / max(wins + losses, 1)
        ppg = statistics.mean(scores)
        stdev = statistics.stdev(scores) if len(scores) > 1 else 0
        consistency = max(0, min(1, 1 - stdev / ppg)) if ppg > 0 else 0.5
        mov = statistics.mean(margins)
        results.append({
            'team': t, 'name': team_names[t],
            'wins': wins, 'losses': losses, 'win_pct': win_pct,
            'ppg': ppg, 'stdev': stdev, 'consistency': consistency,
            'mov': mov, 'sos': 0.0, 'momentum': 0.0,
            'scores': scores, 'weeks_played': len(weeks), 'weeks': weeks
        })
    return results


def compute_per_week_prs(teams, team_scores, team_opp, max_week):
    """Compute a simplified PR for each team at each week (for SOS calculation).
    Uses Win%, PPG, MOV, CON only (no SOS/MOM to avoid circularity)."""
    # pr_at_week[t][w] = team t's PR through week w
    pr_at_week = {t: {} for t in teams}

    for through_week in range(1, max_week + 1):
        week_results = []
        for t in teams:
            weeks_so_far = [w for w in sorted(team_scores[t].keys()) if w <= through_week]
            if not weeks_so_far:
                continue
            scores = [team_scores[t][w] for w in weeks_so_far]
            margins = [team_scores[t][w] - team_opp[t][w][1] for w in weeks_so_far]
            wins = sum(1 for m in margins if m > 0)
            losses = sum(1 for m in margins if m < 0)
            win_pct = wins / max(wins + losses, 1)
            ppg = statistics.mean(scores)
            stdev = statistics.stdev(scores) if len(scores) > 1 else 0
            consistency = max(0, min(1, 1 - stdev / ppg)) if ppg > 0 else 0.5
            mov = statistics.mean(margins)
            week_results.append({
                'team': t, 'win_pct': win_pct, 'ppg': ppg,
                'consistency': consistency, 'mov': mov
            })

        if len(week_results) < 2:
            for wr in week_results:
                pr_at_week[wr['team']][through_week] = 0.0
            continue

        # Z-normalize and compute simple PR (equal weight on 4 components)
        for comp in ['win_pct', 'ppg', 'consistency', 'mov']:
            vals = [wr[comp] for wr in week_results]
            mu = statistics.mean(vals)
            sigma = statistics.stdev(vals) if len(vals) > 1 else 1
            for wr in week_results:
                wr['z_' + comp] = (wr[comp] - mu) / sigma if sigma > 0 else 0

        for wr in week_results:
            pr = (0.35 * wr['z_win_pct'] + 0.30 * wr['z_ppg']
                  + 0.20 * wr['z_mov'] + 0.15 * wr['z_consistency'])
            pr_at_week[wr['team']][through_week] = pr

    return pr_at_week


def compute_sos(results, team_scores, team_opp, pr_at_week):
    """Compute SOS as mean of opponent's rolling PR at time of matchup."""
    for r in results:
        t = r['team']
        weeks = r['weeks']
        opp_prs = []
        for w in weeks:
            opp_id = team_opp[t][w][0]
            opp_pr = pr_at_week.get(opp_id, {}).get(w, 0.0)
            opp_prs.append(opp_pr)
        r['sos'] = statistics.mean(opp_prs) if opp_prs else 0.0


def compute_momentum(results, team_scores, team_opp, teams):
    """Compute hybrid momentum: 50% rolling win rate + 50% scoring ratio vs league avg."""
    for r in results:
        t = r['team']
        weeks = r['weeks']
        K = min(len(weeks), 5)
        recent_weeks = weeks[-K:]

        if K < 2:
            r['momentum'] = 0.0
            continue

        # Rolling win rate over last K weeks
        recent_wins = 0
        for rw in recent_weeks:
            my_score = team_scores[t][rw]
            opp_score = team_opp[t][rw][1]
            if my_score > opp_score:
                recent_wins += 1
        recent_win_rate = recent_wins / K

        # Scoring ratio vs league average over last K weeks
        scoring_ratios = []
        for rw in recent_weeks:
            all_scores_that_week = [team_scores[t2][rw] for t2 in teams if rw in team_scores[t2]]
            if all_scores_that_week:
                league_mean = statistics.mean(all_scores_that_week)
                if league_mean > 0:
                    scoring_ratios.append(team_scores[t][rw] / league_mean)
                else:
                    scoring_ratios.append(1.0)
        avg_scoring_ratio = statistics.mean(scoring_ratios) if scoring_ratios else 1.0

        r['recent_win_rate'] = recent_win_rate
        r['recent_scoring_ratio'] = avg_scoring_ratio

    # Z-normalize both sub-components, then blend 50/50
    if len(results) < 2:
        for r in results:
            r['momentum'] = 0.0
        return

    win_rates = [r.get('recent_win_rate', 0.5) for r in results]
    score_ratios = [r.get('recent_scoring_ratio', 1.0) for r in results]

    wr_mu, wr_sig = statistics.mean(win_rates), statistics.stdev(win_rates) if len(win_rates) > 1 else 1
    sr_mu, sr_sig = statistics.mean(score_ratios), statistics.stdev(score_ratios) if len(score_ratios) > 1 else 1

    for r in results:
        z_wr = (r.get('recent_win_rate', 0.5) - wr_mu) / wr_sig if wr_sig > 0 else 0
        z_sr = (r.get('recent_scoring_ratio', 1.0) - sr_mu) / sr_sig if sr_sig > 0 else 0
        r['momentum'] = 0.5 * z_wr + 0.5 * z_sr


def compute_league_pr(teams, team_names, matchups, league_key, standings=None):
    """Compute PR for a single league with iterative SOS and hybrid momentum."""
    team_scores, team_opp = build_matchup_data(teams, matchups)
    max_week = max((w for t in teams for w in team_scores[t]), default=0)
    if max_week == 0:
        return None

    # Base stats (Win%, PPG, MOV, CON)
    results = compute_base_stats(teams, team_names, team_scores, team_opp)
    if not results:
        return None

    # Per-week PRs for SOS computation
    pr_at_week = compute_per_week_prs(teams, team_scores, team_opp, max_week)

    # Iterative SOS: compute SOS -> PR -> refine SOS
    for iteration in range(SOS_ITERATIONS):
        compute_sos(results, team_scores, team_opp, pr_at_week)
        compute_momentum(results, team_scores, team_opp, teams)

        # Z-normalize all components
        for comp in COMPONENTS:
            z_normalize(results, comp)

        # Compute PR
        W = results[0]['weeks_played']
        ew = effective_weights(W)
        for r in results:
            r['pr'] = sum(ew[c] * r['z_' + c] for c in COMPONENTS)
            r['display_pr'] = 50 + 10 * r['pr']

        # Update per-week PRs using full formula results for next iteration
        if iteration < SOS_ITERATIONS - 1:
            pr_map = {r['team']: r['pr'] for r in results}
            for t in teams:
                for w in team_scores[t]:
                    if t in pr_map:
                        pr_at_week[t][w] = pr_map[t]

    # Old FedPR for comparison
    for r in results:
        high_pf = max(r['scores']) if r['scores'] else 0
        low_pf = min(r['scores']) if r['scores'] else 0
        r['old_pr'] = ((r['ppg'] * 6) + ((high_pf + low_pf) * 2) + ((r['win_pct'] * 200) * 2)) / 10

    old_avg = statistics.mean([r['old_pr'] for r in results])
    for r in results:
        r['old_pr_rank'] = r['old_pr'] / old_avg if old_avg > 0 else 1

    # Rankings
    results.sort(key=lambda x: -x['pr'])
    for i, r in enumerate(results):
        r['new_rank'] = i + 1

    by_old = sorted(results, key=lambda x: -x['old_pr'])
    for i, r in enumerate(by_old):
        r['old_rank'] = i + 1

    # Actual standings
    standings_rank_map = {}
    if standings:
        for s in standings:
            fed_id = s.get('fed_id')
            final_rank = s.get('final_rank', s.get('rank'))
            if fed_id and final_rank:
                standings_rank_map[fed_id] = final_rank

    if standings_rank_map:
        for r in results:
            r['standings_rank'] = standings_rank_map.get(r['team'], 99)
    else:
        by_standings = sorted(results, key=lambda x: (-x['wins'], -x['ppg']))
        for i, r in enumerate(by_standings):
            r['standings_rank'] = i + 1

    results.sort(key=lambda x: x['new_rank'])

    # Correlations
    n = len(results)
    d_sq = sum((r['new_rank'] - r['standings_rank'])**2 for r in results)
    spearman_new = 1 - (6 * d_sq) / (n * (n**2 - 1))
    d_sq_old = sum((r['old_rank'] - r['standings_rank'])**2 for r in results)
    spearman_old = 1 - (6 * d_sq_old) / (n * (n**2 - 1))
    mad_new = statistics.mean([abs(r['new_rank'] - r['standings_rank']) for r in results])
    mad_old = statistics.mean([abs(r['old_rank'] - r['standings_rank']) for r in results])

    return {
        'results': results, 'max_week': max_week,
        'weights': effective_weights(results[0]['weeks_played']),
        'spearman_new': spearman_new, 'spearman_old': spearman_old,
        'mad_new': mad_new, 'mad_old': mad_old, 'is_frozen': False
    }


def compute_pr_from_data(d):
    """Compute PR from an in-memory data dict. Returns the PR output dict."""
    teams = list(d['teams'].keys())
    team_names = {t: d['teams'][t]['name'] for t in teams}
    all_results = {}

    for lk in ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb']:
        ld = d['league_data'][lk]
        matchups = ld.get('matchups', [])
        complete = [m for m in matchups if m.get('complete')]

        if complete:
            result = compute_league_pr(teams, team_names, matchups, lk, standings=ld.get('standings'))
            if result:
                all_results[lk] = result
        elif lk == 'fed_fl' and d.get('nfl_previous_season'):
            prev = d['nfl_previous_season']
            result = compute_league_pr(teams, team_names, prev.get('matchups', []), lk, standings=prev.get('standings'))
            if result:
                result['is_frozen'] = True
                all_results[lk] = result
        else:
            print(SPORT_NAMES.get(lk, lk) + ': No data (season not started)')

    # Print per-league results
    for lk in ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb']:
        if lk not in all_results:
            continue
        data = all_results[lk]
        results = data['results']
        sport = SPORT_NAMES[lk]
        frozen = ' [FROZEN]' if data['is_frozen'] else ''
        print('\n' + '=' * 95)
        print(' %s Power Rankings (through Week %d)%s' % (sport, data['max_week'], frozen))
        print('=' * 95)
        print('%3s %-22s %5s %5s %7s %7s %5s %6s %6s %6s %4s %4s' % (
            'PR#', 'Team', 'W-L', 'Win%', 'PPG', 'MOV', 'Con', 'SOS', 'Mom', 'Score', 'Old#', 'Stnd'))
        print('-' * 95)
        for r in results:
            wl = '%d-%d' % (r['wins'], r['losses'])
            print('%3d %-22s %5s %.3f %7.1f %7.1f %.3f %+6.3f %+6.3f %6.1f %4d %4d' % (
                r['new_rank'], r['name'], wl, r['win_pct'], r['ppg'], r['mov'],
                r['consistency'], r['sos'], r['momentum'], r['display_pr'],
                r['old_rank'], r['standings_rank']))
        print('\nSpearman: v2=%.4f  old=%.4f  |  MAD: v2=%.2f  old=%.2f' % (
            data['spearman_new'], data['spearman_old'], data['mad_new'], data['mad_old']))

    # Federation PR
    print('\n' + '=' * 80)
    print(' FEDERATION Power Rankings')
    print('=' * 80)
    fed_pr, fed_detail = {}, {}
    for t in teams:
        prs, detail = [], {}
        for lk in all_results:
            for r in all_results[lk]['results']:
                if r['team'] == t:
                    prs.append(r['pr'])
                    detail[lk] = {'pr': r['pr'], 'display': r['display_pr'], 'rank': r['new_rank']}
        if prs:
            fed_pr[t] = statistics.mean(prs)
            fed_detail[t] = detail

    fed_sorted = sorted(fed_pr.items(), key=lambda x: -x[1])
    print('%4s %-22s %7s %8s  Per-League' % ('Rank', 'Team', 'Fed PR', 'Display'))
    print('-' * 80)
    for i, (t, pr) in enumerate(fed_sorted):
        detail = fed_detail[t]
        lranks = '  '.join('%s:#%d' % (SPORT_NAMES[lk], detail[lk]['rank'])
                           for lk in ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb'] if lk in detail)
        print('%4d %-22s %+7.3f %8.1f  %s' % (i + 1, team_names[t], pr, 50 + 10 * pr, lranks))

    # JSON output
    output = {
        'leagues': {}, 'league_meta': {},
        'federation': [
            {'rank': i + 1, 'team': t, 'name': team_names[t],
             'pr': round(pr, 3), 'display': round(50 + 10 * pr, 1),
             'by_league': {lk: fed_detail[t][lk] for lk in fed_detail[t]}}
            for i, (t, pr) in enumerate(fed_sorted)
        ]
    }
    for lk, data in all_results.items():
        output['league_meta'][lk] = {
            'max_week': data['max_week'], 'is_frozen': data['is_frozen'],
            'spearman_new': round(data['spearman_new'], 4),
            'spearman_old': round(data['spearman_old'], 4),
            'mad_new': round(data['mad_new'], 2), 'mad_old': round(data['mad_old'], 2)
        }
        output['leagues'][lk] = [{
            'new_rank': r['new_rank'], 'old_rank': r['old_rank'],
            'standings_rank': r['standings_rank'],
            'team': r['team'], 'name': r['name'],
            'wins': r['wins'], 'losses': r['losses'],
            'win_pct': round(r['win_pct'], 3),
            'ppg': round(r['ppg'], 1), 'stdev': round(r['stdev'], 1),
            'consistency': round(r['consistency'], 3), 'mov': round(r['mov'], 1),
            'sos': round(r['sos'], 3), 'momentum': round(r['momentum'], 3),
            'display_pr': round(r['display_pr'], 1), 'old_pr': round(r['old_pr'], 1),
            'z_win_pct': round(r['z_win_pct'], 3), 'z_ppg': round(r['z_ppg'], 3),
            'z_consistency': round(r['z_consistency'], 3), 'z_mov': round(r['z_mov'], 3),
            'z_sos': round(r['z_sos'], 3), 'z_momentum': round(r['z_momentum'], 3),
            'pr': round(r['pr'], 3)
        } for r in data['results']]

    return output


def compute_pr(data_path):
    """CLI wrapper: read file, compute PR, write pr_data.json."""
    d = json.load(open(data_path))
    output = compute_pr_from_data(d)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pr_data.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print('\nSaved ' + out_path)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'site/data/fed_combined.json'
    compute_pr(path)
