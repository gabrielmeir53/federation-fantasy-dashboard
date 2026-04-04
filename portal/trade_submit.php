<?php
$page_title = 'Trades';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$all_users = db()->query('SELECT id, display_name, team_key FROM users ORDER BY display_name')->fetchAll();

// Build trade data from JSON for JS dropdowns
$trade_data = ['players' => [], 'picks' => [], 'faab' => []];
$user_team_map = [];
foreach ($all_users as $u) {
    $user_team_map[$u['id']] = $u['team_key'];
}

$league_display = ['fed_fl' => 'FedFL', 'fed_ba' => 'FedBA', 'fed_hl' => 'FedHL', 'fed_lb' => 'FedLB'];

// Check which leagues are past their trade deadline
$locked_leagues = [];
$deadline_info = get_trade_deadlines();
foreach ($league_display as $lk => $lname) {
    if (is_league_trade_locked($lk)) {
        $dl_date = $deadline_info[$lk]['deadline'] ?? '';
        $locked_leagues[$lk] = [
            'name' => $lname,
            'deadline' => $dl_date ? date('M j, Y', strtotime($dl_date)) : '',
        ];
    }
}
$combined_path = DATA_DIR . 'ysf_combined.json';
if (file_exists($combined_path)) {
    $combined = json_decode(file_get_contents($combined_path), true);

    // Players: index by ysf_id, grouped by league (mark locked leagues)
    foreach ($league_display as $lk => $lname) {
        $league = $combined['league_data'][$lk] ?? [];
        $teams_map = [];
        foreach ($league['teams'] ?? [] as $t) {
            $teams_map[$t['fantrax_id']] = $t['ysf_id'];
        }
        foreach ($league['rosters'] ?? [] as $fid => $roster) {
            $ysf_id = $roster['ysf_id'] ?? ($teams_map[$fid] ?? '');
            if (!$ysf_id) continue;
            foreach ($roster['players'] ?? [] as $p) {
                $trade_data['players'][$ysf_id][] = [
                    'name' => $p['name'],
                    'pos'  => $p['position'] ?? '',
                    'team' => $p['real_team'] ?? '',
                    'league' => $lname,
                    'league_key' => $lk,
                    'pid'  => $p['fantrax_player_id'] ?? '',
                ];
            }
        }
        // FAAB from standings
        foreach ($league['standings'] ?? [] as $s) {
            $ysf_id = $s['ysf_id'] ?? '';
            if ($ysf_id && isset($s['faab_remaining'])) {
                $trade_data['faab'][$ysf_id][$lname] = (int)$s['faab_remaining'];
            }
        }
    }

    // Draft picks by team (mark locked leagues)
    $picks_by_team = $combined['draft_picks_by_team'] ?? [];
    foreach ($picks_by_team as $ysf_id => $seasons) {
        foreach ($seasons as $season => $leagues) {
            foreach ($leagues as $lk => $picks) {
                $lname = $league_display[$lk] ?? strtoupper($lk);
                foreach ($picks as $pick) {
                    $label = "{$season} {$lname} Rd {$pick['round']}";
                    if ($pick['traded'] && ($pick['original_ysf_id'] ?? '') !== $ysf_id) {
                        $orig_name = team_name($pick['original_ysf_id'] ?? '');
                        $label .= " (from {$orig_name})";
                    }
                    $trade_data['picks'][$ysf_id][] = [
                        'label'  => $label,
                        'season' => $season,
                        'league' => $lk,
                        'round'  => $pick['round'],
                    ];
                }
            }
        }
    }

    $scraped_at = $combined['scraped_at'] ?? '';
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $side_count = (int)($_POST['side_count'] ?? 2);
    if ($side_count < 2 || $side_count > 4) $side_count = 2;
    $notes = trim($_POST['notes'] ?? '');

    // Parse sides
    $sides = [];
    for ($i = 1; $i <= $side_count; $i++) {
        $uid = (int)($_POST["side_{$i}_user"] ?? 0);
        $assets = [];
        if (!empty($_POST["side_{$i}_asset_name"]) && is_array($_POST["side_{$i}_asset_name"])) {
            foreach ($_POST["side_{$i}_asset_name"] as $j => $name) {
                $name = trim($name);
                $type = $_POST["side_{$i}_asset_type"][$j] ?? 'player';
                if (!in_array($type, ['player', 'pick', 'faab', 'other'])) $type = 'player';
                if ($name !== '') {
                    $assets[] = ['name' => $name, 'type' => $type];
                }
            }
        }
        if (!$uid) {
            $error = "Please select a team for Side {$i}.";
            break;
        }
        if (empty($assets)) {
            $error = "Side {$i} must acquire at least one asset.";
            break;
        }
        $sides[] = ['user_id' => $uid, 'assets' => $assets];
    }

    // Check for duplicate teams
    if (!$error) {
        $uids = array_column($sides, 'user_id');
        if (count($uids) !== count(array_unique($uids))) {
            $error = 'Each side must be a different team.';
        }
    }

    // Submitter must be one of the sides
    if (!$error) {
        $uids = array_column($sides, 'user_id');
        if (!in_array($user['id'], $uids)) {
            $error = 'You must be one of the teams in the trade.';
        }
    }

    // Server-side: reject assets from locked leagues
    if (!$error && $locked_leagues) {
        foreach ($sides as $side) {
            foreach ($side['assets'] as $asset) {
                foreach ($locked_leagues as $lk => $info) {
                    $ln = $info['name'];
                    if ($asset['type'] === 'player' && stripos($asset['name'], "[{$ln}]") !== false) {
                        $error = "Cannot trade {$ln} players — trade deadline passed {$info['deadline']}.";
                        break 3;
                    }
                    if ($asset['type'] === 'pick' && stripos($asset['name'], $ln) !== false) {
                        $error = "Cannot trade {$ln} picks — trade deadline passed {$info['deadline']}.";
                        break 3;
                    }
                }
            }
        }
    }

    if (!$error) {
        $pdo = db();
        $pdo->beginTransaction();
        try {
            $stmt = $pdo->prepare('INSERT INTO trades (submitted_by, notes) VALUES (:u, :n)');
            $stmt->execute([':u' => $user['id'], ':n' => $notes ?: null]);
            $trade_id = $pdo->lastInsertId();

            foreach ($sides as $side) {
                $is_sub = ($side['user_id'] == $user['id']) ? 1 : 0;
                $accepted = $is_sub ? 1 : 0;
                $accepted_at = $is_sub ? date('Y-m-d H:i:s') : null;

                $tk_stmt = $pdo->prepare('SELECT team_key FROM users WHERE id = :id');
                $tk_stmt->execute([':id' => $side['user_id']]);
                $team_key = $tk_stmt->fetchColumn();

                $stmt = $pdo->prepare('INSERT INTO trade_sides (trade_id, user_id, team_key, is_submitter, accepted, accepted_at) VALUES (:tid, :uid, :tk, :is, :a, :at)');
                $stmt->execute([
                    ':tid' => $trade_id,
                    ':uid' => $side['user_id'],
                    ':tk'  => $team_key,
                    ':is'  => $is_sub,
                    ':a'   => $accepted,
                    ':at'  => $accepted_at,
                ]);
                $side_id = $pdo->lastInsertId();

                foreach ($side['assets'] as $asset) {
                    $stmt = $pdo->prepare('INSERT INTO trade_assets (trade_side_id, asset_name, asset_type) VALUES (:sid, :n, :t)');
                    $stmt->execute([':sid' => $side_id, ':n' => $asset['name'], ':t' => $asset['type']]);
                }
            }

            $pdo->commit();

            // Email counter-parties
            require_once __DIR__ . '/includes/mail.php';
            $counter_parties = array_filter($sides, fn($s) => $s['user_id'] != $user['id']);
            foreach ($counter_parties as $side) {
                $cp = $pdo->prepare('SELECT email, display_name FROM users WHERE id = :id AND notify_email = 1');
                $cp->execute([':id' => $side['user_id']]);
                $cp_user = $cp->fetch();
                if ($cp_user && $cp_user['email']) {
                    portal_mail(
                        [$cp_user['email']],
                        'Federation Trade Proposal — Action Required',
                        '<h2>New Trade Proposal</h2>'
                        . '<p>' . e($user['display_name']) . ' has submitted a trade that includes your team.</p>'
                        . '<p>Please log in to the portal to review and accept or reject.</p>'
                        . '<p><a href="' . SITE_URL . '/trade.php?id=' . $trade_id . '">View Trade &rarr;</a></p>'
                    );
                }
            }

            flash('success', 'Trade submitted. Waiting for counter-party acceptance.');
            redirect('trade.php?id=' . $trade_id);
        } catch (Exception $ex) {
            $pdo->rollBack();
            $error = 'Failed to submit trade. Please try again.';
        }
    }
}

require __DIR__ . '/includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="trades.php">&larr; Trades</a></p>
<h1>Submit Trade</h1>
<p style="font-size:.9rem; color:var(--text-dim); margin-bottom:.3rem;">
  Specify what each side <strong>acquires</strong>. Counter-parties will be emailed to accept or reject.
</p>
<?php if (!empty($scraped_at)): ?>
<p style="font-size:.75rem; color:var(--text-muted); margin-bottom:1.2rem;">Rosters as of <?= e(date('M j, g:i A', strtotime($scraped_at))) ?></p>
<?php endif; ?>

<?php if ($locked_leagues): ?>
  <div class="alert alert-error" style="margin-bottom:1rem;">
    <strong>Trade deadline passed:</strong>
    <?php foreach ($locked_leagues as $lk => $info): ?>
      <?= e($info['name']) ?> (<?= e($info['deadline']) ?>)<?= $lk !== array_key_last($locked_leagues) ? ',' : '' ?>
    <?php endforeach; ?>.
    Players and picks from <?= count($locked_leagues) === 1 ? 'this league' : 'these leagues' ?> cannot be traded until <?= count($locked_leagues) === 1 ? 'its' : 'their' ?> championship concludes.
  </div>
<?php endif; ?>

<?php if ($error): ?>
  <div class="alert alert-error"><?= e($error) ?></div>
<?php endif; ?>

<form method="post" id="trade-form" class="card">
  <?= csrf_field() ?>

  <div class="form-group">
    <label>Number of teams</label>
    <div class="trade-team-count">
      <?php for ($n = 2; $n <= 4; $n++): ?>
        <label class="trade-count-option">
          <input type="radio" name="side_count" value="<?= $n ?>" <?= ($n == ($_POST['side_count'] ?? 2)) ? 'checked' : '' ?>>
          <?= $n ?>-team
        </label>
      <?php endfor; ?>
    </div>
  </div>

  <div id="sides-container">
    <?php
    $sc = (int)($_POST['side_count'] ?? 2);
    for ($i = 1; $i <= 4; $i++):
    ?>
    <fieldset class="trade-side" id="side-<?= $i ?>" <?= $i > $sc ? 'style="display:none"' : '' ?>>
      <legend>Side <?= $i ?> — acquires</legend>
      <div class="form-group">
        <label for="side_<?= $i ?>_user">Team</label>
        <select name="side_<?= $i ?>_user" id="side_<?= $i ?>_user" class="side-team-select" data-side="<?= $i ?>">
          <option value="">Select team...</option>
          <?php foreach ($all_users as $u): ?>
            <option value="<?= $u['id'] ?>" <?= (($i == 1 && empty($_POST)) && $u['id'] == $user['id']) || (($_POST["side_{$i}_user"] ?? '') == $u['id']) ? 'selected' : '' ?>>
              <?= e($u['display_name']) ?> (<?= e(team_name($u['team_key'])) ?>)
            </option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="asset-rows" id="assets-<?= $i ?>"></div>
      <button type="button" class="btn btn-sm btn-outline add-asset" data-side="<?= $i ?>">+ Add Asset</button>
    </fieldset>
    <?php endfor; ?>
  </div>

  <div class="form-group" style="margin-top:1rem;">
    <label for="notes">Notes (optional)</label>
    <textarea id="notes" name="notes" style="min-height:80px;" placeholder="Any context for the other parties or commissioners..."><?= e($_POST['notes'] ?? '') ?></textarea>
  </div>

  <button type="submit" class="btn btn-primary">Submit Trade</button>
</form>

<script>
var TRADE_DATA = <?= json_encode($trade_data, JSON_UNESCAPED_UNICODE) ?>;
var USER_TEAM_MAP = <?= json_encode($user_team_map) ?>;
var LOCKED_LEAGUES = <?= json_encode(array_map(fn($v) => $v, $locked_leagues), JSON_UNESCAPED_UNICODE) ?>;
// LOCKED_LEAGUES = { "fed_ba": { "name": "ySFBA", "deadline": "Feb 8, 2026" }, ... }

(function() {
  var form = document.getElementById('trade-form');

  // ── Helpers ──
  function getTeamKey(side) {
    var sel = document.getElementById('side_' + side + '_user');
    var uid = sel ? sel.value : '';
    return uid ? (USER_TEAM_MAP[uid] || '') : '';
  }

  // ── Build asset row ──
  function buildAssetRow(side) {
    var row = document.createElement('div');
    row.className = 'asset-row';

    // Type selector (visible)
    var typeSel = document.createElement('select');
    typeSel.className = 'asset-type-select';
    typeSel.innerHTML = '<option value="player">Player</option><option value="pick">Draft Pick</option><option value="faab">FAAB</option><option value="other">Other</option>';

    // Hidden inputs for form submission
    var hiddenType = document.createElement('input');
    hiddenType.type = 'hidden';
    hiddenType.name = 'side_' + side + '_asset_type[]';
    hiddenType.value = 'player';

    var hiddenName = document.createElement('input');
    hiddenName.type = 'hidden';
    hiddenName.name = 'side_' + side + '_asset_name[]';
    hiddenName.value = '';

    // Dynamic input area
    var wrap = document.createElement('div');
    wrap.className = 'asset-input-wrap';

    // Remove button
    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-sm btn-red remove-asset';
    removeBtn.title = 'Remove';
    removeBtn.textContent = '\u00d7';

    row.appendChild(typeSel);
    row.appendChild(hiddenType);
    row.appendChild(hiddenName);
    row.appendChild(wrap);
    row.appendChild(removeBtn);

    // Wire up type change
    typeSel.addEventListener('change', function() {
      hiddenType.value = this.value;
      hiddenName.value = '';
      updateAssetInput(row, side);
    });

    return row;
  }

  // ── Update asset input based on type ──
  function updateAssetInput(row, side) {
    var type = row.querySelector('.asset-type-select').value;
    var wrap = row.querySelector('.asset-input-wrap');
    var hidden = row.querySelector('input[name$="_asset_name[]"]');
    var teamKey = getTeamKey(side);
    wrap.innerHTML = '';

    if (type === 'player') {
      buildPlayerDropdown(wrap, hidden, teamKey);
    } else if (type === 'pick') {
      buildPickDropdown(wrap, hidden, teamKey);
    } else if (type === 'faab') {
      buildFaabInput(wrap, hidden, teamKey);
    } else {
      var inp = document.createElement('input');
      inp.type = 'text';
      inp.className = 'asset-text-input';
      inp.placeholder = 'Describe asset...';
      inp.addEventListener('input', function() { hidden.value = this.value; });
      wrap.appendChild(inp);
    }
  }

  // ── Searchable player dropdown ──
  function buildPlayerDropdown(wrap, hidden, teamKey) {
    var players = TRADE_DATA.players[teamKey] || [];
    var container = document.createElement('div');
    container.className = 'searchable-select';

    var search = document.createElement('input');
    search.type = 'text';
    search.className = 'ss-search';
    search.placeholder = players.length ? 'Search players...' : 'Select a team first';
    search.autocomplete = 'off';
    if (!players.length) search.disabled = true;

    var dropdown = document.createElement('div');
    dropdown.className = 'ss-dropdown';
    dropdown.style.display = 'none';

    // Group by league
    var byLeague = {};
    players.forEach(function(p) {
      if (!byLeague[p.league]) byLeague[p.league] = [];
      byLeague[p.league].push(p);
    });

    function renderOptions(filter) {
      dropdown.innerHTML = '';
      var hasResults = false;
      var q = (filter || '').toLowerCase();
      // Show unlocked leagues first, locked leagues at bottom
      var allLeagues = ['FedFL','FedBA','FedHL','FedLB'];
      var lkMap = {'FedFL':'fed_fl','FedBA':'fed_ba','FedHL':'fed_hl','FedLB':'fed_lb'};
      var unlocked = allLeagues.filter(function(l) { return !LOCKED_LEAGUES[lkMap[l]]; });
      var locked = allLeagues.filter(function(l) { return !!LOCKED_LEAGUES[lkMap[l]]; });
      unlocked.concat(locked).forEach(function(league) {
        var lp = byLeague[league] || [];
        var filtered = lp.filter(function(p) {
          if (!q) return true;
          return (p.name + ' ' + p.pos + ' ' + p.team).toLowerCase().indexOf(q) !== -1;
        });
        if (!filtered.length) return;
        hasResults = true;
        var lk = lkMap[league] || '';
        var locked = LOCKED_LEAGUES[lk] || null;
        var header = document.createElement('div');
        header.className = 'ss-group-header';
        if (locked) {
          header.innerHTML = league + ' <span class="ss-locked-tag">(Unavailable \u2014 Past Trade Deadline: ' + locked.deadline + ')</span>';
        } else {
          header.textContent = league;
        }
        dropdown.appendChild(header);
        filtered.forEach(function(p) {
          var opt = document.createElement('div');
          opt.className = 'ss-option' + (locked ? ' ss-option-locked' : '');
          var label = p.name;
          if (p.pos) label += ' \u2014 ' + p.pos;
          if (p.team) label += ', ' + p.team;
          opt.textContent = label;
          if (!locked) {
            var val = p.name + ' (' + p.pos + ', ' + p.team + ') [' + p.league + ']';
            opt.addEventListener('click', function() {
              search.value = label;
              hidden.value = val;
              dropdown.style.display = 'none';
            });
          }
          dropdown.appendChild(opt);
        });
      });
      if (!hasResults) {
        var no = document.createElement('div');
        no.className = 'ss-no-results';
        no.textContent = 'No players found';
        dropdown.appendChild(no);
      }
    }

    search.addEventListener('focus', function() {
      renderOptions(this.value);
      dropdown.style.display = '';
    });
    search.addEventListener('input', function() {
      renderOptions(this.value);
      dropdown.style.display = '';
    });

    container.appendChild(search);
    container.appendChild(dropdown);
    wrap.appendChild(container);
  }

  // ── Pick dropdown ──
  function buildPickDropdown(wrap, hidden, teamKey) {
    var picks = TRADE_DATA.picks[teamKey] || [];
    var sel = document.createElement('select');
    sel.className = 'asset-pick-select';

    if (!picks.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = teamKey ? 'No draft picks available' : 'Select a team first';
      opt.disabled = true;
      opt.selected = true;
      sel.appendChild(opt);
      sel.disabled = true;
    } else {
      var def = document.createElement('option');
      def.value = '';
      def.textContent = 'Select a pick...';
      sel.appendChild(def);
      picks.forEach(function(p) {
        var locked = LOCKED_LEAGUES[p.league] || null;
        var opt = document.createElement('option');
        if (locked) {
          opt.value = '';
          opt.textContent = p.label + ' (Unavailable \u2014 Past Deadline: ' + locked.deadline + ')';
          opt.disabled = true;
          opt.className = 'pick-option-locked';
        } else {
          opt.value = p.label;
          opt.textContent = p.label;
        }
        sel.appendChild(opt);
      });
    }

    sel.addEventListener('change', function() { hidden.value = this.value; });
    wrap.appendChild(sel);
  }

  // ── FAAB input ──
  function buildFaabInput(wrap, hidden, teamKey) {
    var faab = TRADE_DATA.faab[teamKey] || {};
    var inp = document.createElement('input');
    inp.type = 'number';
    inp.className = 'asset-faab-input';
    inp.min = '1';
    inp.placeholder = '$ amount';

    inp.addEventListener('input', function() {
      hidden.value = this.value ? ('$' + this.value + ' FAAB') : '';
    });

    wrap.appendChild(inp);

    // Show remaining balances
    var leagues = Object.keys(faab);
    if (leagues.length) {
      var hint = document.createElement('span');
      hint.className = 'faab-remaining';
      hint.textContent = 'Remaining: ' + leagues.map(function(l) { return '$' + faab[l] + ' (' + l + ')'; }).join(', ');
      wrap.appendChild(hint);
    }
  }

  // ── Team change → refresh all asset rows ──
  document.querySelectorAll('.side-team-select').forEach(function(sel) {
    sel.addEventListener('change', function() {
      var side = this.dataset.side;
      var container = document.getElementById('assets-' + side);
      // Clear and add one fresh row
      container.innerHTML = '';
      var row = buildAssetRow(side);
      container.appendChild(row);
      updateAssetInput(row, side);
    });
  });

  // ── Add asset row ──
  form.addEventListener('click', function(e) {
    if (e.target.classList.contains('add-asset')) {
      var side = e.target.dataset.side;
      var container = document.getElementById('assets-' + side);
      var row = buildAssetRow(side);
      container.appendChild(row);
      updateAssetInput(row, side);
    }
    if (e.target.classList.contains('remove-asset')) {
      var row = e.target.closest('.asset-row');
      var container = row.parentNode;
      if (container.querySelectorAll('.asset-row').length > 1) {
        row.remove();
      }
    }
  });

  // ── Close dropdowns on outside click ──
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.searchable-select')) {
      document.querySelectorAll('.ss-dropdown').forEach(function(dd) {
        dd.style.display = 'none';
      });
    }
  });

  // ── Side count toggle ──
  document.querySelectorAll('input[name="side_count"]').forEach(function(r) {
    r.addEventListener('change', function() {
      var count = parseInt(this.value);
      for (var i = 1; i <= 4; i++) {
        document.getElementById('side-' + i).style.display = i <= count ? '' : 'none';
      }
    });
  });

  // ── Init: add one asset row per visible side ──
  var sideCount = parseInt(document.querySelector('input[name="side_count"]:checked').value) || 2;
  for (var i = 1; i <= sideCount; i++) {
    var container = document.getElementById('assets-' + i);
    if (container && !container.children.length) {
      var row = buildAssetRow(i);
      container.appendChild(row);
      updateAssetInput(row, i);
    }
  }
})();
</script>

<?php require __DIR__ . '/includes/footer.php'; ?>
