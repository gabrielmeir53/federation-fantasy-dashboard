/* Federation Cup — Transactions Page */
'use strict';

var LEAGUE_META = {
  fed_fl: { code: 'FedFL', logo: 'logos/leagues/fed_fl.svg' },
  fed_fl_prev: { code: 'FedFL', logo: 'logos/leagues/fed_fl.svg' },
  fed_ba: { code: 'FedBA', logo: 'logos/leagues/fed_ba.svg' },
  fed_hl: { code: 'FedHL', logo: 'logos/leagues/fed_hl.svg' },
  fed_lb: { code: 'FedLB', logo: 'logos/leagues/fed_lb.svg' },
};
var KNOWN_SEASONS = ['2025-26'];
var allData = {};
var txTeams = {};

var TYPE_LABELS = { FA: 'Add FA', DROP: 'Drop', WW: 'Waiver Wire', TRADE: 'Trade', LINEUP_CHANGE: 'Lineup' };
function typeLabel(type) { return TYPE_LABELS[type] || type || 'Unknown'; }

function txFormatDate(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  var opts = { timeZone: 'America/New_York' };
  var dateFull = d.toLocaleDateString('en-US', { ...opts, month: 'short', day: 'numeric', year: 'numeric' });
  var mm = String(d.toLocaleString('en-US', { ...opts, month: 'numeric' }));
  var dd = String(d.toLocaleString('en-US', { ...opts, day: 'numeric' }));
  var yyyy = String(d.toLocaleString('en-US', { ...opts, year: 'numeric' }));
  var dateShort = mm.padStart(2, '0') + '/' + dd.padStart(2, '0') + '/' + yyyy;
  var timePart = d.toLocaleTimeString('en-US', { ...opts, hour: 'numeric', minute: '2-digit', hour12: true }) + ' ET';
  return '<span class="tx-date-full">' + dateFull + ' ' + timePart + '</span>'
    + '<span class="tx-date-mobile"><span class="tx-date-d">' + dateShort + '</span><span class="tx-date-t">' + timePart + '</span></span>';
}

function getAllTransactions() {
  var txns = [];
  for (var [season, sData] of Object.entries(allData)) {
    if (!sData || !sData.leagues) continue;
    for (var [lk, ld] of Object.entries(sData.leagues)) {
      for (var tx of (ld.transactions || [])) {
        for (var p of (tx.players || [])) {
          txns.push({
            id: tx.id, date: tx.date, season: season, leagueKey: lk,
            leagueCode: LEAGUE_META[lk]?.code || ld.sport || lk,
            leagueLogo: LEAGUE_META[lk]?.logo || '',
            teamName: tx.team_name, fedId: tx.fed_id,
            playerName: p.name, playerPos: p.position, playerTeam: p.real_team, type: p.type,
          });
        }
      }
    }
  }
  txns.sort(function (a, b) { return new Date(b.date) - new Date(a.date); });
  return txns;
}

function getCheckedValues(groupName) {
  var checks = document.querySelectorAll('#txSidebar input[data-group="' + groupName + '"]:checked');
  return [...checks].map(function (c) { return c.value; });
}

function renderSidebar() {
  var sidebar = document.getElementById('txSidebar');
  var h = '';
  var seasons = Object.keys(allData).sort();
  h += '<div class="sidebar-group"><h3>Season</h3>';
  for (var s of seasons) h += '<label class="sidebar-cb"><input type="checkbox" data-group="season" value="' + s + '" checked>' + s + '</label>';
  h += '</div>';

  var leagueSet = new Map();
  for (var sData of Object.values(allData)) {
    if (!sData || !sData.leagues) continue;
    for (var [lk, ld] of Object.entries(sData.leagues)) {
      if (!leagueSet.has(lk)) leagueSet.set(lk, LEAGUE_META[lk]?.code || ld.sport || lk);
    }
  }
  h += '<div class="sidebar-group"><h3>League</h3>';
  for (var [lk, code] of leagueSet) h += '<label class="sidebar-cb"><input type="checkbox" data-group="league" value="' + lk + '" checked>' + code + '</label>';
  h += '</div>';

  var teamSet = new Set();
  for (var sData of Object.values(allData)) {
    if (!sData || !sData.leagues) continue;
    for (var ld of Object.values(sData.leagues)) {
      for (var tx of (ld.transactions || [])) { if (tx.fed_id) teamSet.add(tx.fed_id); }
    }
  }
  var sortedTeams = [...teamSet].sort(function (a, b) {
    var na = txTeams[a]?.abbr || a, nb = txTeams[b]?.abbr || b;
    return na.localeCompare(nb);
  });
  h += '<div class="sidebar-group"><h3>Team</h3>';
  for (var tid of sortedTeams) {
    var t = txTeams[tid];
    var display = t ? (t.abbr + ' - ' + t.name) : tid;
    h += '<label class="sidebar-cb"><input type="checkbox" data-group="team" value="' + tid + '" checked>' + display + '</label>';
  }
  h += '</div>';

  h += '<div class="sidebar-group"><h3>Type</h3>';
  for (var [code, label] of Object.entries(TYPE_LABELS)) {
    h += '<label class="sidebar-cb"><input type="checkbox" data-group="type" value="' + code + '" checked>' + label + '</label>';
  }
  h += '</div>';

  sidebar.innerHTML = h;
  sidebar.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.addEventListener('change', renderTable); });
}

function renderTable() {
  var container = document.getElementById('txContent');
  var countEl = document.getElementById('txCount');
  var allTxns = getAllTransactions();
  if (!allTxns.length) {
    container.innerHTML = '<div class="no-data"><h3>No Transaction Data</h3><p>Run the scraper to fetch transactions: <code>python scrape_fantrax.py</code></p></div>';
    countEl.textContent = '';
    return;
  }
  var checkedSeasons = getCheckedValues('season');
  var checkedLeagues = getCheckedValues('league');
  var checkedTeams = getCheckedValues('team');
  var checkedTypes = getCheckedValues('type');
  var searchFilter = document.getElementById('filterSearch').value.toLowerCase().trim();
  var dateFrom = document.getElementById('filterDateFrom').value;
  var dateTo = document.getElementById('filterDateTo').value;
  var txns = allTxns;
  txns = txns.filter(function (t) { return checkedSeasons.includes(t.season); });
  txns = txns.filter(function (t) { return checkedLeagues.includes(t.leagueKey); });
  txns = txns.filter(function (t) { return checkedTeams.length === 0 || checkedTeams.includes(t.fedId); });
  txns = txns.filter(function (t) { return checkedTypes.includes(t.type); });
  if (dateFrom) txns = txns.filter(function (t) { return t.date && t.date.substring(0, 10) >= dateFrom; });
  if (dateTo) txns = txns.filter(function (t) { return t.date && t.date.substring(0, 10) <= dateTo; });
  if (searchFilter) {
    txns = txns.filter(function (t) {
      var teamAbbr = txTeams[t.fedId]?.abbr || '';
      var teamName = t.teamName || '';
      var tLabel = typeLabel(t.type).toLowerCase();
      return t.playerName.toLowerCase().includes(searchFilter) || teamAbbr.toLowerCase().includes(searchFilter) || teamName.toLowerCase().includes(searchFilter) || tLabel.includes(searchFilter) || t.leagueCode.toLowerCase().includes(searchFilter) || (t.playerPos || '').toLowerCase().includes(searchFilter) || (t.playerTeam || '').toLowerCase().includes(searchFilter);
    });
  }
  countEl.textContent = txns.length + ' transaction' + (txns.length !== 1 ? 's' : '');
  if (!txns.length) { container.innerHTML = '<div class="no-data"><p>No transactions match the current filters.</p></div>'; return; }
  var h = '<table class="tx-table"><thead><tr><th>Date</th><th>League</th><th>Team</th><th>Type</th><th>Player</th></tr></thead><tbody>';
  for (var tx of txns) {
    var t = txTeams[tx.fedId];
    var teamColor = t?.color || 'var(--text)';
    var teamAbbr = t?.abbr || tx.teamName;
    h += '<tr>';
    h += '<td class="tx-date">' + txFormatDate(tx.date) + '</td>';
    h += '<td class="tx-league">' + (tx.leagueLogo ? '<img src="' + assetPath(tx.leagueLogo) + '" onerror="this.style.display=\'none\'">' : '') + tx.leagueCode + '</td>';
    h += '<td><div class="tx-team">' + (tx.fedId ? '<img src="' + assetPath('logos/teams/' + tx.fedId + '.svg') + '" onerror="this.style.display=\'none\'">' : '') + '<span class="tx-team-name" style="color:' + teamColor + '">' + teamAbbr + '</span></div></td>';
    h += '<td><span class="tx-type ' + (tx.type || '') + '">' + typeLabel(tx.type) + '</span></td>';
    h += '<td><span class="tx-player">' + tx.playerName + '</span><span class="tx-player-pos">' + (tx.playerPos || '') + '</span>';
    if (tx.playerTeam) h += ' <span class="tx-player-team">(' + tx.playerTeam + ')</span>';
    h += '</td></tr>';
  }
  h += '</tbody></table>';
  container.innerHTML = h;
}

async function loadTxData() {
  for (var season of KNOWN_SEASONS) {
    try {
      var resp = await fetch(assetPath('data/transactions_' + season + '.json'));
      if (resp.ok) {
        var data = await resp.json();
        allData[season] = data;
        if (data.teams) txTeams = { ...txTeams, ...data.teams };
      }
    } catch (e) { /* ignore missing files */ }
  }
  if (D && D.teams) txTeams = { ...txTeams, ...D.teams };
  renderSidebar();
  renderTable();
  document.getElementById('filterSearch').addEventListener('input', renderTable);
  document.getElementById('filterDateFrom').addEventListener('change', renderTable);
  document.getElementById('filterDateTo').addEventListener('change', renderTable);
}

window.pageInit = function () {
  // Transactions page loads its own data separately
  loadTxData();
};
