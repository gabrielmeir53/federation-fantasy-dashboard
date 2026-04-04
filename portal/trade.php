<?php
$page_title = 'Trades';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$id = (int)($_GET['id'] ?? 0);
if (!$id) { redirect('trades.php'); }

$pdo = db();

$trade = $pdo->prepare('SELECT t.*, u.display_name AS submitter_name FROM trades t JOIN users u ON t.submitted_by = u.id WHERE t.id = :id');
$trade->execute([':id' => $id]);
$trade = $trade->fetch();
if (!$trade) { http_response_code(404); die('<h1>Trade not found</h1>'); }

// Fetch sides with assets
$sides_stmt = $pdo->prepare('
    SELECT ts.*, u.display_name, u.email
    FROM trade_sides ts
    JOIN users u ON ts.user_id = u.id
    WHERE ts.trade_id = :tid
    ORDER BY ts.is_submitter DESC, ts.id ASC
');
$sides_stmt->execute([':tid' => $id]);
$sides = $sides_stmt->fetchAll();

foreach ($sides as &$side) {
    $a_stmt = $pdo->prepare('SELECT * FROM trade_assets WHERE trade_side_id = :sid ORDER BY id');
    $a_stmt->execute([':sid' => $side['id']]);
    $side['assets'] = $a_stmt->fetchAll();
}
unset($side);

$is_party = false;
$my_side = null;
foreach ($sides as $s) {
    if ((int)$s['user_id'] === (int)$user['id']) {
        $is_party = true;
        $my_side = $s;
        break;
    }
}

$all_accepted = true;
foreach ($sides as $s) {
    if (!$s['accepted']) { $all_accepted = false; break; }
}

// 48-hour review period
$review_ends = null;
if ($trade['accepted_at']) {
    $review_ends = date('Y-m-d H:i:s', strtotime($trade['accepted_at']) + 48 * 3600);
}

require __DIR__ . '/includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="trades.php">&larr; Trades</a></p>

<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:.5rem;">
  <h1 style="margin-bottom:0;">Trade #<?= $trade['id'] ?></h1>
  <?= trade_status_badge($trade['status']) ?>
</div>
<div class="card-meta" style="margin-bottom:1.5rem;">
  Submitted by <?= e($trade['submitter_name']) ?> &middot; <?= format_datetime($trade['created_at']) ?>
  <?php if ($review_ends && in_array($trade['status'], ['pending_review', 'approved'])): ?>
    &middot; Review period <?= time() < strtotime($review_ends) ? 'ends' : 'ended' ?> <?= format_datetime($review_ends) ?>
  <?php endif; ?>
</div>

<?php if ($trade['notes']): ?>
  <div class="card" style="margin-bottom:1.5rem;">
    <div style="font-size:.78rem; font-family:var(--ui); color:var(--text-muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:.3rem;">Notes</div>
    <div style="font-size:.95rem;"><?= nl2br(e($trade['notes'])) ?></div>
  </div>
<?php endif; ?>

<!-- Trade sides -->
<div class="trade-grid">
<?php foreach ($sides as $i => $side): ?>
  <div class="card trade-side-card">
    <div class="trade-side-header">
      <strong><?= e($side['display_name']) ?></strong>
      <span style="color:var(--text-muted); font-size:.85rem;">(<?= e(team_name($side['team_key'])) ?>)</span>
      <?php if ($side['accepted']): ?>
        <span class="badge badge-green" style="margin-left:.5rem;">Accepted</span>
      <?php elseif ($trade['status'] === 'pending_acceptance'): ?>
        <span class="badge badge-gray" style="margin-left:.5rem;">Pending</span>
      <?php endif; ?>
    </div>
    <div style="font-size:.78rem; font-family:var(--ui); color:var(--text-muted); text-transform:uppercase; letter-spacing:.06em; margin:.6rem 0 .3rem;">Acquires</div>
    <ul class="trade-asset-list">
      <?php foreach ($side['assets'] as $asset): ?>
        <li>
          <?= e($asset['asset_name']) ?>
          <span class="badge <?= asset_type_badge_class($asset['asset_type']) ?>"><?= e($asset['asset_type']) ?></span>
        </li>
      <?php endforeach; ?>
    </ul>
  </div>
<?php endforeach; ?>
</div>

<!-- Actions -->
<?php if ($trade['status'] === 'pending_acceptance' && $is_party && $my_side && !$my_side['accepted']): ?>
  <div class="card" style="margin-top:1rem;">
    <h2>Your Response</h2>
    <p style="font-size:.9rem; color:var(--text-dim); margin-bottom:.8rem;">Review the trade above, then accept or reject.</p>
    <div class="btn-row">
      <form method="post" action="trade_respond.php" style="display:inline;">
        <?= csrf_field() ?>
        <input type="hidden" name="trade_id" value="<?= $trade['id'] ?>">
        <input type="hidden" name="action" value="accept">
        <button type="submit" class="btn btn-green">Accept Trade</button>
      </form>
      <form method="post" action="trade_respond.php" style="display:inline;">
        <?= csrf_field() ?>
        <input type="hidden" name="trade_id" value="<?= $trade['id'] ?>">
        <input type="hidden" name="action" value="reject">
        <button type="submit" class="btn btn-red">Reject Trade</button>
      </form>
    </div>
  </div>
<?php endif; ?>

<?php if (is_commissioner() && $trade['status'] === 'pending_review'): ?>
  <div class="card" style="margin-top:1rem;">
    <h2>Commissioner Review</h2>
    <?php if ($review_ends): ?>
      <p style="font-size:.85rem; color:var(--text-dim); margin-bottom:.5rem;">
        48-hour review period <?= time() < strtotime($review_ends) ? 'ends' : 'ended' ?> <strong><?= format_datetime($review_ends) ?></strong>.
      </p>
    <?php endif; ?>
    <div class="btn-row">
      <form method="post" action="trade_manage.php" style="display:inline;">
        <?= csrf_field() ?>
        <input type="hidden" name="trade_id" value="<?= $trade['id'] ?>">
        <input type="hidden" name="action" value="approve">
        <button type="submit" class="btn btn-green">Approve</button>
      </form>
      <form method="post" action="trade_manage.php" class="trade-reject-form">
        <?= csrf_field() ?>
        <input type="hidden" name="trade_id" value="<?= $trade['id'] ?>">
        <input type="hidden" name="action" value="reject">
        <input type="text" name="reject_reason" placeholder="Reason for rejection..." class="trade-reject-input">
        <button type="submit" class="btn btn-red btn-sm">Reject</button>
      </form>
    </div>
  </div>
<?php endif; ?>

<?php if (is_commissioner() && $trade['status'] === 'approved'): ?>
  <div class="card" style="margin-top:1rem;">
    <h2>Process on Fantrax</h2>
    <p style="font-size:.9rem; color:var(--text-dim); margin-bottom:.8rem;">Once you've entered this trade on Fantrax, mark it as processed.</p>
    <form method="post" action="trade_manage.php">
      <?= csrf_field() ?>
      <input type="hidden" name="trade_id" value="<?= $trade['id'] ?>">
      <input type="hidden" name="action" value="process">
      <button type="submit" class="btn btn-primary">Mark as Processed</button>
    </form>
  </div>
<?php endif; ?>

<?php if ($trade['status'] === 'rejected' && $trade['reject_reason']): ?>
  <div class="alert alert-error" style="margin-top:1rem;">
    <strong>Rejection reason:</strong> <?= e($trade['reject_reason']) ?>
  </div>
<?php endif; ?>

<?php if ($trade['reviewed_by']): ?>
  <?php
  $reviewer = $pdo->prepare('SELECT display_name FROM users WHERE id = :id');
  $reviewer->execute([':id' => $trade['reviewed_by']]);
  $reviewer_name = $reviewer->fetchColumn();
  ?>
  <p style="font-size:.85rem; color:var(--text-muted); margin-top:1rem;">
    <?= in_array($trade['status'], ['approved', 'processed']) ? 'Approved' : 'Reviewed' ?> by <?= e($reviewer_name) ?>
    <?php if ($trade['reviewed_at']): ?> on <?= format_datetime($trade['reviewed_at']) ?><?php endif; ?>
  </p>
<?php endif; ?>

<?php if ($trade['processed_by']): ?>
  <?php
  $processor = $pdo->prepare('SELECT display_name FROM users WHERE id = :id');
  $processor->execute([':id' => $trade['processed_by']]);
  $processor_name = $processor->fetchColumn();
  ?>
  <p style="font-size:.85rem; color:var(--text-muted);">
    Processed by <?= e($processor_name) ?>
    <?php if ($trade['processed_at']): ?> on <?= format_datetime($trade['processed_at']) ?><?php endif; ?>
  </p>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
