/* Federation Cup — League Detail Page */
'use strict';

var leagueTab = 'standings';

function buildBracketFromMatchups(lk) {
  var eff = getEff(lk), data = eff.data;
  if (!data?.matchups) return null;
  var meta = data.schedule_meta || {}, periods = meta.periods || {};
  var playoffPeriods = Object.entries(periods).filter(function ([k, v]) { return v.is_playoff; }).map(function ([k, v]) { return { num: Number(k), ...v }; }).sort(function (a, b) { return a.num - b.num; });
  if (!playoffPeriods.length) return null;
  var playoffNums = playoffPeriods.map(function (p) { return p.num; });
  var allPlayoffMus = data.matchups.filter(function (m) { return playoffNums.includes(m.period) || m.is_playoff; });
  var playoffMus = allPlayoffMus.filter(function (m) { return !m.is_consolation; });
  var consolMus = allPlayoffMus.filter(function (m) { return m.is_consolation; });
  if (!playoffMus.length) return null;
  var allComplete = playoffMus.every(function (m) { return m.complete; });
  var seeds = {};
  if (data.standings) {
    var playoffTeams = new Set();
    for (var m of allPlayoffMus) { if (m.home_fed_id) playoffTeams.add(m.home_fed_id); if (m.away_fed_id) playoffTeams.add(m.away_fed_id); }
    for (var s of data.standings) { if (playoffTeams.has(s.fed_id)) seeds[s.fed_id] = s.reg_season_rank || s.rank; }
  }
  var rounds = [];
  for (var pp of playoffPeriods) {
    var periodMus = playoffMus.filter(function (m) { return m.period === pp.num; });
    if (!periodMus.length) continue;
    var rawName = pp.name || ('Round ' + (rounds.length + 1));
    var cleanName = rawName.replace(/^Playoffs\s*-\s*/i, '').replace(/\s*\(Week\s*\d+\)/i, '').trim();
    var isLast = pp === playoffPeriods[playoffPeriods.length - 1] && periodMus.length === 1;
    var matchups = periodMus.map(function (m) {
      var isBye = !m.away_fed_id || !m.home_fed_id || m.away_name === 'None/Bye' || m.home_name === 'None/Bye';
      var winner_fed_id = m.complete && !isBye ? (m.away_score > m.home_score ? m.away_fed_id : m.home_fed_id) : null;
      return { is_bye: isBye, away_fed_id: m.away_fed_id, home_fed_id: m.home_fed_id, away_score: m.away_score, home_score: m.home_score, complete: m.complete, winner_fed_id: winner_fed_id };
    });
    rounds.push({ name: isLast ? 'Championship' : cleanName, matchups: matchups });
  }
  for (var cm of consolMus) {
    var name = cm.consolation_name || 'Consolation';
    var isBye = !cm.away_fed_id || !cm.home_fed_id;
    var winner_fed_id = cm.complete && !isBye ? (cm.away_score > cm.home_score ? cm.away_fed_id : cm.home_fed_id) : null;
    var existing = rounds.find(function (r) { return r.name === name; });
    var mu = { is_bye: isBye, away_fed_id: cm.away_fed_id, home_fed_id: cm.home_fed_id, away_score: cm.away_score, home_score: cm.home_score, complete: cm.complete, winner_fed_id: winner_fed_id };
    if (existing) existing.matchups.push(mu);
    else rounds.push({ name: name, matchups: [mu] });
  }
  return { status: allComplete ? 'complete' : 'in_progress', seeds: seeds, rounds: rounds };
}

function renderPlaceholderBracket(lk) {
  var eff = getEff(lk), src = eff.data;
  var st = src?.standings || [];
  if (st.length < 6) return '';
  var top6 = st.slice(0, 6);
  function tl(s) { var t = D.teams?.[s.fed_id]; return '<span class="bracket-seed">(' + s.rank + ')</span>' + (t?.abbr || s.team_name || '?'); }
  function tbd() { return '<span style="color:var(--text-dim)">TBD</span>'; }
  function renderPlaceholderGame(awayHtml, homeHtml, isChamp) {
    return '<div class="bracket-game' + (isChamp ? ' championship' : '') + '" style="opacity:.7"><div class="bracket-team">' + awayHtml + '</div><div class="bracket-team">' + homeHtml + '</div></div>';
  }
  var s1 = top6[0], s2 = top6[1], s3 = top6[2], s4 = top6[3], s5 = top6[4], s6 = top6[5];
  var h = '<div class="bracket-section"><div class="bracket-title">Playoff Bracket (Projected Seeding)</div>';
  h += '<div class="note-box" style="margin-bottom:.8rem"><div class="note-body">Bracket seeded from current standings. Matchups will update when playoff data is available.</div></div>';
  h += '<div class="bracket-grid">';
  // Round 1
  h += '<div><div class="bracket-round-title">Round 1</div>';
  h += '<div class="bracket-bye">' + tl(s1) + ' &mdash; BYE</div>';
  h += '<div class="bracket-bye">' + tl(s2) + ' &mdash; BYE</div>';
  h += renderPlaceholderGame(tl(s3), tl(s6), false);
  h += renderPlaceholderGame(tl(s4), tl(s5), false);
  h += '</div>';
  // Semifinals
  h += '<div><div class="bracket-round-title">Semifinals</div>';
  h += renderPlaceholderGame(tl(s1), 'Winner #4/#5', false);
  h += renderPlaceholderGame(tl(s2), 'Winner #3/#6', false);
  h += '</div>';
  // Championship
  h += '<div><div class="bracket-round-title">Championship</div>';
  h += renderPlaceholderGame(tbd(), tbd(), true);
  h += '</div>';
  h += '</div>';
  // Consolation
  h += '<div class="bracket-consolation"><div class="bracket-round-title" style="margin-bottom:.4rem">Consolation</div><div class="bracket-consolation-grid">';
  h += '<div><div class="bracket-round-title">3rd Place</div>' + renderPlaceholderGame(tbd(), tbd(), false) + '</div>';
  h += '<div><div class="bracket-round-title">5th Place</div>' + renderPlaceholderGame(tbd(), tbd(), false) + '</div>';
  h += '</div></div>';
  h += '</div>';
  return h;
}

function renderPlayoffBracket(lk) {
  var eff = getEff(lk), bracket = eff.data?.playoff_bracket;
  if (!bracket) bracket = buildBracketFromMatchups(lk);
  if (!bracket || bracket.status === 'not_started') return renderPlaceholderBracket(lk);
  var seeds = bracket.seeds || {};
  function tl(yid, seed) { var t = D.teams?.[yid]; return '<span class="bracket-seed">(' + seed + ')</span>' + (t?.abbr || yid || '?'); }
  function renderGame(mu, isChamp) {
    if (mu.is_bye) { var bt = mu.home_fed_id || mu.away_fed_id; return '<div class="bracket-bye">' + tl(bt, seeds[bt] || '?') + ' &mdash; BYE</div>'; }
    var awS = seeds[mu.away_fed_id] || '?', hmS = seeds[mu.home_fed_id] || '?';
    var awC = mu.winner_fed_id === mu.away_fed_id ? 'winner' : (mu.complete ? 'loser' : '');
    var hmC = mu.winner_fed_id === mu.home_fed_id ? 'winner' : (mu.complete ? 'loser' : '');
    var awSc = mu.complete && !mu.source ? '<span class="bracket-score">' + Number(mu.away_score).toFixed(2) + '</span>' : '';
    var hmSc = mu.complete && !mu.source ? '<span class="bracket-score">' + Number(mu.home_score).toFixed(2) + '</span>' : '';
    return '<div class="bracket-game' + (isChamp ? ' championship' : '') + '"><div class="bracket-team ' + awC + '">' + tl(mu.away_fed_id, awS) + ' ' + awSc + '</div><div class="bracket-team ' + hmC + '">' + tl(mu.home_fed_id, hmS) + ' ' + hmSc + '</div></div>';
  }
  var mainR = bracket.rounds.filter(function (r) { return r.name !== '3rd Place' && r.name !== '5th Place'; });
  var consolR = bracket.rounds.filter(function (r) { return r.name === '3rd Place' || r.name === '5th Place'; });
  var h = '<div class="bracket-section"><div class="bracket-title">' + (bracket.status === 'complete' ? 'Playoff Results' : 'Playoff Bracket (In Progress)') + '</div>';
  h += '<div class="bracket-grid">';
  for (var round of mainR) {
    var isC = round.name === 'Championship';
    h += '<div><div class="bracket-round-title">' + round.name + '</div>';
    for (var mu of round.matchups) h += renderGame(mu, isC);
    h += '</div>';
  }
  h += '</div>';
  if (consolR.length) {
    h += '<div class="bracket-consolation"><div class="bracket-round-title" style="margin-bottom:.4rem">Consolation</div><div class="bracket-consolation-grid">';
    for (var round of consolR) {
      h += '<div><div class="bracket-round-title">' + round.name + '</div>';
      for (var mu of round.matchups) {
        h += renderGame(mu, false);
        if (mu.source === 'inferred') h += '<div class="bracket-inferred">No consolation game played &mdash; ranked by regular season seed</div>';
      }
      h += '</div>';
    }
    h += '</div></div>';
  }
  if (bracket.final_standings_1_to_6) {
    h += '<div style="margin-top:.8rem"><div class="bracket-round-title">Final Playoff Standings</div><div class="bracket-final">';
    var colors = { 1: 'var(--gold)', 2: 'var(--silver)', 3: 'var(--bronze)' };
    for (var fs of bracket.final_standings_1_to_6) {
      var t = D.teams?.[fs.fed_id], c = colors[fs.final_rank] || 'var(--text-dim)';
      h += '<span class="bracket-final-item"><span class="bracket-final-rank" style="color:' + c + '">' + fs.final_rank + '.</span>' + (t?.abbr || fs.fed_id) + '</span>';
    }
    h += '</div></div>';
  }
  h += '</div>'; return h;
}

function renderLeagueMatchups(lk) {
  var meta = getSchMeta(lk), mus = getMatchups(lk);
  if (!mus.length || !Object.keys(meta.periods || {}).length) return '';
  var wk = getCurrentWeek(lk), pInfo = meta.periods?.[String(wk)] || {};
  var dateStr = (pInfo.start && pInfo.end) ? formatDate(pInfo.start) + ' \u2014 ' + formatDate(pInfo.end) : '';
  var status = pInfo.complete ? 'final' : pInfo.current ? 'live' : 'upcoming';
  var statusLabel = pInfo.complete ? 'Final' : pInfo.current ? 'Live' : 'Upcoming';
  var rivalry = meta.rivalry_week === wk;
  var h = '<div style="margin-top:1.2rem"><div class="sch-league-bar"><span class="name">' + (pInfo.name || 'Week ' + wk) + '</span>';
  h += '<span class="badge ' + status + '">' + statusLabel + '</span>';
  if (rivalry) h += '<span class="badge rivalry-badge">Rivalry Week</span>';
  h += '<span class="dates">' + dateStr + '</span></div>';
  h += renderMatchupCards(lk, wk);
  return h + '</div>';
}

function renderLeagueStandings(lk) {
  var l = LM[lk], d = ld(lk), eff = getEff(lk), src = eff.data;
  var h = '';
  var seasonDone = eff.isPrev || !isActive(lk);
  if (eff.isPrev) h += '<div class="note-box"><div class="note-title">' + l.code + ' Season Complete</div><div class="note-body">The season has concluded. Showing final results.</div></div>';
  if (!isActive(lk) && !eff.isPrev) h += '<div class="note-box"><div class="note-title">Not Started</div><div class="note-body">This league hasn\'t begun play yet.</div></div>';
  var st = src?.standings || [];
  if (st.length) {
    var showFaab = !seasonDone && st.some(function (s) { return s.faab_remaining !== undefined; });
    var cols = showFaab ? 8 : seasonDone ? 8 : 7;
    var rows = '';
    for (var s of st) {
      var m = s.fed_id ? tm(s.fed_id) : {};
      var badge = '';
      if (s.playoff_result === 'Champion') badge = '<span class="playoff-badge champion">Champion</span>';
      else if (s.playoff_result === 'Runner-up') badge = '<span class="playoff-badge runner-up">Runner-up</span>';
      else if (s.playoff_result) badge = '<span class="playoff-badge placement">' + s.playoff_result + '</span>';
      var regNote = '';
      if (s.reg_season_rank && s.reg_season_rank !== s.rank) regNote = '<span class="reg-rank-note" title="Regular season: #' + s.reg_season_rank + '">(RS: ' + s.reg_season_rank + ')</span>';
      var extraCells = '';
      if (showFaab) {
        var rem = Math.round(s.faab_remaining || 0), pct = Math.round((rem / 250) * 100);
        var barColor = pct > 60 ? 'var(--green)' : pct > 30 ? 'var(--accent)' : 'var(--red)';
        extraCells = '<td class="n faab-cell"><div class="faab-amt">$' + rem + '</div><div class="faab-bar"><div class="faab-fill" style="width:' + pct + '%;background:' + barColor + '"></div></div></td>';
      } else if (seasonDone) {
        extraCells = '<td class="n" style="text-align:center;font-family:\'JetBrains Mono\',monospace;font-size:.78rem">' + (s.pa ? s.pa.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014') + '</td>';
      }
      var monoStyle = 'text-align:center;font-family:\'JetBrains Mono\',monospace;font-size:.78rem';
      var gbCell = '<td class="hm n" style="' + monoStyle + ';color:var(--text-dim)">' + (s.gb > 0 ? s.gb.toFixed(1) : '\u2014') + '</td>';
      var pfCell = '<td class="n" style="' + monoStyle + '">' + (s.pf ? s.pf.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014') + '</td>';
      var lpr = getPR(s.fed_id, lk);
      var prCell = '<td class="pr-cell">' + (lpr ? lpr.display_pr.toFixed(1) : '\u2014') + '</td>';
      rows += '<tr class="team-row" data-tid="' + (s.fed_id || '') + '" data-ctx="' + lk + '"><td class="rk">' + RE[s.rank] + regNote + '</td><td><div class="tc">' + (s.fed_id ? '<img src="' + assetPath('logos/teams/' + s.fed_id + '.svg') + '" style="width:28px;height:28px;border-radius:4px;object-fit:contain;flex-shrink:0" onerror="this.style.display=\'none\'">' : '') + '<div><div class="tn" style="color:' + (m.color || 'var(--text)') + '">' + s.team_name + badge + '</div><div class="to">' + (m.owner || '') + '</div></div></div></td><td class="rc">' + s.w + '-' + s.l + (s.t ? '-' + s.t : '') + '</td>' + gbCell + pfCell + prCell + extraCells + '<td class="fp">' + (13 - s.rank) + '</td></tr>';
      rows += '<tr class="detail-row" id="det-' + lk + '-' + (s.fed_id || s.rank) + '"><td colspan="' + cols + '"></td></tr>';
    }
    var extraHeader = showFaab ? '<th class="n">FAAB</th>' : seasonDone ? '<th class="n">PA</th>' : '';
    h += '<table class="st"><thead><tr><th class="n">Rk</th><th>Team</th><th class="n">Record</th><th class="n hm">GB</th><th class="n">PF</th><th class="n">PR</th>' + extraHeader + '<th class="n">Fed</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }
  return h;
}

function renderLeagueScheduleTab(lk) {
  if (!schWeek[lk]) schWeek[lk] = getCurrentWeek(lk);
  var wk = schWeek[lk], meta = getSchMeta(lk), pInfo = meta.periods?.[String(wk)] || {};
  var dateStr = (pInfo.start && pInfo.end) ? formatDate(pInfo.start) + ' \u2014 ' + formatDate(pInfo.end) : '';
  var status = pInfo.complete ? 'final' : pInfo.current ? 'live' : 'upcoming';
  var statusLabel = pInfo.complete ? 'Final' : pInfo.current ? 'Live' : 'Upcoming';
  var rivalry = meta.rivalry_week === wk;
  var h = '<div class="sch-league-bar"><span class="name">' + (pInfo.name || 'Week ' + wk) + '</span>';
  h += '<span class="badge ' + status + '">' + statusLabel + '</span>';
  if (rivalry) h += '<span class="badge rivalry-badge">Rivalry Week</span>';
  h += '<span class="dates">' + dateStr + '</span></div>';
  h += renderWeekBar(lk, wk);
  h += renderMatchupCards(lk, wk);
  return h;
}

function renderPage() {
  var lk = window.LEAGUE_KEY;
  var l = LM[lk], d = ld(lk);
  var h = '<div class="lh"><img src="' + assetPath(l.logo) + '" alt="" onerror="this.outerHTML=\'<div class=li style=background:' + l.color + '>' + l.code + '</div>\'"><div><div class="lt">' + l.emoji + ' ' + l.code + ' &mdash; ' + (d?.full_name || d?.name || l.code) + '</div><div class="lm">' + (d?.year || '') + ' &bull; ' + (d?.standings?.length || 0) + ' teams &bull; ' + (d?.method || '') + '</div></div></div>';

  if (lk === 'fed_fl') h += '<img src="' + assetPath('logos/banner/banner.png') + '" alt="FedFL Championship Banner" class="champ-banner">';

  // Tab bar
  h += '<div class="league-tabs">';
  h += '<button class="league-tab' + (leagueTab === 'standings' ? ' active' : '') + '" onclick="switchLeagueTab(\'standings\')">Standings</button>';
  h += '<button class="league-tab' + (leagueTab === 'schedule' ? ' active' : '') + '" onclick="switchLeagueTab(\'schedule\')">Schedule</button>';
  h += '<button class="league-tab' + (leagueTab === 'bracket' ? ' active' : '') + '" onclick="switchLeagueTab(\'bracket\')">Bracket</button>';
  h += '</div>';

  // Tab content
  h += '<div id="leagueContent">';
  if (leagueTab === 'standings') {
    h += renderLeagueStandings(lk);
    h += renderLeagueMatchups(lk);
  } else if (leagueTab === 'schedule') {
    h += renderLeagueScheduleTab(lk);
  } else if (leagueTab === 'bracket') {
    h += renderPlayoffBracket(lk);
  }
  h += '</div>';

  document.getElementById('app').innerHTML = h;
  bindRows();
  bindSchedule(renderPage);
}

window.switchLeagueTab = function (tab) {
  leagueTab = tab;
  renderPage();
};

window.pageInit = renderPage;
