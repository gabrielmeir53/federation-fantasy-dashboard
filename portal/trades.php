<?php
$page_title = 'Trades';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$tab = $_GET['tab'] ?? 'mine';
$pdo = db();

// My trades (where I'm a party)
$my_trades = $pdo->prepare('
    SELECT t.*, u.display_name AS submitter_name,
           GROUP_CONCAT(DISTINCT ts2.team_key ORDER BY ts2.is_submitter DESC SEPARATOR ",") AS team_keys
    FROM trades t
    JOIN users u ON t.submitted_by = u.id
    JOIN trade_sides ts ON ts.trade_id = t.id AND ts.user_id = :uid
    JOIN trade_sides ts2 ON ts2.trade_id = t.id
    GROUP BY t.id
    ORDER BY t.created_at DESC
');
$my_trades->execute([':uid' => $user['id']]);
$my_trades = $my_trades->fetchAll();

// Awaiting review (commissioners only)
$review_trades = [];
if (is_commissioner()) {
    $review_trades = $pdo->query("
        SELECT t.*, u.display_name AS submitter_name,
               GROUP_CONCAT(DISTINCT ts.team_key ORDER BY ts.is_submitter DESC SEPARATOR ',') AS team_keys
        FROM trades t
        JOIN users u ON t.submitted_by = u.id
        JOIN trade_sides ts ON ts.trade_id = t.id
        WHERE t.status = 'pending_review'
        GROUP BY t.id
        ORDER BY t.accepted_at ASC
    ")->fetchAll();
}

// History (all completed/rejected)
$history = $pdo->query("
    SELECT t.*, u.display_name AS submitter_name,
           GROUP_CONCAT(DISTINCT ts.team_key ORDER BY ts.is_submitter DESC SEPARATOR ',') AS team_keys
    FROM trades t
    JOIN users u ON t.submitted_by = u.id
    JOIN trade_sides ts ON ts.trade_id = t.id
    WHERE t.status IN ('approved','processed','rejected','cancelled')
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT 50
")->fetchAll();

require __DIR__ . '/includes/header.php';
?>

<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem;">
  <h1 style="margin-bottom:0;">Trades</h1>
  <a href="trade_submit.php" class="btn btn-primary btn-sm">+ New Trade</a>
</div>

<div class="tabs">
  <a class="tab <?= $tab === 'mine' ? 'active' : '' ?>" href="?tab=mine">
    My Trades <span class="tab-count"><?= count($my_trades) ?></span>
  </a>
  <?php if (is_commissioner()): ?>
  <a class="tab <?= $tab === 'review' ? 'active' : '' ?>" href="?tab=review">
    Awaiting Review <span class="tab-count"><?= count($review_trades) ?></span>
  </a>
  <?php endif; ?>
  <a class="tab <?= $tab === 'history' ? 'active' : '' ?>" href="?tab=history">
    History <span class="tab-count"><?= count($history) ?></span>
  </a>
</div>

<?php
function render_trade_list(array $trades, string $empty_msg): void {
    if (empty($trades)) {
        echo '<p style="color:var(--text-muted);">' . $empty_msg . '</p>';
        return;
    }
    foreach ($trades as $t) {
        $teams = array_map('team_name', explode(',', $t['team_keys']));
        $team_str = implode(' &harr; ', array_map('e', $teams));
        echo '<a href="trade.php?id=' . $t['id'] . '" class="card card-link">';
        echo '<div class="card-title">' . $team_str . ' ' . trade_status_badge($t['status']) . '</div>';
        echo '<div class="card-meta">Submitted by ' . e($t['submitter_name']) . ' &middot; ' . format_date($t['created_at']) . '</div>';
        if ($t['notes']) {
            echo '<div class="card-body">' . e(mb_strimwidth($t['notes'], 0, 150, '...')) . '</div>';
        }
        echo '</a>';
    }
}

if ($tab === 'mine'):
    render_trade_list($my_trades, 'No trades yet. Submit one to get started.');
elseif ($tab === 'review' && is_commissioner()):
    render_trade_list($review_trades, 'No trades awaiting review.');
else:
    render_trade_list($history, 'No completed trades yet.');
endif;
?>

<?php require __DIR__ . '/includes/footer.php'; ?>
