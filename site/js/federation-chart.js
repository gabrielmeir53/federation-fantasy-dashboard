/* Federation Cup — Race Chart */
'use strict';

var FED_PTS = [0, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1];

function computeRaceData() {
  if (!D || !D.league_data) return null;

  var teamIds = Object.keys(D.teams || {});
  if (!teamIds.length) return null;

  // Find max completed period across active leagues
  var maxWeek = 0;
  var activeLeagues = [];
  LO.forEach(function (lk) {
    var ld = D.league_data[lk];
    if (!ld || !ld.matchups) return;
    var completed = 0;
    (ld.matchups || []).forEach(function (m) {
      if (m.complete && m.period > completed) completed = m.period;
    });
    if (completed > 0) {
      activeLeagues.push(lk);
      if (completed > maxWeek) maxWeek = completed;
    }
  });

  if (!maxWeek || !activeLeagues.length) return null;

  // For each week 1..maxWeek, compute projected fed points per team
  var weekLabels = [];
  var teamSeries = {}; // teamId -> [pts_week1, pts_week2, ...]
  teamIds.forEach(function (tid) { teamSeries[tid] = []; });

  for (var week = 1; week <= maxWeek; week++) {
    weekLabels.push('W' + week);
    var fedPts = {};
    teamIds.forEach(function (tid) { fedPts[tid] = 0; });

    // For each active league, compute standings through this week
    activeLeagues.forEach(function (lk) {
      var ld = D.league_data[lk];
      // Accumulate W-L-PF through this week's matchups
      var records = {};
      teamIds.forEach(function (tid) { records[tid] = { w: 0, l: 0, pf: 0 }; });

      (ld.matchups || []).forEach(function (m) {
        if (!m.complete || m.period > week) return;
        var aId = m.away_fed_id, hId = m.home_fed_id;
        var aScore = parseFloat(m.away_score) || 0;
        var hScore = parseFloat(m.home_score) || 0;
        if (aId && records[aId] !== undefined) {
          records[aId].pf += aScore;
          if (aScore > hScore) records[aId].w++; else if (hScore > aScore) records[aId].l++;
        }
        if (hId && records[hId] !== undefined) {
          records[hId].pf += hScore;
          if (hScore > aScore) records[hId].w++; else if (aScore > hScore) records[hId].l++;
        }
      });

      // Rank teams by W desc, then PF desc
      var ranked = teamIds.slice().sort(function (a, b) {
        if (records[b].w !== records[a].w) return records[b].w - records[a].w;
        return records[b].pf - records[a].pf;
      });

      // Assign fed points based on rank
      ranked.forEach(function (tid, idx) {
        fedPts[tid] += FED_PTS[idx + 1] || 0;
      });
    });

    // Store this week's total for each team
    teamIds.forEach(function (tid) {
      teamSeries[tid].push(fedPts[tid]);
    });
  }

  return { labels: weekLabels, series: teamSeries, teamIds: teamIds };
}

function renderRaceChart() {
  var data = computeRaceData();
  if (!data) return '';

  var teams = D.teams || {};
  var datasets = [];

  // Sort teams by final week points (descending) for legend order
  var sorted = data.teamIds.slice().sort(function (a, b) {
    var sa = data.series[a], sb = data.series[b];
    return (sb[sb.length - 1] || 0) - (sa[sa.length - 1] || 0);
  });

  sorted.forEach(function (tid) {
    var t = teams[tid] || {};
    var color = t.color || '#666';
    datasets.push({
      label: t.abbr || tid,
      data: data.series[tid],
      borderColor: color,
      backgroundColor: color + '22',
      borderWidth: 2.5,
      pointRadius: 0,
      pointHoverRadius: 5,
      tension: 0.2,
      fill: false,
    });
  });

  // Create chart container
  var html = '<div class="race-chart-container" style="margin:24px 0;padding:20px;background:var(--card);border-radius:12px;border:1px solid var(--border)">';
  html += '<h2 style="margin:0 0 12px;font-family:Palatino,serif;font-size:1.3rem;color:var(--text)">Federation Cup Race</h2>';
  html += '<div style="position:relative;height:340px"><canvas id="raceChart"></canvas></div>';
  html += '</div>';

  // Defer chart creation until canvas is in DOM
  setTimeout(function () {
    var ctx = document.getElementById('raceChart');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'line',
      data: { labels: data.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 12, padding: 8,
              font: { family: 'Palatino', size: 11 },
              color: '#5c5c5c'
            }
          },
          tooltip: {
            backgroundColor: '#ffffff',
            titleColor: '#1a1a1a',
            bodyColor: '#333',
            borderColor: '#d4d3cc',
            borderWidth: 1,
            titleFont: { family: 'Palatino', size: 13 },
            bodyFont: { family: 'Palatino', size: 12 },
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': ' + ctx.parsed.y + ' pts';
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(0,0,0,0.06)' },
            ticks: { color: '#5c5c5c', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y: {
            grid: { color: 'rgba(0,0,0,0.06)' },
            ticks: { color: '#5c5c5c', font: { family: 'JetBrains Mono', size: 10 } },
            title: { display: true, text: 'Projected Fed Pts', color: '#5c5c5c', font: { family: 'Palatino', size: 12 } }
          }
        }
      }
    });
  }, 50);

  return html;
}
