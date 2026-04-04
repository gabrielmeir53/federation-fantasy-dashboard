<?php
$page_title = 'Memos';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$memos = db()->query('SELECT m.*, u.display_name FROM memos m JOIN users u ON m.author_id = u.id ORDER BY m.created_at DESC')->fetchAll();

require __DIR__ . '/includes/header.php';
?>

<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem;">
  <h1 style="margin-bottom:0;">Memos</h1>
  <?php if (is_commissioner()): ?>
    <a href="memo_edit.php" class="btn btn-primary btn-sm">New Memo</a>
  <?php endif; ?>
</div>

<?php if ($memos): ?>
  <?php foreach ($memos as $m): ?>
    <a href="memo.php?id=<?= $m['id'] ?>" class="card card-link">
      <div class="card-title"><?= e($m['title']) ?></div>
      <div class="card-meta"><?= e($m['display_name']) ?> &middot; <?= format_date($m['created_at']) ?><?php if ($m['updated_at']): ?> (edited)<?php endif; ?></div>
      <div class="card-body"><?= e(mb_strimwidth($m['body'], 0, 250, '...')) ?></div>
    </a>
  <?php endforeach; ?>
<?php else: ?>
  <p style="color:var(--text-muted);">No memos have been posted yet.</p>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
