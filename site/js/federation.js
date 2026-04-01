/* Federation Cup — Federation Standings Page */
'use strict';

function renderFed() {
  var fed = computeFed('all');
  var rows = '';
  for (var t of fed) {
    var lcs = '';
    for (var lk of LO) {
      var b = t.by_league?.[lk];
      if (b) lcs += '<td class="lc hm"><div class="lr ' + cc(b.rank) + '">#' + b.rank + '</div><div class="lp">' + b.fed_pts + 'p</div></td>';
      else lcs += '<td class="lc hm" style="color:var(--text-muted)">\u2014</td>';
    }
    var fpr = getPR(t.team_id);
    var prCell = '<td class="pr-cell">' + (fpr ? fpr.display.toFixed(1) : '\u2014') + '</td>';
    rows += '<tr class="team-row" data-tid="' + t.team_id + '" data-ctx="federation"><td class="rk">' + RE[t.federation_rank] + '</td><td><div class="tc"><img src="' + assetPath('logos/teams/' + t.team_id + '.svg') + '" style="width:28px;height:28px;border-radius:4px;object-fit:contain;flex-shrink:0" onerror="this.style.display=\'none\'"><div><div class="tn" style="color:' + (t.color || 'var(--text)') + '">' + t.name + '</div><div class="to">' + t.owner + '</div></div></div></td><td class="fp">' + t.total_fed_pts + '</td>' + prCell + lcs + '<td class="rc">' + t.combined_w + '-' + t.combined_l + '</td></tr>';
    rows += '<tr class="detail-row" id="det-fed-' + t.team_id + '"><td colspan="9"></td></tr>';
  }
  return '<div class="fed-hero"><img class="hero-logo" src="' + assetPath('logos/fed.svg') + '" alt="Federation" onerror="this.style.display=\'none\'"><h1>Federation Cup</h1><div class="subtitle">Fantasy Sports Federation &bull; Multi-Sport Dynasty League</div><div class="season-badge">' + (D.federation_season || '2025-26') + ' Season</div></div><table class="st"><thead><tr><th class="n">Rk</th><th>Team</th><th class="n">Pts</th><th class="n">PR</th><th class="n hm">' + LM.fed_fl.emoji + ' ' + LM.fed_fl.code + '</th><th class="n hm">' + LM.fed_ba.emoji + ' ' + LM.fed_ba.code + '</th><th class="n hm">' + LM.fed_hl.emoji + ' ' + LM.fed_hl.code + '</th><th class="n hm">' + LM.fed_lb.emoji + ' ' + LM.fed_lb.code + '</th><th class="n">Record</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

function renderPage() {
  document.getElementById('app').innerHTML = renderFed();
  bindRows();
}

window.pageInit = renderPage;
