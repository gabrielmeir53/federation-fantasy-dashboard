<?php
$page_title = 'Proposals';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$tab = $_GET['tab'] ?? 'open';
if (!in_array($tab, ['open', 'submitted', 'closed'])) $tab = 'open';

$counts = [];
foreach (['open', 'submitted', 'closed'] as $t) {
    if ($t === 'closed') {
        $counts[$t] = db()->query("SELECT COUNT(*) FROM proposals WHERE status IN ('passed','failed','rejected')")->fetchColumn();
    } else {
        $stmt = db()->prepare('SELECT COUNT(*) FROM proposals WHERE status = :s');
        $stmt->execute([':s' => $t]);
        $counts[$t] = $stmt->fetchColumn();
    }
}

if ($tab === 'closed') {
    $proposals = db()->query("SELECT p.*, u.display_name FROM proposals p JOIN users u ON p.submitted_by = u.id WHERE p.status IN ('passed','failed','rejected') ORDER BY p.closed_at DESC")->fetchAll();
} else {
    $stmt = db()->prepare('SELECT p.*, u.display_name FROM proposals p JOIN users u ON p.submitted_by = u.id WHERE p.status = :s ORDER BY p.created_at DESC');
    $stmt->execute([':s' => $tab]);
    $proposals = $stmt->fetchAll();
}

require __DIR__ . '/includes/header.php';
?>

<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem;">
  <h1 style="margin-bottom:0;">Proposals</h1>
  <a href="proposal_submit.php" class="btn btn-primary btn-sm">Submit Proposal</a>
</div>

<div class="tabs">
  <a href="?tab=open" class="tab <?= $tab === 'open' ? 'active' : '' ?>">Open <span class="tab-count"><?= $counts['open'] ?></span></a>
  <?php if (is_commissioner()): ?>
  <a href="?tab=submitted" class="tab <?= $tab === 'submitted' ? 'active' : '' ?>">Pending Review <span class="tab-count"><?= $counts['submitted'] ?></span></a>
  <?php endif; ?>
  <a href="?tab=closed" class="tab <?= $tab === 'closed' ? 'active' : '' ?>">Closed <span class="tab-count"><?= $counts['closed'] ?></span></a>
</div>

<?php if ($proposals): ?>
  <?php foreach ($proposals as $p): ?>
    <a href="proposal.php?id=<?= $p['id'] ?>" class="card card-link">
      <div class="card-title"><?= e($p['title']) ?> <?= type_badge($p['proposal_type']) ?> <?= status_badge($p['status']) ?></div>
      <div class="card-meta">
        Submitted by <?= e($p['display_name']) ?> &middot; <?= format_date($p['created_at']) ?>
        <?php if ($p['emergency']): ?> &middot; <span class="badge badge-orange">Emergency</span><?php endif; ?>
      </div>
    </a>
  <?php endforeach; ?>
<?php else: ?>
  <p style="color:var(--text-muted);">No proposals in this category.</p>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
