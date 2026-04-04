<?php
$page_title = 'Dashboard';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$greeting_name = $user['preferred_name'] ?: explode(' ', $user['display_name'])[0];
$hour = (int)date('G');
if ($hour < 12) $greeting = 'Good morning';
elseif ($hour < 17) $greeting = 'Good afternoon';
else $greeting = 'Good evening';

$recent_memos = db()->query('SELECT m.*, u.display_name FROM memos m JOIN users u ON m.author_id = u.id ORDER BY m.created_at DESC LIMIT 5')->fetchAll();
$open_proposals = db()->query("SELECT p.*, u.display_name FROM proposals p JOIN users u ON p.submitted_by = u.id WHERE p.status = 'open' ORDER BY p.opened_at DESC")->fetchAll();
$pending_count = 0;
if (is_commissioner()) {
    $pending_count = db()->query("SELECT COUNT(*) FROM proposals WHERE status = 'submitted'")->fetchColumn();
}

// Trades needing my action
$my_pending_trades = db()->prepare("
    SELECT t.id, GROUP_CONCAT(DISTINCT ts2.team_key ORDER BY ts2.is_submitter DESC SEPARATOR ',') AS team_keys
    FROM trades t
    JOIN trade_sides ts ON ts.trade_id = t.id AND ts.user_id = :uid AND ts.accepted = 0
    JOIN trade_sides ts2 ON ts2.trade_id = t.id
    WHERE t.status = 'pending_acceptance'
    GROUP BY t.id
    ORDER BY t.created_at DESC
");
$my_pending_trades->execute([':uid' => $user['id']]);
$my_pending_trades = $my_pending_trades->fetchAll();

$trade_review_count = 0;
if (is_commissioner()) {
    $trade_review_count = db()->query("SELECT COUNT(*) FROM trades WHERE status = 'pending_review'")->fetchColumn();
}

// Load scoreboard data from league JSONs
$league_labels = ['fed_fl' => 'FedFL', 'fed_ba' => 'FedBA', 'fed_hl' => 'FedHL', 'fed_lb' => 'FedLB'];
$scoreboards = [];
$scraped_at = '';
$my_team_key = $user['team_key'];

if (defined('DATA_DIR')) {
    $core_path = DATA_DIR . 'core.json';
    if (file_exists($core_path)) {
        $core = json_decode(file_get_contents($core_path), true);
        $scraped_at = $core['scraped_at'] ?? '';
    }

    foreach ($league_labels as $lk => $lname) {
        $path = DATA_DIR . "league_{$lk}.json";
        if (!file_exists($path)) continue;
        $data = json_decode(file_get_contents($path), true);
        $periods = $data['schedule_meta']['periods'] ?? [];
        $matchups = $data['matchups'] ?? [];

        // Find current period
        $current_period = null;
        foreach ($periods as $pk => $pv) {
            if (!empty($pv['current'])) { $current_period = (int)$pk; break; }
        }
        if (!$current_period) continue;

        $period_info = $periods[(string)$current_period] ?? [];
        $period_name = $period_info['name'] ?? "Week {$current_period}";

        // Build team info map
        $team_info = [];
        foreach ($data['teams'] ?? [] as $t) {
            $team_info[$t['ysf_id'] ?? ''] = [
                'short' => $t['short'] ?? '',
                'name'  => $t['fantrax_name'] ?? '',
                'ysf_id' => $t['ysf_id'] ?? '',
            ];
        }

        // Filter matchups for current period
        $current_matchups = [];
        foreach ($matchups as $mu) {
            if ((int)($mu['period'] ?? 0) !== $current_period) continue;
            $away_id = $mu['away_ysf_id'] ?? '';
            $home_id = $mu['home_ysf_id'] ?? '';
            $current_matchups[] = [
                'away_short' => $team_info[$away_id]['short'] ?? ($mu['away_name'] ?? ''),
                'away_name'  => $mu['away_name'] ?? '',
                'away_id'    => $away_id,
                'away_score' => $mu['away_score'] ?? null,
                'home_short' => $team_info[$home_id]['short'] ?? ($mu['home_name'] ?? ''),
                'home_name'  => $mu['home_name'] ?? '',
                'home_id'    => $home_id,
                'home_score' => $mu['home_score'] ?? null,
                'complete'   => !empty($mu['complete']),
                'is_mine'    => ($away_id === $my_team_key || $home_id === $my_team_key),
            ];
        }

        if ($current_matchups) {
            $scoreboards[] = [
                'league'   => $lname,
                'period'   => $period_name,
                'matchups' => $current_matchups,
            ];
        }
    }
}

require __DIR__ . '/includes/header.php';
?>

<h1><?= e($greeting) ?>, <?= e($greeting_name) ?>.</h1>
<?php
$tz = $user['timezone'];
$prev_tz = $user['last_login_tz_prev'];
?>
<?php if ($user['last_login_prev']): ?>
<?php
  $original = format_datetime_tz($user['last_login_prev'], $prev_tz);
  $same_tz = ($prev_tz === $tz);
  $converted = '';
  if (!$same_tz) {
      $converted = format_datetime_tz($user['last_login_prev'], $tz);
  }
?>
<p style="font-style:italic; font-size:.85rem; color:var(--text-muted); margin-bottom:1.5rem;">
  Last login: <?= e($original) ?><?php if (!$same_tz): ?> (<?= e($converted) ?>)<?php endif; ?>
</p>
<?php else: ?>
<p style="font-style:italic; font-size:.85rem; color:var(--text-muted); margin-bottom:1.5rem;">Welcome to the Federation Portal.</p>
<?php endif; ?>

<?php if ($open_proposals): ?>
<h2>Open Votes</h2>
<?php foreach ($open_proposals as $p): ?>
  <?php
    $my_vote = db()->prepare('SELECT vote FROM votes WHERE proposal_id = :pid AND user_id = :uid');
    $my_vote->execute([':pid' => $p['id'], ':uid' => $user['id']]);
    $voted = $my_vote->fetchColumn();
    $vote_count = db()->prepare('SELECT COUNT(*) FROM votes WHERE proposal_id = :pid');
    $vote_count->execute([':pid' => $p['id']]);
    $count = $vote_count->fetchColumn();
  ?>
  <a href="proposal.php?id=<?= $p['id'] ?>" class="card card-link">
    <div class="card-title"><?= e($p['title']) ?> <?= type_badge($p['proposal_type']) ?></div>
    <div class="card-meta">by <?= e($p['display_name']) ?> &middot; <?= format_date($p['opened_at']) ?> &middot; <?= $count ?>/12 votes cast<?php if ($voted): ?> &middot; <strong>You voted</strong><?php endif; ?></div>
  </a>
<?php endforeach; ?>
<?php endif; ?>

<?php if ($my_pending_trades): ?>
<h2 style="margin-top:2rem;">Trades Awaiting Your Response</h2>
<?php foreach ($my_pending_trades as $pt): ?>
  <?php $teams = array_map('team_name', explode(',', $pt['team_keys'])); ?>
  <a href="trade.php?id=<?= $pt['id'] ?>" class="card card-link">
    <div class="card-title"><?= implode(' &harr; ', array_map('e', $teams)) ?> <?= trade_status_badge('pending_acceptance') ?></div>
    <div class="card-meta">Action required &mdash; accept or reject</div>
  </a>
<?php endforeach; ?>
<?php endif; ?>

<?php if ($pending_count > 0): ?>
<div class="alert alert-success" style="margin-top:1rem;">
  <strong><?= $pending_count ?></strong> proposal<?= $pending_count > 1 ? 's' : '' ?> awaiting commissioner review.
  <a href="proposals.php?tab=submitted">Review &rarr;</a>
</div>
<?php endif; ?>

<?php if ($trade_review_count > 0): ?>
<div class="alert alert-success" style="margin-top:.5rem;">
  <strong><?= $trade_review_count ?></strong> trade<?= $trade_review_count > 1 ? 's' : '' ?> awaiting commissioner review.
  <a href="trades.php?tab=review">Review &rarr;</a>
</div>
<?php endif; ?>

<?php if ($scoreboards): ?>
<div style="display:flex; align-items:baseline; justify-content:space-between; margin-top:2rem;">
  <div style="display:flex; align-items:baseline; gap:.6rem;">
    <h2 style="margin-bottom:0;">Scores</h2>
    <?php if ($scraped_at): ?>
      <span style="font-family:var(--ui); font-size:.65rem; color:var(--text-muted);">Updated <?= format_datetime_tz($scraped_at, $tz) ?></span>
    <?php endif; ?>
  </div>
  <div class="tabs" style="border-bottom:none; margin-bottom:0;">
    <a class="tab active" href="#" id="sb-tab-all">All Games</a>
    <a class="tab" href="#" id="sb-tab-mine">My Games</a>
  </div>
</div>

<?php foreach ($scoreboards as $sb): ?>
<div style="margin-top:.8rem;" class="sb-league">
  <div style="font-family:var(--ui); font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em; color:var(--text-muted); margin-bottom:.4rem;">
    <?= e($sb['league']) ?> &mdash; <?= e($sb['period']) ?>
  </div>
  <div class="mu-grid">
    <?php foreach ($sb['matchups'] as $mu): ?>
      <?php
        $a_score = $mu['away_score'] !== null ? number_format($mu['away_score'], 1) : '—';
        $h_score = $mu['home_score'] !== null ? number_format($mu['home_score'], 1) : '—';
        $a_win = $mu['complete'] && $mu['away_score'] > $mu['home_score'];
        $h_win = $mu['complete'] && $mu['home_score'] > $mu['away_score'];
        $complete_cls = $mu['complete'] ? ' complete' : '';
      ?>
      <div class="mu-card<?= $complete_cls ?>" data-mine="<?= $mu['is_mine'] ? '1' : '0' ?>">
        <div class="mu-team away">
          <img src="<?= MAIN_SITE_URL ?>/logos/teams/<?= e($mu['away_id']) ?>.svg" onerror="this.style.display='none'">
          <div class="mu-info">
            <div class="mu-name"><?= e($mu['away_short']) ?></div>
            <div class="mu-owner"><?= e($mu['away_name']) ?></div>
          </div>
        </div>
        <div class="mu-score<?= $a_win ? ' winner' : ($mu['complete'] ? ' loser' : '') ?>"><?= $a_score ?></div>
        <div class="mu-vs">vs</div>
        <div class="mu-score<?= $h_win ? ' winner' : ($mu['complete'] ? ' loser' : '') ?>"><?= $h_score ?></div>
        <div class="mu-team home">
          <img src="<?= MAIN_SITE_URL ?>/logos/teams/<?= e($mu['home_id']) ?>.svg" onerror="this.style.display='none'">
          <div class="mu-info">
            <div class="mu-name"><?= e($mu['home_short']) ?></div>
            <div class="mu-owner"><?= e($mu['home_name']) ?></div>
          </div>
        </div>
      </div>
    <?php endforeach; ?>
  </div>
</div>
<?php endforeach; ?>

<script>
(function() {
  var tabAll = document.getElementById('sb-tab-all');
  var tabMine = document.getElementById('sb-tab-mine');
  function showAll() {
    tabAll.classList.add('active'); tabMine.classList.remove('active');
    document.querySelectorAll('.mu-card').forEach(function(c) { c.style.display = ''; });
    document.querySelectorAll('.sb-league').forEach(function(l) { l.style.display = ''; });
  }
  function showMine() {
    tabMine.classList.add('active'); tabAll.classList.remove('active');
    document.querySelectorAll('.mu-card').forEach(function(c) {
      c.style.display = c.dataset.mine === '1' ? '' : 'none';
    });
    // Hide league sections with no visible cards
    document.querySelectorAll('.sb-league').forEach(function(l) {
      var visible = l.querySelectorAll('.mu-card[data-mine="1"]').length;
      l.style.display = visible ? '' : 'none';
    });
  }
  tabAll.addEventListener('click', function(e) { e.preventDefault(); showAll(); });
  tabMine.addEventListener('click', function(e) { e.preventDefault(); showMine(); });
})();
</script>
<?php endif; ?>

<h2 style="margin-top:2rem;">Recent Memos</h2>
<?php if ($recent_memos): ?>
  <?php foreach ($recent_memos as $m): ?>
    <a href="memo.php?id=<?= $m['id'] ?>" class="card card-link">
      <div class="card-title"><?= e($m['title']) ?></div>
      <div class="card-meta"><?= e($m['display_name']) ?> &middot; <?= format_date($m['created_at']) ?></div>
      <div class="card-body"><?= e(mb_strimwidth($m['body'], 0, 200, '...')) ?></div>
    </a>
  <?php endforeach; ?>
  <a href="memos.php" style="font-size:.9rem;">View all memos &rarr;</a>
<?php else: ?>
  <p style="color:var(--text-muted);">No memos yet.</p>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
