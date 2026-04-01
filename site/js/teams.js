/* Federation Cup — Teams & Team Detail Page */
'use strict';

function getTeamMatchup(lk, tid, period) {
  return getMatchups(lk).find(function (m) { return m.period === period && (m.away_fed_id === tid || m.home_fed_id === tid); });
}

function getEffMatchups(lk) {
  var eff = getEff(lk);
  return { matchups: eff.data?.matchups || [], meta: eff.data?.schedule_meta || {}, isPrev: eff.isPrev };
}

function renderTeams() {
  var f = computeFed(fedMode), cards = '';
  for (var t of f) {
    var logo = '<img src="' + assetPath('logos/teams/' + t.team_id + '.svg') + '" alt="" style="width:36px;height:36px;border-radius:5px;object-fit:contain" onerror="this.style.display=\'none\'">';
    var lb = '';
    for (var lk of LO) {
      var b = t.by_league?.[lk], l = LM[lk];
      if (b) {
        var lpr = getPR(t.team_id, lk);
        var prTag = lpr ? '<span style="font-family:\'JetBrains Mono\',monospace;font-size:.68rem;color:var(--blue)">' + lpr.display_pr.toFixed(1) + '</span>' : '';
        lb += '<div style="display:flex;align-items:center;justify-content:space-between;padding:.2rem 0;border-bottom:1px solid var(--border)"><span style="font-size:.72rem">' + l.emoji + ' ' + l.code + '</span><span class="' + cc(b.rank) + '" style="font-family:Palatino,serif">#' + b.rank + '</span>' + prTag + '<span style="font-family:\'JetBrains Mono\',monospace;font-size:.72rem;color:var(--text-dim)">' + b.w + '-' + b.l + '</span></div>';
      }
    }
    var fpr = getPR(t.team_id);
    var prStat = fpr ? '<div><div style="font-size:.55rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted)">PR</div><div style="font-family:\'JetBrains Mono\',monospace;font-size:1.4rem;font-weight:700;color:var(--blue)">' + fpr.display.toFixed(1) + '</div></div>' : '';
    cards += '<div class="team-card" data-tid="' + t.team_id + '" style="border-top-color:' + (t.color || 'var(--border)') + ';cursor:pointer"><div class="team-card-header">' + logo + '<div><div style="font-family:Palatino,serif;font-size:1.1rem;font-weight:600">' + t.name + '</div><div style="font-size:.78rem;color:var(--text-dim)">' + t.owner + ' &bull; ' + t.abbr + '</div></div></div><div style="display:flex;gap:1rem;margin-bottom:.6rem"><div><div style="font-size:.55rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted)">Rank</div><div style="font-family:Palatino,serif;font-size:1.4rem;font-weight:700;color:var(--accent)">#' + t.federation_rank + '</div></div><div><div style="font-size:.55rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted)">Points</div><div style="font-family:Palatino,serif;font-size:1.4rem;font-weight:700">' + t.total_fed_pts + '</div></div>' + prStat + '<div><div style="font-size:.55rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted)">Record</div><div style="font-family:Palatino,serif;font-size:1.4rem;font-weight:700">' + t.combined_w + '-' + t.combined_l + '</div></div></div>' + lb + '</div>';
  }
  return '<div class="fed-hero" style="padding-bottom:.8rem"><h1 style="font-size:1.8rem">All Teams</h1><div class="subtitle">12 Franchises &bull; 4 Sports &bull; 1 Champion</div></div><div class="teams-grid">' + cards + '</div>';
}

function renderTeamDetail(tid) {
  var t = tm(tid), fed = computeFed(fedMode).find(function (x) { return x.team_id === tid; });

  // Reset background (no team-colored tint)
  document.body.style.background = '';

  var h = '<a class="td-back" href="' + assetPath('team.html') + '">&larr; All Teams</a>';
  h += '<div class="td-header">';
  h += '<img src="' + assetPath('logos/teams/' + tid + '.svg') + '" onerror="this.style.display=\'none\'">';
  h += '<div><div class="td-name" style="color:' + (t.color || 'var(--text)') + '">' + t.name + '</div><div class="td-owner">' + t.owner + ' &bull; ' + t.abbr + '</div></div>';
  if (fed) {
    h += '<div class="td-stats">';
    h += '<div class="td-stat"><div class="label">Rank</div><div class="val" style="color:var(--accent)">#' + fed.federation_rank + '</div></div>';
    h += '<div class="td-stat"><div class="label">Points</div><div class="val">' + fed.total_fed_pts + '</div></div>';
    h += '<div class="td-stat"><div class="label">Record</div><div class="val">' + fed.combined_w + '-' + fed.combined_l + '</div></div>';
    var detPr = getPR(tid);
    if (detPr) h += '<div class="td-stat"><div class="label">PR</div><div class="val" style="color:var(--blue)">' + detPr.display.toFixed(1) + '</div></div>';
    h += '</div>';
  }
  h += '</div>';

  // Current matchups
  h += '<div class="td-this-week"><div class="td-tw-title">Current Matchups</div><div class="td-tw-grid">';
  for (var lk of LO) {
    var l = LM[lk], eff = getEffMatchups(lk);
    if (!eff.matchups.length) continue;
    var meta = eff.meta, wk = meta.current_period || meta.last_completed || 1;
    var mu = eff.matchups.find(function (m) { return m.period === wk && (m.away_fed_id === tid || m.home_fed_id === tid); });
    if (!mu) continue;
    var isAway = mu.away_fed_id === tid;
    var oppId = isAway ? mu.home_fed_id : mu.away_fed_id;
    var oppName = isAway ? mu.home_name : mu.away_name;
    var opp = oppId ? tm(oppId) : {};
    var myScore = isAway ? mu.away_score : mu.home_score;
    var oppScore = isAway ? mu.home_score : mu.away_score;
    var msF = myScore != null ? myScore.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014';
    var osF = oppScore != null ? oppScore.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014';
    var wl = 'tbd', wlText = '\u2014';
    if (mu.complete) {
      if (myScore > oppScore) { wl = 'W'; wlText = 'W'; }
      else if (myScore < oppScore) { wl = 'L'; wlText = 'L'; }
      else { wl = 'T'; wlText = 'T'; }
    }
    var pInfo = meta.periods?.[String(wk)] || {};
    var pName = pInfo.name || (lk === 'fed_fl' ? 'Week ' + wk : 'Period ' + wk);
    var roundTag = '';
    if (mu.is_consolation) { roundTag = ' (' + (mu.consolation_name || 'Consolation') + ')'; }
    else if (pInfo.is_playoff) {
      var pp = Object.entries(meta.periods || {}).filter(function ([k, v]) { return v.is_playoff; }).map(function ([k]) { return Number(k); }).sort(function (a, b) { return a - b; });
      var ri = pp.indexOf(wk), ct = pp.length;
      if (ri === ct - 1) roundTag = ' (Championship)'; else if (ri === ct - 2) roundTag = ' (Semifinals)'; else roundTag = ' (Quarterfinals)';
    }
    h += '<div class="td-tw-card">';
    h += '<div class="league-tag">' + l.code + '</div>';
    h += '<div class="opp">' + (oppId ? '<img src="' + assetPath('logos/teams/' + oppId + '.svg') + '" onerror="this.style.display=\'none\'">' : '');
    h += '<div><div class="opp-name" style="color:' + (opp.color || 'var(--text)') + '">vs ' + (opp.abbr || oppName) + '</div>';
    h += '<div class="opp-owner">' + pName + roundTag + '</div></div></div>';
    h += '<div class="score-pair"><span class="' + (wl === 'W' ? 'win' : wl === 'L' ? 'loss' : '') + '">' + msF + '</span> \u2014 <span class="' + (wl === 'L' ? 'win' : wl === 'W' ? 'loss' : '') + '">' + osF + '</span></div>';
    h += '<div class="wl-badge ' + wl + '">' + wlText + '</div>';
    h += '</div>';
  }
  h += '</div></div>';

  // Full schedule grid per league
  for (var lk of LO) {
    var l = LM[lk], eff = getEffMatchups(lk);
    if (!eff.matchups.length) continue;
    var meta = eff.meta, periods = Object.keys(meta.periods || {}).map(Number).sort(function (a, b) { return a - b; });
    if (!periods.length) continue;
    var curWk = meta.current_period || meta.last_completed || 0;
    h += '<div style="margin-bottom:1.5rem">';
    h += '<div class="sch-league-bar"><img src="' + assetPath(l.logo) + '" onerror="this.style.display=\'none\'"><span class="name">' + l.emoji + ' ' + l.code + '</span></div>';
    h += '<div style="overflow-x:auto"><table class="td-sch-table"><thead><tr><th class="lk-col">Wk</th>';
    for (var p of periods) {
      var pi = meta.periods?.[String(p)] || {};
      var isP = pi.is_playoff;
      var lab = isP ? 'P' + (p - periods.filter(function (x) { var pp = meta.periods?.[String(x)]; return pp && !pp.is_playoff; }).length) : '' + p;
      h += '<th' + (p === curWk ? ' style="color:var(--accent)"' : '') + '>' + lab + '</th>';
    }
    h += '</tr></thead><tbody><tr><td class="lk-cell">' + l.code + '</td>';
    for (var p of periods) {
      var pi = meta.periods?.[String(p)] || {};
      var mu = eff.matchups.find(function (m) { return m.period === p && (m.away_fed_id === tid || m.home_fed_id === tid); });
      if (!mu) { h += '<td>\u2014</td>'; continue; }
      var isBye = mu.away_name === 'None/Bye' || mu.home_name === 'None/Bye';
      if (isBye) { h += '<td style="color:var(--text-muted);font-size:.6rem" title="Bye">BYE</td>'; continue; }
      var isAway = mu.away_fed_id === tid;
      var oppId = isAway ? mu.home_fed_id : mu.away_fed_id;
      var opp = oppId ? tm(oppId) : {};
      var oppAbbr = opp.abbr || (isAway ? mu.home_name : mu.away_name).substring(0, 4);
      var myScore = isAway ? mu.away_score : mu.home_score;
      var oppScore = isAway ? mu.home_score : mu.away_score;
      var cls = '', prefix = '';
      if (mu.complete) {
        if (myScore > oppScore) { cls = 'cell-w'; prefix = 'W '; }
        else if (myScore < oppScore) { cls = 'cell-l'; prefix = 'L '; }
        else { cls = 'cell-t'; prefix = 'T '; }
      } else if (pi.current) { cls = 'cell-current'; }
      else if (!pi.complete) { cls = 'cell-future'; }
      var atPrefix = isAway ? '@' : '';
      var cellLabel = '';
      if (mu.is_consolation) { cellLabel = mu.consolation_name || 'Consolation'; }
      else if (pi.is_playoff) {
        var pp2 = Object.entries(meta.periods || {}).filter(function ([k, v]) { return v.is_playoff; }).map(function ([k]) { return Number(k); }).sort(function (a, b) { return a - b; });
        var ri2 = pp2.indexOf(p), t2 = pp2.length;
        if (ri2 === t2 - 1) cellLabel = 'Championship'; else if (ri2 === t2 - 2) cellLabel = 'Semifinals'; else cellLabel = 'Quarterfinals';
      }
      var scoreStr = mu.complete ? prefix + (Math.round(myScore * 10) / 10) + '-' + (Math.round(oppScore * 10) / 10) : '';
      h += '<td class="' + cls + '" title="' + (cellLabel ? cellLabel + ': ' : '') + (isAway ? '@ ' : 'vs ') + oppAbbr + (scoreStr ? ' ' + scoreStr : '') + '">';
      if (cellLabel) h += '<div style="font-size:.5rem;color:var(--accent);line-height:1">' + cellLabel + '</div>';
      h += '<div class="opp-abbr">' + atPrefix + oppAbbr + '</div>';
      if (scoreStr) h += '<div class="cell-score">' + prefix + (Math.round(myScore * 10) / 10) + '</div>';
      h += '</td>';
    }
    h += '</tr></tbody></table></div></div>';
  }

  // FAAB budget per league
  var faabHtml = '';
  for (var lk of LO) {
    var effData = getEff(lk), src = effData.data;
    if (!src?.standings) continue;
    var st = src.standings.find(function (s) { return s.fed_id === tid; });
    if (!st || st.faab_remaining === undefined || st.faab_remaining === null) continue;
    var rem = Math.round(st.faab_remaining), spent = Math.round(st.faab_spent || 0), pct = Math.round((rem / 250) * 100);
    var barColor = pct > 60 ? 'var(--green)' : pct > 30 ? 'var(--accent)' : 'var(--red)';
    faabHtml += '<div class="td-faab-item"><span class="td-faab-league">' + LM[lk].emoji + ' ' + LM[lk].code + '</span><span class="td-faab-val">$' + rem + ' / $250</span><div class="td-faab-bar"><div class="td-faab-fill" style="width:' + pct + '%;background:' + barColor + '"></div></div></div>';
  }
  if (faabHtml) h += '<div style="margin-top:1.2rem"><div class="sh">FAAB Budget</div><div class="td-faab-grid">' + faabHtml + '</div></div>';

  // Rosters and draft picks
  var rh = '';
  for (var lk of LO) {
    var l = LM[lk], pl = getRoster(lk, tid);
    if (lk === 'fed_fl' && (!pl || !pl.length)) {
      var prevData = D.nfl_previous_season;
      if (prevData?.rosters) for (var [, r] of Object.entries(prevData.rosters)) if (r.fed_id === tid) { pl = r.players || []; break; }
    }
    if (pl && pl.length) rh += '<div style="margin-top:.8rem"><div class="sh"><img src="' + assetPath(l.logo) + '" onerror="this.style.display=\'none\'">' + l.emoji + ' ' + l.code + ' Roster (' + pl.length + ')</div>' + renderRosterBlock(pl, l.sport) + '</div>';
  }
  rh += renderDraftPicks(tid, window.LEAGUE_KEY || null);
  rh += renderTeamTxWidget(tid);
  h += rh;

  return h;
}

// Transaction history widget for team detail
var teamTxData = null;
var teamTxFilters = { types: ['FA', 'DROP', 'WW', 'TRADE'], leagues: ['FedFL', 'FedBA', 'FedHL', 'FedLB'], search: '' };

function loadTeamTransactions(tid, callback) {
  if (teamTxData) { callback(teamTxData); return; }
  fetch(assetPath('data/transactions_2025-26.json')).then(function (r) { return r.json(); }).then(function (d) {
    teamTxData = d;
    callback(d);
  }).catch(function () { callback(null); });
}

function renderTeamTxWidget(tid) {
  if (!teamTxData) return '';
  var leagues = teamTxData.leagues || {};
  var txns = [];
  for (var lk in leagues) {
    var code = (LM[lk.replace('_prev', '')] || {}).code || lk;
    var list = leagues[lk].transactions || [];
    for (var t of list) {
      if (t.fed_id !== tid) continue;
      txns.push({ date: t.date, league: code, players: t.players || [], bid: t.bid || 0 });
    }
  }
  txns.sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });

  // Filter
  var filt = txns.filter(function (t) {
    if (!teamTxFilters.leagues.includes(t.league)) return false;
    var typeMatch = t.players.some(function (p) { return teamTxFilters.types.includes(p.type); });
    if (!typeMatch) return false;
    if (teamTxFilters.search) {
      var q = teamTxFilters.search.toLowerCase();
      var match = t.players.some(function (p) { return (p.name || '').toLowerCase().includes(q) || (p.type || '').toLowerCase().includes(q); }) || (t.league || '').toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  var h = '<div class="team-tx-widget"><div class="sh" style="margin-bottom:.5rem">Transaction History (' + filt.length + ')</div>';
  // Filter controls
  h += '<div class="team-tx-filters">';
  var types = [['FA', 'Add'], ['DROP', 'Drop'], ['WW', 'Waiver'], ['TRADE', 'Trade']];
  for (var tp of types) {
    var chk = teamTxFilters.types.includes(tp[0]) ? ' checked' : '';
    h += '<label class="tx-filter-label"><input type="checkbox" data-txtype="' + tp[0] + '"' + chk + '> ' + tp[1] + '</label>';
  }
  h += '<input type="text" class="tx-search-input" placeholder="Search..." value="' + (teamTxFilters.search || '') + '">';
  h += '</div><div class="team-tx-filters" style="margin-top:.3rem">';
  var leagueOpts = [['FedFL', LM.fed_fl.emoji], ['FedBA', LM.fed_ba.emoji], ['FedHL', LM.fed_hl.emoji], ['FedLB', LM.fed_lb.emoji]];
  for (var lg of leagueOpts) {
    var chk2 = teamTxFilters.leagues.includes(lg[0]) ? ' checked' : '';
    h += '<label class="tx-filter-label"><input type="checkbox" data-txleague="' + lg[0] + '"' + chk2 + '> ' + lg[1] + ' ' + lg[0] + '</label>';
  }
  h += '</div>';
  // Transaction list
  h += '<div class="team-tx-scroll">';
  if (!filt.length) {
    h += '<div style="padding:.6rem;color:var(--text-muted);font-size:.8rem">No transactions found</div>';
  }
  for (var t of filt) {
    var d = t.date ? new Date(t.date) : null;
    var ds = d ? (d.getMonth() + 1) + '/' + d.getDate() : '';
    for (var p of t.players) {
      if (!teamTxFilters.types.includes(p.type)) continue;
      var badge = p.type === 'FA' ? 'badge-fa' : p.type === 'DROP' ? 'badge-drop' : p.type === 'WW' ? 'badge-ww' : p.type === 'TRADE' ? 'badge-trade' : '';
      var bidStr = p.type === 'WW' && t.bid > 0 ? ' <span style="color:var(--accent);font-size:.7rem">$' + t.bid + '</span>' : '';
      h += '<div class="team-tx-row"><span class="tx-date">' + ds + '</span><span class="tx-league">' + t.league + '</span><span class="badge ' + badge + '">' + p.type + '</span><span class="tx-player">' + (p.name || '?') + '</span>' + bidStr + '</div>';
    }
  }
  h += '</div></div>';
  return h;
}

function bindTeamTxFilters(tid) {
  document.querySelectorAll('.team-tx-widget input[data-txtype]').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var t = this.dataset.txtype;
      if (this.checked) { if (!teamTxFilters.types.includes(t)) teamTxFilters.types.push(t); }
      else { teamTxFilters.types = teamTxFilters.types.filter(function (x) { return x !== t; }); }
      document.querySelector('.team-tx-widget').outerHTML = renderTeamTxWidget(tid);
      bindTeamTxFilters(tid);
    });
  });
  document.querySelectorAll('.team-tx-widget input[data-txleague]').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var lg = this.dataset.txleague;
      if (this.checked) { if (!teamTxFilters.leagues.includes(lg)) teamTxFilters.leagues.push(lg); }
      else { teamTxFilters.leagues = teamTxFilters.leagues.filter(function (x) { return x !== lg; }); }
      document.querySelector('.team-tx-widget').outerHTML = renderTeamTxWidget(tid);
      bindTeamTxFilters(tid);
    });
  });
  var searchInput = document.querySelector('.tx-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      teamTxFilters.search = this.value;
      document.querySelector('.team-tx-widget').outerHTML = renderTeamTxWidget(tid);
      bindTeamTxFilters(tid);
      var si = document.querySelector('.tx-search-input');
      if (si) { si.focus(); si.selectionStart = si.selectionEnd = si.value.length; }
    });
  }
}

function bindTeamCards() {
  document.querySelectorAll('.team-card[data-tid]').forEach(function (c) {
    c.addEventListener('click', function () {
      window.location.href = assetPath('team.html') + '?id=' + this.dataset.tid;
    });
  });
}

function renderPage() {
  var params = new URLSearchParams(window.location.search);
  var tid = params.get('id');
  if (tid && D.teams?.[tid]) {
    // Lazy-load detail data then render
    var loads = [];
    if (!D.nfl_previous_season) loads.push(loadLazy('nfl_previous_season'));
    if (!D.draft_picks_by_team) loads.push(loadLazy('draft_picks_by_team'));
    Promise.all(loads).then(function () {
      loadTeamTransactions(tid, function () {
        document.getElementById('app').innerHTML = renderTeamDetail(tid);
        document.title = 'Federation \u2014 ' + (tm(tid).name || tid);
        bindTeamTxFilters(tid);
      });
    });
  } else {
    // Reset body background for grid view
    document.body.style.background = '';
    document.getElementById('app').innerHTML = renderTeams();
    bindTeamCards();
  }
}

window.pageInit = renderPage;
