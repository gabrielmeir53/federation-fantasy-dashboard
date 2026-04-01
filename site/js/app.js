/* Federation Cup — Shared Application Core */
'use strict';

// ===== LEAGUE CONFIG =====
const LM = {
  fed_fl: { code: 'FedFL', emoji: '\u{1F3C8}', sport: 'NFL', logo: 'logos/leagues/fed_fl.svg', color: '#013369' },
  fed_ba: { code: 'FedBA', emoji: '\u{1F3C0}', sport: 'NBA', logo: 'logos/leagues/fed_ba.svg', color: '#c9082a' },
  fed_hl: { code: 'FedHL', emoji: '\u{1F3D2}', sport: 'NHL', logo: 'logos/leagues/fed_hl.svg', color: '#333' },
  fed_lb: { code: 'FedLB', emoji: '\u26BE', sport: 'MLB', logo: 'logos/leagues/fed_lb.svg', color: '#002d72' },
};
const LO = ['fed_fl', 'fed_ba', 'fed_hl', 'fed_lb'];
const RE = ['', '&#x1F947;', '&#x1F948;', '&#x1F949;', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

// ===== GLOBAL STATE =====
let D = {};
let fedMode = 'active';
let schWeek = {};
var _lazyCache = {};

// ===== POWER RANKINGS HELPER =====
function getPR(teamId, leagueKey) {
  var pr = D && D.power_rankings;
  if (!pr) return null;
  if (!leagueKey) {
    return pr.federation ? pr.federation.find(function(p) { return p.team === teamId; }) : null;
  }
  return pr.leagues && pr.leagues[leagueKey]
    ? pr.leagues[leagueKey].find(function(p) { return p.team === teamId; })
    : null;
}

// ===== BASE PATH =====
const BASE = window.FED_BASE || '';

function assetPath(path) { return BASE + path; }

// ===== PAGE DATA MANIFESTS =====
const PAGE_DATA = {
  federation:    { eager: ['core','league_fed_fl','league_fed_ba','league_fed_hl','league_fed_lb','nfl_previous_season','power_rankings','federation'] },
  league_fed_fl: { eager: ['core','league_fed_fl','nfl_previous_season','power_rankings'] },
  league_fed_ba: { eager: ['core','league_fed_ba','power_rankings'] },
  league_fed_hl: { eager: ['core','league_fed_hl','power_rankings'] },
  league_fed_lb: { eager: ['core','league_fed_lb','power_rankings'] },
  rankings:      { eager: ['core','league_fed_fl','league_fed_ba','league_fed_hl','league_fed_lb','power_rankings'] },
  schedule:      { eager: ['core','league_fed_fl','league_fed_ba','league_fed_hl','league_fed_lb','nfl_previous_season'] },
  teams:         { eager: ['core','league_fed_fl','league_fed_ba','league_fed_hl','league_fed_lb','power_rankings'] },
  transactions:  { eager: ['core'] },
  static:        { eager: ['core'] },
};

// ===== DATA LOADING =====
var DATA_PATH = assetPath(window.FED_DATA_DIR || 'data/');

function _mergeChunk(name, data) {
  if (name.startsWith('league_')) {
    D.league_data = D.league_data || {};
    D.league_data[name.replace('league_', '')] = data;
  } else if (name === 'core') {
    Object.assign(D, data);
  } else {
    Object.assign(D, data);
  }
}

async function loadCombined() {
  var r = await fetch(DATA_PATH + 'fed_combined.json');
  if (!r.ok) throw new Error('HTTP ' + r.status);
  var data = await r.json();
  Object.assign(D, data);
}

async function loadData() {
  var manifest = PAGE_DATA[window.PAGE_ID];
  if (!manifest) {
    try { await loadCombined(); } catch (e) { showError('Failed to load data', e); return; }
    try { onReady(); } catch (e) { showError('Dashboard error', e); }
    return;
  }
  try {
    await Promise.all(manifest.eager.map(function (name) {
      return fetch(DATA_PATH + name + '.json').then(function (r) {
        if (!r.ok) throw new Error(name + ': HTTP ' + r.status);
        return r.json();
      }).then(function (data) { _mergeChunk(name, data); });
    }));
  } catch (e) {
    console.warn('Split load failed, falling back to combined:', e);
    try { await loadCombined(); } catch (e2) { showError('Failed to load data', e2); return; }
  }
  try { onReady(); } catch (e) { showError('Dashboard error', e); }
}

async function loadLazy(name) {
  if (_lazyCache[name]) return _lazyCache[name];
  _lazyCache[name] = fetch(DATA_PATH + name + '.json').then(function (r) {
    if (!r.ok) throw new Error(name + ': HTTP ' + r.status);
    return r.json();
  }).then(function (data) { _mergeChunk(name, data); return data; });
  return _lazyCache[name];
}

function showError(msg, e) {
  console.error(msg, e);
  const el = document.getElementById('loading');
  if (el) {
    el.innerHTML = '<div style="color:#c06060">' + msg + '</div>'
      + '<div style="font-size:.75rem;color:var(--text-dim);margin-top:.5rem;font-family:JetBrains Mono,monospace;word-break:break-all">' + String(e) + '</div>'
      + '<div style="font-size:.8rem;color:var(--text-dim);margin-top:1rem">Press F12 for details.</div>';
  }
}

function onReady() {
  const loadingEl = document.getElementById('loading');
  if (loadingEl) loadingEl.style.display = 'none';
  const d = new Date(D.scraped_at);
  const updEl = document.getElementById('lastUpdated');
  if (updEl) updEl.textContent = 'Updated ' + d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (typeof window.pageInit === 'function') window.pageInit();
}

// ===== NAV INIT =====
function initNav() {
  // Hamburger toggle
  const hamburger = document.querySelector('.hamburger');
  if (hamburger) {
    hamburger.addEventListener('click', function () {
      document.querySelector('.nav-tabs').classList.toggle('open');
    });
  }
  // Close mobile nav on link click
  document.querySelectorAll('.nav-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      const navTabs = document.querySelector('.nav-tabs');
      if (navTabs) navTabs.classList.remove('open');
    });
  });
}

// ===== UTILITY FUNCTIONS =====
function tm(id) { return D.teams?.[id] || {}; }
function cc(r) { return r === 1 ? 'c1' : r === 2 ? 'c2' : r === 3 ? 'c3' : r <= 6 ? 'ct' : r <= 9 ? 'cm' : 'cb'; }
function ld(k) { return D.league_data?.[k]; }

function getRoster(lk, yid) {
  const d = ld(lk);
  if (!d?.rosters) return [];
  for (const [, r] of Object.entries(d.rosters)) if (r.fed_id === yid) return r.players || [];
  return [];
}

function isActive(lk) {
  const d = D?.league_data?.[lk];
  if (!d?.standings) return false;
  return d.standings.some(function (s) { return (s.w || 0) + (s.l || 0) > 0; });
}

function getEff(lk) {
  const d = D?.league_data?.[lk];
  if (lk === 'fed_fl') {
    const z = d?.standings?.every(function (s) { return s.w === 0 && s.l === 0; });
    if (z && D?.nfl_previous_season) return { data: D.nfl_previous_season, isPrev: true };
  }
  return { data: d, isPrev: false };
}

// ===== REAL TEAM ABBREVIATIONS =====
const TEAM_ABBR = {
  // NBA
  'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN','Charlotte Hornets':'CHA',
  'Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE','Dallas Mavericks':'DAL','Denver Nuggets':'DEN',
  'Detroit Pistons':'DET','Golden State Warriors':'GSW','Houston Rockets':'HOU','Indiana Pacers':'IND',
  'Los Angeles Clippers':'LAC','Los Angeles Lakers':'LAL','Memphis Grizzlies':'MEM','Miami Heat':'MIA',
  'Milwaukee Bucks':'MIL','Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NOP','New York Knicks':'NYK',
  'Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI','Phoenix Suns':'PHX',
  'Portland Trail Blazers':'POR','Sacramento Kings':'SAC','San Antonio Spurs':'SAS','Toronto Raptors':'TOR',
  'Utah Jazz':'UTA','Washington Wizards':'WAS',
  // NHL
  'Anaheim Ducks':'ANA','Boston Bruins':'BOS','Buffalo Sabres':'BUF','Calgary Flames':'CGY',
  'Carolina Hurricanes':'CAR','Chicago Blackhawks':'CHI','Colorado Avalanche':'COL','Columbus Blue Jackets':'CBJ',
  'Dallas Stars':'DAL','Detroit Red Wings':'DET','Edmonton Oilers':'EDM','Florida Panthers':'FLA',
  'Los Angeles Kings':'LAK','Minnesota Wild':'MIN','Montreal Canadiens':'MTL','Nashville Predators':'NSH',
  'New Jersey Devils':'NJD','New York Islanders':'NYI','New York Rangers':'NYR','Ottawa Senators':'OTT',
  'Philadelphia Flyers':'PHI','Pittsburgh Penguins':'PIT','San Jose Sharks':'SJS','Seattle Kraken':'SEA',
  'St. Louis Blues':'STL','Tampa Bay Lightning':'TBL','Toronto Maple Leafs':'TOR','Utah Mammoth':'UMM',
  'Vancouver Canucks':'VAN','Vegas Golden Knights':'VGK','Washington Capitals':'WSH','Winnipeg Jets':'WPG',
  // MLB
  'Arizona Diamondbacks':'ARI','Athletics':'ATH','Atlanta Braves':'ATL','Baltimore Orioles':'BAL',
  'Boston Red Sox':'BOS','Chicago Cubs':'CHC','Chicago White Sox':'CWS','Cincinnati Reds':'CIN',
  'Cleveland Guardians':'CLE','Colorado Rockies':'COL','Detroit Tigers':'DET','Houston Astros':'HOU',
  'Kansas City Royals':'KC','Los Angeles Angels':'LAA','Los Angeles Dodgers':'LAD','Miami Marlins':'MIA',
  'Milwaukee Brewers':'MIL','Minnesota Twins':'MIN','New York Mets':'NYM','New York Yankees':'NYY',
  'Philadelphia Phillies':'PHI','Pittsburgh Pirates':'PIT','San Diego Padres':'SD','San Francisco Giants':'SF',
  'Seattle Mariners':'SEA','St. Louis Cardinals':'STL','Tampa Bay Rays':'TB','Texas Rangers':'TEX',
  'Toronto Blue Jays':'TOR','Washington Nationals':'WAS',
  // Special
  'Not on a team':'FA'
};
function teamAbbr(name) { return TEAM_ABBR[name] || name; }

// ===== POSITION MAPPING =====
const FULL_POS_MAP = {
  // NBA (Fantrax returns truncated: "Point", "Shooting", "Small", "Power", "Center", "Flex")
  'Point':'PG','Shooting':'SG','Small':'SF','Power':'PF',
  // NHL (Fantrax returns: "Center", "Defense", "Goalie", "Left", "Right", "Skater")
  'Center':'C','Defense':'D','Goalie':'G','Left':'LW','Right':'RW','Skater':'Sk',
  // MLB (Fantrax returns: "Catcher", "Outfield", "Relief", "Shortstop", "Starting", "Utility")
  'Catcher':'C','Outfield':'OF','Relief':'RP','Shortstop':'SS','Starting':'SP','Utility':'Util',
  // NFL
  'RWT':'Flex','DST':'D/ST',
  // Shared
  'Flex':'Flex'
};

const POSMAP = {
  NBA: { P: 'PG', S: 'SG', F: 'F', C: 'C', U: 'Util', G: 'G', Flx: 'Flex' },
  MLB: { C: 'C', R: 'RP', S: 'SP', D: 'DH', U: 'Util', O: 'OF', '1': '1B', '2': '2B', '3': '3B' },
  NFL: { Q: 'QB', R: 'RB', W: 'WR', T: 'TE', K: 'K', D: 'D/ST', F: 'Flex' },
  NHL: { C: 'C', L: 'LW', R: 'RW', D: 'D', G: 'G', S: 'Sk' }
};

function cleanPos(p, sport) {
  var pos = p.position || p.positions || p.slot || '';
  pos = String(pos);
  // Handle bracketed format: [002:1st Base:1B] → 1B
  var m = pos.match(/\[\d+:([^:\]]+):([A-Za-z0-9/]+)\]/);
  if (m) return m[2];
  // Handle simpler bracketed: [1]:QB → QB
  var m2 = pos.match(/\[?(\d+):([A-Za-z/]+)/);
  if (m2) pos = m2[2];
  pos = pos.replace(/Position\(|\)/g, '').replace(/Slot\s*:\s*/i, '').trim();
  // Check full word map first (Center → C, Point → PG, etc.)
  if (FULL_POS_MAP[pos]) return FULL_POS_MAP[pos];
  // Then single/double char map
  if (sport && pos.length <= 2) { var map = POSMAP[sport]; if (map && map[pos]) pos = map[pos]; }
  return pos.substring(0, 6);
}

// ===== SHARED RENDERING =====
function renderPlayerRow(p, cls, sport) {
  var pos = cleanPos(p, sport), name = p.name || '', team = teamAbbr(p.real_team || '');
  return '<div class="rp ' + cls + '"><span class="rps">' + (pos || '--') + '</span><span class="rpn">' + name + '</span><span class="rpt">' + team + '</span></div>';
}

function renderRosterBlock(players, sport) {
  if (!players || !players.length) return '<div style="color:var(--text-muted);padding:.4rem;font-size:.78rem">No roster data</div>';
  var act = players.filter(function (p) { return !['INJURED_RESERVE', 'RESERVE', 'IR'].includes(p.status || ''); });
  var res = players.filter(function (p) { return (p.status || '') === 'RESERVE'; });
  var ir = players.filter(function (p) { return (p.status || '') === 'INJURED_RESERVE' || (p.status || '') === 'IR'; });
  var s = '';
  if (act.length) s += '<div class="stit">Active (' + act.length + ')</div><div class="rg">' + act.map(function (p) { return renderPlayerRow(p, '', sport); }).join('') + '</div>';
  if (res.length) s += '<div class="stit">Reserve (' + res.length + ')</div><div class="rg">' + res.map(function (p) { return renderPlayerRow(p, 'res', sport); }).join('') + '</div>';
  if (ir.length) s += '<div class="stit">IR (' + ir.length + ')</div><div class="rg">' + ir.map(function (p) { return renderPlayerRow(p, 'ir', sport); }).join('') + '</div>';
  return s;
}

function renderDraftPicks(tid, filterLeague) {
  var dp = D.draft_picks_by_team?.[tid];
  if (!dp || !Object.keys(dp).length) return '';
  var leagueList = filterLeague ? [filterLeague] : LO;
  var h = '<div class="stit" style="margin-top:1.5rem">Future Draft Picks</div>';
  for (var szn of Object.keys(dp).sort()) {
    h += '<div class="dp-season"><div class="dp-season-title">' + szn + '</div>';
    for (var lk of leagueList) {
      var picks = dp[szn]?.[lk]; if (!picks || !picks.length) continue;
      h += '<div class="dp-league"><div class="dp-league-name">' + LM[lk].code + '</div><div class="dp-picks">';
      for (var p of picks) {
        var traded = p.traded ? 'traded' : '';
        var from = p.traded ? ' <span class="from">via ' + ((D.teams?.[p.original_fed_id]?.abbr) || p.original_team) + '</span>' : '';
        h += '<div class="dp-pick ' + traded + '">Rd ' + p.round + from + '</div>';
      }
      h += '</div></div>';
    }
    h += '</div>';
  }
  return h;
}

function renderDetailContent(tid, context) {
  var m = tm(tid), sc = '';
  var fed = computeFed(fedMode).find(function (t) { return t.team_id === tid; });
  if (fed) {
    sc += '<div class="sc"><div class="l">Fed Rank</div><div class="v" style="color:var(--accent)">#' + fed.federation_rank + '</div></div>';
    sc += '<div class="sc"><div class="l">Fed Points</div><div class="v">' + fed.total_fed_pts + '</div></div>';
    sc += '<div class="sc"><div class="l">Record</div><div class="v">' + fed.combined_w + '-' + fed.combined_l + '</div></div>';
    var fedPr = getPR(tid);
    if (fedPr) sc += '<div class="sc"><div class="l">Fed PR</div><div class="v" style="color:var(--blue)">' + fedPr.display.toFixed(1) + '</div></div>';
    for (var lk of LO) {
      var b = fed.by_league?.[lk];
      var lpr = getPR(tid, lk);
      var prTag = lpr ? ' <span style="font-size:.72rem;color:var(--blue)">PR ' + lpr.display_pr.toFixed(1) + '</span>' : '';
      if (b) sc += '<div class="sc"><div class="l">' + LM[lk].code + '</div><div class="v"><span class="' + cc(b.rank) + '">#' + b.rank + '</span> <span style="font-size:.72rem;color:var(--text-dim)">' + b.w + '-' + b.l + '</span>' + prTag + '</div></div>';
    }
  }
  // FAAB for current league context
  if (context !== 'federation') {
    var effCtx = getEff(context), srcCtx = effCtx.data;
    if (srcCtx?.standings) {
      var tSt = srcCtx.standings.find(function(s) { return s.fed_id === tid; });
      if (tSt && tSt.faab_remaining !== undefined) {
        sc += '<div class="sc"><div class="l">FAAB</div><div class="v">$' + Math.round(tSt.faab_remaining) + '</div></div>';
      }
    }
  }
  if (context === 'federation') {
    return '<div class="sg">' + sc + '</div><div style="margin-top:.8rem"><a href="' + assetPath('team.html?id=' + tid) + '" style="color:var(--accent);font-size:.82rem;text-decoration:none">View Team Page &rarr;</a></div>';
  }
  var rh = '';
  var leagueKeys = [context];
  for (var lk of leagueKeys) {
    var l = LM[lk], pl = getRoster(lk, tid);
    if (lk === 'fed_fl' && (!pl || !pl.length)) {
      var prev = D.nfl_previous_season;
      if (prev?.rosters) for (var [, r] of Object.entries(prev.rosters)) if (r.fed_id === tid) { pl = r.players || []; break; }
    }
    if (pl && pl.length) rh += '<div style="margin-top:.8rem"><div class="sh"><img src="' + assetPath(l.logo) + '" onerror="this.style.display=\'none\'">' + l.code + ' Roster (' + pl.length + ')</div>' + renderRosterBlock(pl, l.sport) + '</div>';
  }
  rh += renderDraftPicks(tid, context);
  return '<div class="sg">' + sc + '</div>' + rh;
}

function computeFed(mode) {
  var teams = {};
  for (var [tid, m] of Object.entries(D.teams || {}))
    teams[tid] = { team_id: tid, owner: m.owner, name: m.name, abbr: m.abbr, color: m.color, logo: m.logo || '', total_fed_pts: 0, by_league: {}, championships: 0, combined_w: 0, combined_l: 0, active_leagues: 0 };
  for (var lk of LO) {
    var active = isActive(lk), eff = getEff(lk), data = eff.data;
    if (!data?.standings) continue; if (mode === 'active' && !active && !eff.isPrev) continue;
    for (var e of data.standings) {
      var yid = e.fed_id; if (!yid || !teams[yid]) continue;
      var r = e.rank, w = e.w || 0, l = e.l || 0, fp = 13 - r;
      teams[yid].total_fed_pts += fp; teams[yid].by_league[lk] = { rank: r, fed_pts: fp, w: w, l: l, pf: e.pf || 0, isPrev: eff.isPrev };
      if (r === 1) teams[yid].championships++;
      teams[yid].combined_w += w; teams[yid].combined_l += l; teams[yid].active_leagues++;
    }
  }
  var s = Object.values(teams).sort(function (a, b) { return (b.total_fed_pts - a.total_fed_pts) || (b.championships - a.championships) || ((b.combined_w / (b.combined_w + b.combined_l || 1)) - (a.combined_w / (a.combined_w + a.combined_l || 1))); });
  s.forEach(function (t, i) { t.federation_rank = i + 1; });
  return s;
}

// ===== SCHEDULE / MATCHUP HELPERS =====
function getSchMeta(lk) { return getEff(lk).data?.schedule_meta || {}; }
function getMatchups(lk) { return getEff(lk).data?.matchups || []; }
function getPeriodNums(lk) { var m = getSchMeta(lk); return Object.keys(m.periods || {}).map(Number).sort(function (a, b) { return a - b; }); }
function getCurrentWeek(lk) { var m = getSchMeta(lk); if (m.current_period) return m.current_period; if (m.last_completed) return m.last_completed; var nums = getPeriodNums(lk); return nums.length ? nums[0] : 1; }
function formatDate(iso) { if (!iso) return ''; var d = new Date(iso + 'T12:00:00'); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }

function renderMatchupCards(lk, period) {
  var mus = getMatchups(lk).filter(function (m) { return m.period === period; });
  if (!mus.length) return '<div style="color:var(--text-muted);padding:.5rem;font-size:.78rem">No matchups for this period</div>';
  var meta = getSchMeta(lk), pInfo = meta.periods?.[String(period)] || {};
  var playoffRound = '';
  if (pInfo.is_playoff) {
    var pp = Object.entries(meta.periods || {}).filter(function ([k, v]) { return v.is_playoff; }).map(function ([k]) { return Number(k); }).sort(function (a, b) { return a - b; });
    var ri = pp.indexOf(period), t = pp.length;
    if (ri === t - 1) playoffRound = 'Championship'; else if (ri === t - 2) playoffRound = 'Semifinals'; else playoffRound = 'Quarterfinals';
  }
  var h = '<div class="mu-grid">';
  for (var m of mus) {
    var isActualBye = m.away_name === 'None/Bye' || m.home_name === 'None/Bye';
    var isSeedPlaceholder = (!m.away_fed_id || !m.home_fed_id) && !isActualBye;
    if (isActualBye) {
      var byeId = m.home_fed_id || m.away_fed_id, byeT = byeId ? tm(byeId) : {};
      var byeName = byeT.abbr || (m.home_fed_id ? m.home_name : m.away_name);
      h += '<div class="mu-card" style="justify-content:center;border-style:dashed">';
      h += (byeId ? '<img src="' + assetPath('logos/teams/' + byeId + '.svg') + '" style="width:22px;height:22px;border-radius:3px;object-fit:contain;margin-right:.35rem" onerror="this.style.display=\'none\'">' : '');
      h += '<span style="font-family:Palatino,serif;font-size:.82rem;font-weight:500;color:' + (byeT.color || 'var(--text)') + '">' + byeName + '</span>';
      h += '<span style="color:var(--text-muted);font-size:.72rem;margin-left:.5rem">&mdash; BYE</span>';
      h += '</div>';
      continue;
    }
    if (isSeedPlaceholder) {
      h += '<div class="mu-card" style="justify-content:center;border-style:dashed;color:var(--text-muted)">';
      h += '<span style="font-family:Palatino,serif;font-size:.78rem">' + m.away_name + '</span>';
      h += '<span style="font-size:.6rem;margin:0 .4rem">vs</span>';
      h += '<span style="font-family:Palatino,serif;font-size:.78rem">' + m.home_name + '</span>';
      h += '<span style="font-size:.6rem;margin-left:.5rem">(TBD)</span>';
      h += '</div>';
      continue;
    }
    var at = m.away_fed_id ? tm(m.away_fed_id) : {}, ht = m.home_fed_id ? tm(m.home_fed_id) : {};
    var aScore = m.away_score != null ? m.away_score.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014';
    var hScore = m.home_score != null ? m.home_score.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '\u2014';
    var aWin = m.complete && m.away_score > m.home_score, hWin = m.complete && m.home_score > m.away_score;
    var cls = m.complete ? 'complete' : '';
    var roundLabel = m.is_consolation ? (m.consolation_name || 'Consolation') : playoffRound;
    var hasLabel = !!roundLabel;
    h += '<div class="mu-card ' + cls + '" style="' + (hasLabel ? 'position:relative;padding-bottom:1.1rem' : '') + '">';
    if (hasLabel) h += '<div style="position:absolute;bottom:.25rem;left:50%;transform:translateX(-50%);font-size:.58rem;font-family:Palatino,serif;color:var(--accent);letter-spacing:.03em;white-space:nowrap;z-index:1">' + roundLabel + '</div>';
    h += '<div class="mu-team away">' + (m.away_fed_id ? '<img src="' + assetPath('logos/teams/' + m.away_fed_id + '.svg') + '" onerror="this.style.display=\'none\'">' : '');
    h += '<div class="mu-info"><div class="mu-name" style="color:' + (at.color || 'var(--text)') + '">' + (at.abbr || m.away_name) + '</div><div class="mu-owner">' + (at.name || '') + '</div></div></div>';
    h += '<div class="mu-score ' + (aWin ? 'winner' : m.complete ? 'loser' : '') + '">' + aScore + '</div>';
    h += '<div class="mu-vs">vs</div>';
    h += '<div class="mu-score ' + (hWin ? 'winner' : m.complete ? 'loser' : '') + '">' + hScore + '</div>';
    h += '<div class="mu-team home">' + (m.home_fed_id ? '<img src="' + assetPath('logos/teams/' + m.home_fed_id + '.svg') + '" onerror="this.style.display=\'none\'">' : '');
    h += '<div class="mu-info"><div class="mu-name" style="color:' + (ht.color || 'var(--text)') + '">' + (ht.abbr || m.home_name) + '</div><div class="mu-owner">' + (ht.name || '') + '</div></div></div>';
    h += '</div>';
  }
  return h + '</div>';
}

function renderWeekBar(lk, selectedWeek) {
  var nums = getPeriodNums(lk), meta = getSchMeta(lk), rivalry = meta.rivalry_week;
  var h = '<div class="sch-weeks" data-lk="' + lk + '">';
  for (var n of nums) {
    var p = meta.periods?.[String(n)] || {};
    var cls = 'sch-wk';
    if (n === selectedWeek) cls += ' active';
    if (p.current) cls += ' current';
    if (n === rivalry) cls += ' rivalry';
    var isPlayoff = p.is_playoff;
    var label = isPlayoff ? 'P' + (n - nums.filter(function (x) { var pp = meta.periods?.[String(x)]; return pp && !pp.is_playoff; }).length) : '' + n;
    var title = (p.name || ('Period ' + n)).replace(/"/g, '&quot;');
    h += '<button class="' + cls + '" data-wk="' + n + '" data-lk="' + lk + '" title="' + title + '">' + label + '</button>';
  }
  return h + '</div>';
}

// ===== EXPANDABLE ROWS =====
function bindRows() {
  document.querySelectorAll('tr.team-row').forEach(function (row) {
    row.addEventListener('click', function () {
      var tid = this.dataset.tid, ctx = this.dataset.ctx;
      if (!tid) return;
      var det = this.nextElementSibling;
      if (!det || !det.classList.contains('detail-row')) return;
      document.querySelectorAll('tr.detail-row.open').forEach(function (dr) { if (dr !== det) { dr.classList.remove('open'); dr.querySelector('td').innerHTML = ''; } });
      if (det.classList.contains('open')) { det.classList.remove('open'); det.querySelector('td').innerHTML = ''; }
      else {
        var td = det.querySelector('td');
        det.classList.add('open');
        if (!D.draft_picks_by_team) {
          td.innerHTML = '<div style="color:var(--text-dim);padding:.5rem;font-size:.8rem">Loading...</div>';
          loadLazy('draft_picks_by_team').then(function () {
            td.innerHTML = renderDetailContent(tid, ctx);
          });
        } else {
          td.innerHTML = renderDetailContent(tid, ctx);
        }
      }
    });
  });
}

// ===== SCHEDULE WEEK BUTTON BINDING =====
function bindSchedule(renderFn) {
  document.querySelectorAll('.sch-wk').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var lk = this.dataset.lk, wk = parseInt(this.dataset.wk);
      schWeek[lk] = wk;
      if (typeof renderFn === 'function') renderFn();
    });
  });
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', function () {
  initNav();
  loadData();
});
