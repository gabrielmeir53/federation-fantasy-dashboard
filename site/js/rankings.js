/* Federation Cup — Power Rankings Page */
'use strict';

var prTab = 'federation';

function renderFedPR() {
  var pr = D.power_rankings;
  if (!pr || !pr.federation) return '<div class="note-box"><div class="note-body">Power rankings data not available yet.</div></div>';

  var rows = '';
  for (var t of pr.federation) {
    var tm_ = D.teams?.[t.team] || {};
    var lcs = '';
    for (var lk of LO) {
      var bl = t.by_league?.[lk];
      if (bl) {
        lcs += '<td class="pr-cell hm">' + bl.display.toFixed(1) + '</td>';
      } else {
        lcs += '<td class="hm" style="color:var(--text-muted);text-align:center">\u2014</td>';
      }
    }
    rows += '<tr>';
    rows += '<td class="rk">' + RE[t.rank] + '</td>';
    rows += '<td><div class="tc"><img src="' + assetPath('logos/teams/' + t.team + '.svg') + '" style="width:28px;height:28px;border-radius:4px;object-fit:contain;flex-shrink:0" onerror="this.style.display=\'none\'"><div><div class="tn" style="color:' + (tm_.color || 'var(--text)') + '">' + t.name + '</div><div class="to">' + (tm_.owner || '') + '</div></div></div></td>';
    rows += '<td class="pr-cell" style="font-size:1rem;font-weight:700">' + t.display.toFixed(1) + '</td>';
    rows += lcs;
    rows += '</tr>';
  }

  var h = '<table class="st"><thead><tr>';
  h += '<th class="n">Rk</th><th>Team</th><th class="n">PR</th>';
  for (var lk of LO) h += '<th class="n hm">' + LM[lk].emoji + ' ' + LM[lk].code + '</th>';
  h += '</tr></thead><tbody>' + rows + '</tbody></table>';
  return h;
}

function renderLeaguePR(lk) {
  var pr = D.power_rankings;
  if (!pr || !pr.leagues || !pr.leagues[lk]) return '<div class="note-box"><div class="note-body">No power rankings data for this league.</div></div>';

  var meta = pr.league_meta?.[lk] || {};
  var teams = pr.leagues[lk];
  var l = LM[lk];

  var h = '';
  h += '<div class="sch-league-bar" style="margin-bottom:.8rem"><img src="' + assetPath(l.logo) + '" onerror="this.style.display=\'none\'"><span class="name">' + l.emoji + ' ' + l.code + '</span>';
  h += '<span class="badge ' + (meta.is_frozen ? 'final' : 'live') + '">' + (meta.is_frozen ? 'Frozen' : 'Through Wk ' + meta.max_week) + '</span>';
  h += '</div>';

  // Main table
  h += '<table class="st"><thead><tr>';
  h += '<th class="n">PR#</th><th>Team</th><th class="n">W-L</th>';
  h += '<th class="n">Score</th>';
  h += '<th class="n hm">Win%</th><th class="n hm">PPG</th><th class="n hm">MOV</th>';
  h += '<th class="n hm">CON</th><th class="n hm">SOS</th><th class="n hm">MOM</th>';
  h += '</tr></thead><tbody>';

  for (var t of teams) {
    var tm_ = D.teams?.[t.team] || {};
    var monoStyle = 'font-family:\'JetBrains Mono\',monospace;font-size:.75rem;text-align:center';

    h += '<tr>';
    h += '<td class="rk">' + RE[t.new_rank] + '</td>';
    h += '<td><div class="tc"><img src="' + assetPath('logos/teams/' + t.team + '.svg') + '" style="width:24px;height:24px;border-radius:4px;object-fit:contain;flex-shrink:0" onerror="this.style.display=\'none\'"><div><div class="tn" style="color:' + (tm_.color || 'var(--text)') + '">' + t.name + '</div></div></div></td>';
    h += '<td class="rc">' + t.wins + '-' + t.losses + '</td>';
    h += '<td class="pr-cell" style="font-weight:700">' + t.display_pr.toFixed(1) + '</td>';
    h += '<td class="hm" style="' + monoStyle + '">' + t.win_pct.toFixed(3) + '</td>';
    h += '<td class="hm" style="' + monoStyle + '">' + t.ppg.toFixed(1) + '</td>';
    h += '<td class="hm" style="' + monoStyle + ';color:' + (t.mov >= 0 ? 'var(--green)' : 'var(--red)') + '">' + (t.mov >= 0 ? '+' : '') + t.mov.toFixed(1) + '</td>';
    h += '<td class="hm" style="' + monoStyle + '">' + t.consistency.toFixed(3) + '</td>';
    h += '<td class="hm" style="' + monoStyle + ';color:' + (t.sos >= 0 ? 'var(--green)' : 'var(--red)') + '">' + (t.sos >= 0 ? '+' : '') + t.sos.toFixed(3) + '</td>';
    h += '<td class="hm" style="' + monoStyle + ';color:' + (t.momentum >= 0 ? 'var(--green)' : 'var(--red)') + '">' + (t.momentum >= 0 ? '+' : '') + t.momentum.toFixed(3) + '</td>';
    h += '</tr>';
  }
  h += '</tbody></table>';

  // Z-score breakdown (collapsible)
  h += '<details style="margin-top:.8rem"><summary style="cursor:pointer;font-size:.82rem;color:var(--text-dim)">Show z-score breakdown</summary>';
  h += '<div style="overflow-x:auto;margin-top:.5rem"><table class="st" style="font-size:.75rem"><thead><tr>';
  h += '<th class="n">PR#</th><th>Team</th><th class="n">z(Win%)</th><th class="n">z(PPG)</th><th class="n">z(MOV)</th><th class="n">z(CON)</th><th class="n">z(SOS)</th><th class="n">z(MOM)</th><th class="n">Raw PR</th>';
  h += '</tr></thead><tbody>';
  for (var t of teams) {
    var tm_ = D.teams?.[t.team] || {};
    var zStyle = 'font-family:\'JetBrains Mono\',monospace;font-size:.72rem;text-align:center';
    function zc(v) { return v >= 0 ? 'color:var(--green)' : 'color:var(--red)'; }
    h += '<tr>';
    h += '<td style="text-align:center;font-size:.75rem">' + t.new_rank + '</td>';
    h += '<td style="font-size:.75rem">' + (tm_.abbr || t.name) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_win_pct) + '">' + (t.z_win_pct >= 0 ? '+' : '') + t.z_win_pct.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_ppg) + '">' + (t.z_ppg >= 0 ? '+' : '') + t.z_ppg.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_mov) + '">' + (t.z_mov >= 0 ? '+' : '') + t.z_mov.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_consistency) + '">' + (t.z_consistency >= 0 ? '+' : '') + t.z_consistency.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_sos) + '">' + (t.z_sos >= 0 ? '+' : '') + t.z_sos.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';' + zc(t.z_momentum) + '">' + (t.z_momentum >= 0 ? '+' : '') + t.z_momentum.toFixed(2) + '</td>';
    h += '<td style="' + zStyle + ';font-weight:700">' + (t.pr >= 0 ? '+' : '') + t.pr.toFixed(3) + '</td>';
    h += '</tr>';
  }
  h += '</tbody></table></div></details>';

  return h;
}

function renderPRPage() {
  var h = '<div class="fed-hero" style="padding-bottom:.8rem"><h1>Power Rankings</h1><div class="subtitle">Six-Factor Composite Rating &bull; Z-Score Normalized</div></div>';

  // Tab bar
  h += '<div class="league-tabs" style="margin-bottom:1rem">';
  h += '<button class="league-tab' + (prTab === 'federation' ? ' active' : '') + '" onclick="switchPRTab(\'federation\')">Federation</button>';
  for (var lk of LO) {
    var l = LM[lk];
    var hasData = D.power_rankings && D.power_rankings.leagues && D.power_rankings.leagues[lk];
    if (hasData) {
      h += '<button class="league-tab' + (prTab === lk ? ' active' : '') + '" onclick="switchPRTab(\'' + lk + '\')">' + l.emoji + ' ' + l.code + '</button>';
    }
  }
  h += '</div>';

  // Tab content
  if (prTab === 'federation') {
    h += renderFedPR();
  } else {
    h += renderLeaguePR(prTab);
  }

  // Race chart at bottom
  h += (typeof renderRaceChart === 'function' ? renderRaceChart() : '');

  return h;
}

window.switchPRTab = function (tab) {
  prTab = tab;
  renderPage();
};

function renderPage() {
  document.getElementById('app').innerHTML = renderPRPage();
}

window.pageInit = renderPage;
