#!/usr/bin/env python3
"""
Weight optimization analysis for FedPR v2 power rankings.
Tests grid of weight combinations and SOS iterations.
Does NOT modify any existing files.
"""
import json, statistics, itertools, sys

DATA_PATH = '/path/to/your/project/advisor/data/fed_combined.json'
COMPONENTS = ['win_pct', 'ppg', 'consistency', 'mov', 'sos', 'momentum']
SPORT_NAMES = {'fed_fl': 'FedFL', 'fed_ba': 'FedBA', 'fed_hl': 'FedHL', 'fed_lb': 'FedLB'}


# ─── Core computation functions (copied from compute_example.py) ──────────────

def z_normalize(results, key):
    vals = [r[key] for r in results]
    mu = statistics.mean(vals)
    sigma = statistics.stdev(vals) if len(vals) > 1 else 1
    for r in results:
        r['z_' + key] = (r[key] - mu) / sigma if sigma > 0 else 0


def effective_weights(W, base_weights):
    """Early-season ramp-in for CON and MOM."""
    mom_factor = min(1, (W - 1) / 4) if W > 1 else 0
    con_factor = min(1, (W - 1) / 3) if W > 1 else 0
    eff_mom = base_weights['momentum'] * mom_factor
    eff_con = base_weights['consistency'] * con_factor
    excess = (base_weights['momentum'] - eff_mom) + (base_weights['consistency'] - eff_con)
    return {
        'win_pct': base_weights['win_pct'] + excess * 0.6,
        'ppg': base_weights['ppg'] + excess * 0.4,
        'consistency': eff_con,
        'mov': base_weights['mov'],
        'sos': base_weights['sos'],
        'momentum': eff_mom
    }


def build_matchup_data(teams, matchups):
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
            week_results.append({'team': t, 'win_pct': win_pct, 'ppg': ppg,
                                  'consistency': consistency, 'mov': mov})
        if len(week_results) < 2:
            for wr in week_results:
                pr_at_week[wr['team']][through_week] = 0.0
            continue
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
    for r in results:
        t = r['team']
        weeks = r['weeks']
        K = min(len(weeks), 5)
        recent_weeks = weeks[-K:]
        if K < 2:
            r['momentum'] = 0.0
            continue
        recent_wins = 0
        for rw in recent_weeks:
            if team_scores[t][rw] > team_opp[t][rw][1]:
                recent_wins += 1
        recent_win_rate = recent_wins / K
        scoring_ratios = []
        for rw in recent_weeks:
            all_scores = [team_scores[t2][rw] for t2 in teams if rw in team_scores[t2]]
            if all_scores:
                league_mean = statistics.mean(all_scores)
                scoring_ratios.append(team_scores[t][rw] / league_mean if league_mean > 0 else 1.0)
        avg_scoring_ratio = statistics.mean(scoring_ratios) if scoring_ratios else 1.0
        r['recent_win_rate'] = recent_win_rate
        r['recent_scoring_ratio'] = avg_scoring_ratio
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


def compute_spearman(results):
    n = len(results)
    if n < 2:
        return 0.0
    d_sq = sum((r['new_rank'] - r['standings_rank'])**2 for r in results)
    return 1 - (6 * d_sq) / (n * (n**2 - 1))


def compute_league_pr(teams, team_names, matchups, standings=None,
                      base_weights=None, sos_iterations=3):
    if base_weights is None:
        base_weights = {'win_pct': 0.30, 'ppg': 0.25, 'consistency': 0.10,
                        'mov': 0.15, 'sos': 0.10, 'momentum': 0.10}

    team_scores, team_opp = build_matchup_data(teams, matchups)
    max_week = max((w for t in teams for w in team_scores[t]), default=0)
    if max_week == 0:
        return None

    results = compute_base_stats(teams, team_names, team_scores, team_opp)
    if not results:
        return None

    pr_at_week = compute_per_week_prs(teams, team_scores, team_opp, max_week)

    for iteration in range(sos_iterations):
        compute_sos(results, team_scores, team_opp, pr_at_week)
        compute_momentum(results, team_scores, team_opp, teams)

        for comp in COMPONENTS:
            z_normalize(results, comp)

        W = results[0]['weeks_played']
        ew = effective_weights(W, base_weights)
        for r in results:
            r['pr'] = sum(ew[c] * r['z_' + c] for c in COMPONENTS)

        if iteration < sos_iterations - 1:
            pr_map = {r['team']: r['pr'] for r in results}
            for t in teams:
                for w in team_scores[t]:
                    if t in pr_map:
                        pr_at_week[t][w] = pr_map[t]

    results.sort(key=lambda x: -x['pr'])
    for i, r in enumerate(results):
        r['new_rank'] = i + 1

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

    return results


# ─── Load data ────────────────────────────────────────────────────────────────

def load_leagues(data_path):
    """Load league data, returning list of (league_key, teams, team_names, matchups, standings)."""
    d = json.load(open(data_path))
    teams = list(d['teams'].keys())
    team_names = {t: d['teams'][t]['name'] for t in teams}
    leagues = []

    for lk in ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb']:
        ld = d['league_data'][lk]
        matchups = ld.get('matchups', [])
        complete = [m for m in matchups if m.get('complete')]

        if complete:
            leagues.append((lk, teams, team_names, matchups, ld.get('standings')))
        elif lk == 'fed_fl' and d.get('nfl_previous_season'):
            prev = d['nfl_previous_season']
            leagues.append((lk + '_prev', teams, team_names,
                            prev.get('matchups', []), prev.get('standings')))

    return leagues


def avg_spearman(leagues, base_weights, sos_iterations=3):
    """Compute average Spearman correlation across all leagues."""
    corrs = []
    for lk, teams, team_names, matchups, standings in leagues:
        results = compute_league_pr(teams, team_names, matchups, standings,
                                    base_weights=base_weights,
                                    sos_iterations=sos_iterations)
        if results:
            corrs.append(compute_spearman(results))
    return statistics.mean(corrs) if corrs else 0.0, corrs


# ─── Grid search ─────────────────────────────────────────────────────────────

def generate_weight_grid(step=0.05):
    """
    Generate all 6-component weight combos summing to 1.0 with given step.
    Components: win_pct, ppg, consistency, mov, sos, momentum
    Each ≥ 0.0, step increments.
    """
    vals = [round(i * step, 10) for i in range(int(1.0 / step) + 1)]
    combos = []
    target = 1.0
    for wp in vals:
        for pp in vals:
            if wp + pp > target + 1e-9:
                break
            for cn in vals:
                if wp + pp + cn > target + 1e-9:
                    break
                for mv in vals:
                    if wp + pp + cn + mv > target + 1e-9:
                        break
                    for so in vals:
                        if wp + pp + cn + mv + so > target + 1e-9:
                            break
                        mo = round(target - wp - pp - cn - mv - so, 10)
                        if mo < -1e-9:
                            break
                        if abs(mo - round(mo / step) * step) < 1e-9 and mo >= -1e-9:
                            mo = max(0.0, mo)
                            combos.append({
                                'win_pct': wp, 'ppg': pp, 'consistency': cn,
                                'mov': mv, 'sos': so, 'momentum': mo
                            })
    return combos


def run_grid_search(leagues, step=0.05):
    print(f"\nGenerating weight grid (step={step})...")
    combos = generate_weight_grid(step)
    print(f"Total combinations to test: {len(combos):,}")

    results = []
    for i, w in enumerate(combos):
        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i+1:,}/{len(combos):,}...", end='\r')
        corr, per_league = avg_spearman(leagues, w)
        results.append((corr, w, per_league))

    print(f"  Done: {len(combos):,}/{len(combos):,}    ")
    results.sort(key=lambda x: -x[0])
    return results


# ─── Single-component analysis ────────────────────────────────────────────────

def single_component_analysis(leagues):
    print("\n" + "=" * 70)
    print("SINGLE-COMPONENT PREDICTIVE POWER")
    print("=" * 70)
    print("(Each component given weight=1.0, all others=0.0)")
    print()

    solo_results = []
    for comp in COMPONENTS:
        w = {c: 0.0 for c in COMPONENTS}
        w[comp] = 1.0
        corr, per_league = avg_spearman(leagues, w)
        solo_results.append((corr, comp, per_league))

    solo_results.sort(key=lambda x: -x[0])
    league_keys = [lk for lk, *_ in leagues]

    header = f"{'Component':<14} {'Avg Spearman':>14}"
    for lk in league_keys:
        header += f"  {SPORT_NAMES.get(lk.replace('_prev', ''), lk):>8}"
    print(header)
    print("-" * (14 + 14 + 10 * len(league_keys)))

    for corr, comp, per_league in solo_results:
        row = f"{comp:<14} {corr:>14.4f}"
        for c in per_league:
            row += f"  {c:>8.4f}"
        print(row)


# ─── SOS iteration analysis ───────────────────────────────────────────────────

def sos_iteration_analysis(leagues):
    print("\n" + "=" * 70)
    print("SOS ITERATION ANALYSIS")
    print("=" * 70)
    print("(Using current weights for all tests)")
    print()

    base_weights = {'win_pct': 0.30, 'ppg': 0.25, 'consistency': 0.10,
                    'mov': 0.15, 'sos': 0.10, 'momentum': 0.10}

    league_keys = [lk for lk, *_ in leagues]
    header = f"{'Iterations':>12} {'Avg Spearman':>14}"
    for lk in league_keys:
        header += f"  {SPORT_NAMES.get(lk.replace('_prev', ''), lk):>8}"
    print(header)
    print("-" * (12 + 14 + 10 * len(league_keys)))

    for n_iter in range(1, 6):
        corr, per_league = avg_spearman(leagues, base_weights, sos_iterations=n_iter)
        row = f"{n_iter:>12} {corr:>14.4f}"
        for c in per_league:
            row += f"  {c:>8.4f}"
        print(row)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("FedPR v2 — Weight Optimization Analysis")
    print("=" * 70)

    print(f"\nLoading data from: {DATA_PATH}")
    leagues = load_leagues(DATA_PATH)
    league_names = [SPORT_NAMES.get(lk.replace('_prev', ''), lk) + (' [prev]' if '_prev' in lk else '')
                    for lk, *_ in leagues]
    print(f"Leagues with data: {', '.join(league_names)}")

    # Current weights baseline
    current_weights = {'win_pct': 0.30, 'ppg': 0.25, 'consistency': 0.10,
                       'mov': 0.15, 'sos': 0.10, 'momentum': 0.10}
    current_corr, current_per_league = avg_spearman(leagues, current_weights)
    print(f"\nCurrent weights baseline:")
    print(f"  Weights: win_pct=0.30, ppg=0.25, consistency=0.10, mov=0.15, sos=0.10, momentum=0.10")
    print(f"  Avg Spearman: {current_corr:.4f}")
    for (lk, *_), c in zip(leagues, current_per_league):
        name = SPORT_NAMES.get(lk.replace('_prev', ''), lk)
        flag = ' [prev]' if '_prev' in lk else ''
        print(f"    {name}{flag}: {c:.4f}")

    # Single component analysis
    single_component_analysis(leagues)

    # SOS iteration analysis
    sos_iteration_analysis(leagues)

    # Grid search
    print("\n" + "=" * 70)
    print("GRID SEARCH (step=0.05)")
    print("=" * 70)
    grid_results = run_grid_search(leagues, step=0.05)

    # Print top 10
    print("\nTOP 10 WEIGHT COMBINATIONS:")
    print()
    league_keys = [lk for lk, *_ in leagues]
    header = (f"{'Rank':>4}  {'win_pct':>7} {'ppg':>7} {'con':>7} {'mov':>7} "
              f"{'sos':>7} {'mom':>7}  {'Avg':>8}")
    for lk in league_keys:
        header += f"  {SPORT_NAMES.get(lk.replace('_prev',''), lk):>8}"
    print(header)
    print("-" * len(header))

    for rank, (corr, w, per_league) in enumerate(grid_results[:10], 1):
        row = (f"{rank:>4}  {w['win_pct']:>7.2f} {w['ppg']:>7.2f} {w['consistency']:>7.2f} "
               f"{w['mov']:>7.2f} {w['sos']:>7.2f} {w['momentum']:>7.2f}  {corr:>8.4f}")
        for c in per_league:
            row += f"  {c:>8.4f}"
        print(row)

    # Where do current weights rank?
    current_rank = next((i + 1 for i, (corr, w, _) in enumerate(grid_results)
                         if abs(w['win_pct'] - 0.30) < 0.001
                         and abs(w['ppg'] - 0.25) < 0.001
                         and abs(w['consistency'] - 0.10) < 0.001
                         and abs(w['mov'] - 0.15) < 0.001
                         and abs(w['sos'] - 0.10) < 0.001
                         and abs(w['momentum'] - 0.10) < 0.001), None)

    print(f"\nCurrent weights rank: #{current_rank} out of {len(grid_results):,} combinations")
    print(f"Current weights avg Spearman: {current_corr:.4f}")
    best_corr = grid_results[0][0]
    print(f"Best possible avg Spearman:   {best_corr:.4f}")
    print(f"Improvement potential:        {best_corr - current_corr:+.4f}")

    # Also show top 20-30 for context if there are ties at the top
    print("\n--- Combinations #11-20 (for context) ---")
    for rank, (corr, w, per_league) in enumerate(grid_results[10:20], 11):
        row = (f"{rank:>4}  {w['win_pct']:>7.2f} {w['ppg']:>7.2f} {w['consistency']:>7.2f} "
               f"{w['mov']:>7.2f} {w['sos']:>7.2f} {w['momentum']:>7.2f}  {corr:>8.4f}")
        print(row)


if __name__ == '__main__':
    main()
