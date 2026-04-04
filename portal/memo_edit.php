<?php
$page_title = 'Memos';
require_once __DIR__ . '/includes/auth.php';
$user = require_commissioner();

$id = (int)($_GET['id'] ?? 0);
$memo = null;
if ($id) {
    $stmt = db()->prepare('SELECT * FROM memos WHERE id = :id');
    $stmt->execute([':id' => $id]);
    $memo = $stmt->fetch();
    if (!$memo) { http_response_code(404); die('Memo not found.'); }
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $title = trim($_POST['title'] ?? '');
    $body = trim($_POST['body'] ?? '');
    $file_path = $memo['file_path'] ?? null;
    $file_name = $memo['file_name'] ?? null;

    // Handle file upload
    if (!empty($_FILES['attachment']['name']) && $_FILES['attachment']['error'] === UPLOAD_ERR_OK) {
        $allowed = ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'gif'];
        $ext = strtolower(pathinfo($_FILES['attachment']['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $allowed)) {
            $error = 'File type not allowed. Accepted: ' . implode(', ', $allowed);
        } elseif ($_FILES['attachment']['size'] > 10 * 1024 * 1024) {
            $error = 'File too large (max 10MB).';
        } else {
            $safe_name = time() . '_' . preg_replace('/[^a-zA-Z0-9._-]/', '_', $_FILES['attachment']['name']);
            $dest = __DIR__ . '/uploads/memos/' . $safe_name;
            if (move_uploaded_file($_FILES['attachment']['tmp_name'], $dest)) {
                // Delete old file if replacing
                if ($file_path && file_exists(__DIR__ . '/' . $file_path)) {
                    unlink(__DIR__ . '/' . $file_path);
                }
                $file_path = 'uploads/memos/' . $safe_name;
                $file_name = $_FILES['attachment']['name'];
            } else {
                $error = 'Failed to upload file.';
            }
        }
    }

    // Handle file removal
    if (!empty($_POST['remove_file']) && $file_path) {
        if (file_exists(__DIR__ . '/' . $file_path)) {
            unlink(__DIR__ . '/' . $file_path);
        }
        $file_path = null;
        $file_name = null;
    }

    if (!$error && !$title) {
        $error = 'Title is required.';
    }

    if (!$error) {
        if ($memo) {
            $stmt = db()->prepare('UPDATE memos SET title = :t, body = :b, file_path = :fp, file_name = :fn, updated_at = NOW() WHERE id = :id');
            $stmt->execute([':t' => $title, ':b' => $body, ':fp' => $file_path, ':fn' => $file_name, ':id' => $memo['id']]);
            flash('success', 'Memo updated.');
            redirect('memo.php?id=' . $memo['id']);
        } else {
            $stmt = db()->prepare('INSERT INTO memos (author_id, title, body, file_path, file_name) VALUES (:a, :t, :b, :fp, :fn)');
            $stmt->execute([':a' => $user['id'], ':t' => $title, ':b' => $body, ':fp' => $file_path, ':fn' => $file_name]);
            $new_id = db()->lastInsertId();
            flash('success', 'Memo posted.');
            redirect('memo.php?id=' . $new_id);
        }
    }
}

require __DIR__ . '/includes/header.php';
?>

<link href="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.snow.css" rel="stylesheet">

<p style="margin-bottom:1rem;"><a href="memos.php">&larr; Memos</a></p>
<h1><?= $memo ? 'Edit Memo' : 'New Memo' ?></h1>

<?php if ($error): ?>
  <div class="alert alert-error"><?= e($error) ?></div>
<?php endif; ?>

<form method="post" enctype="multipart/form-data" class="card" id="memo-form">
  <?= csrf_field() ?>
  <div class="form-group">
    <label for="title">Title</label>
    <input type="text" id="title" name="title" required value="<?= e($memo['title'] ?? '') ?>">
  </div>

  <div class="form-group">
    <label>Body</label>
    <div id="editor" style="min-height:200px; background:#fff;"><?= $memo['body'] ?? '' ?></div>
    <input type="hidden" name="body" id="body-input">
  </div>

  <div class="form-group">
    <label for="attachment">Attach File (PDF, DOCX, images &mdash; max 10MB)</label>
    <input type="file" id="attachment" name="attachment" accept=".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg,.gif" style="font-size:.9rem;">
    <?php if (!empty($memo['file_name'])): ?>
      <div style="margin-top:.4rem; font-size:.85rem;">
        Current: <a href="<?= e($memo['file_path']) ?>" target="_blank"><?= e($memo['file_name']) ?></a>
        <label class="form-check" style="display:inline-flex; margin-left:.8rem;">
          <input type="checkbox" name="remove_file" value="1"> Remove file
        </label>
      </div>
    <?php endif; ?>
  </div>

  <button type="submit" class="btn btn-primary"><?= $memo ? 'Save Changes' : 'Post Memo' ?></button>
</form>

<script src="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.js"></script>
<script>
var quill = new Quill('#editor', {
  theme: 'snow',
  modules: {
    toolbar: [
      [{ 'header': [1, 2, 3, false] }],
      ['bold', 'italic', 'underline', 'strike'],
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      ['blockquote'],
      ['link'],
      ['clean']
    ]
  }
});
document.getElementById('memo-form').addEventListener('submit', function() {
  document.getElementById('body-input').value = quill.root.innerHTML;
});
</script>

<?php require __DIR__ . '/includes/footer.php'; ?>
