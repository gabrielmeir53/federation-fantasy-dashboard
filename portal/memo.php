<?php
$page_title = 'Memos';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$id = (int)($_GET['id'] ?? 0);
$stmt = db()->prepare('SELECT m.*, u.display_name FROM memos m JOIN users u ON m.author_id = u.id WHERE m.id = :id');
$stmt->execute([':id' => $id]);
$memo = $stmt->fetch();
if (!$memo) { http_response_code(404); die('Memo not found.'); }

require __DIR__ . '/includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="memos.php">&larr; All Memos</a></p>

<div class="card">
  <h1 style="margin-bottom:.3rem;"><?= e($memo['title']) ?></h1>
  <div class="card-meta" style="margin-bottom:1rem;">
    <?= e($memo['display_name']) ?> &middot; <?= format_datetime($memo['created_at']) ?>
    <?php if ($memo['updated_at']): ?> &middot; Edited <?= format_datetime($memo['updated_at']) ?><?php endif; ?>
  </div>

  <?php if ($memo['body']): ?>
  <div class="memo-body"><?= $memo['body'] ?></div>
  <?php endif; ?>

  <?php if ($memo['file_path']): ?>
  <div style="margin-top:1rem; padding-top:1rem; border-top:1px solid var(--border);">
    <strong style="font-size:.85rem; color:var(--text-dim);">Attachment:</strong>
    <a href="<?= e($memo['file_path']) ?>" target="_blank" class="btn btn-outline btn-sm" style="margin-left:.5rem;"><?= e($memo['file_name']) ?></a>
  </div>
  <?php endif; ?>

  <?php if (is_commissioner()): ?>
  <div class="btn-row" style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid var(--border);">
    <a href="memo_edit.php?id=<?= $memo['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
    <form method="post" action="memo_delete.php" style="display:inline;" onsubmit="return confirm('Delete this memo?');">
      <?= csrf_field() ?>
      <input type="hidden" name="id" value="<?= $memo['id'] ?>">
      <button type="submit" class="btn btn-red btn-sm">Delete</button>
    </form>
  </div>
  <?php endif; ?>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
