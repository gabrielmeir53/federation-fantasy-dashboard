/* Federation Cup — Schedule Page */
'use strict';

function renderSchedulePage() {
  var h = '<div class="fed-hero" style="padding-bottom:.8rem"><h1 style="font-size:1.8rem">Schedule</h1><div class="subtitle">Weekly Matchups &bull; All Leagues</div></div>';
  for (var lk of LO) {
    var eff = getEff(lk), sd = eff.data;
    if (!sd || !sd.matchups || !sd.matchups.length) continue;
    var l = LM[lk], meta = getSchMeta(lk);
    if (!schWeek[lk]) schWeek[lk] = getCurrentWeek(lk);
    var wk = schWeek[lk], pInfo = meta.periods?.[String(wk)] || {};
    var dateStr = (pInfo.start && pInfo.end) ? formatDate(pInfo.start) + ' \u2014 ' + formatDate(pInfo.end) : '';
    var status = pInfo.complete ? 'final' : pInfo.current ? 'live' : 'upcoming';
    var statusLabel = pInfo.complete ? 'Final' : pInfo.current ? 'Live' : 'Upcoming';
    var rivalry = meta.rivalry_week === wk;
    h += '<div class="sch-league-section">';
    h += '<div class="sch-league-bar"><img src="' + assetPath(l.logo) + '" onerror="this.style.display=\'none\'"><span class="name">' + l.emoji + ' ' + l.code + '</span>';
    h += '<span class="badge ' + status + '">' + statusLabel + '</span>';
    if (rivalry) h += '<span class="badge rivalry-badge">Rivalry Week</span>';
    h += '<span class="dates">' + dateStr + '</span></div>';
    h += renderWeekBar(lk, wk);
    h += renderMatchupCards(lk, wk);
    h += '</div>';
  }
  if (!h.includes('sch-league-section')) h += '<div style="color:var(--text-muted);padding:2rem;text-align:center">No schedule data available. Run the scraper first.</div>';
  return h;
}

function renderPage() {
  document.getElementById('app').innerHTML = renderSchedulePage();
  bindSchedule(renderPage);
}

window.pageInit = renderPage;
