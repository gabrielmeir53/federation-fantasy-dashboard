<?php
$page_title = 'Proposals';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $title = trim($_POST['title'] ?? '');
    $body = trim($_POST['body'] ?? '');
    $type = $_POST['proposal_type'] ?? 'rule';
    $emergency = !empty($_POST['emergency']) ? 1 : 0;
    if (!in_array($type, ['amendment', 'rule'])) $type = 'rule';

    $file_path = null;
    $file_name = null;

    // Handle file upload
    if (!empty($_FILES['attachment']['name']) && $_FILES['attachment']['error'] === UPLOAD_ERR_OK) {
        $allowed = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'];
        $ext = strtolower(pathinfo($_FILES['attachment']['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $allowed)) {
            $error = 'File type not allowed. Accepted: ' . implode(', ', $allowed);
        } elseif ($_FILES['attachment']['size'] > 10 * 1024 * 1024) {
            $error = 'File too large (max 10MB).';
        } else {
            $safe_name = time() . '_' . preg_replace('/[^a-zA-Z0-9._-]/', '_', $_FILES['attachment']['name']);
            $dest = __DIR__ . '/uploads/proposals/' . $safe_name;
            if (move_uploaded_file($_FILES['attachment']['tmp_name'], $dest)) {
                $file_path = 'uploads/proposals/' . $safe_name;
                $file_name = $_FILES['attachment']['name'];
            } else {
                $error = 'Failed to upload file.';
            }
        }
    }

    if (!$error && !$title) {
        $error = 'Title is required.';
    }

    if (!$error) {
        $stmt = db()->prepare('INSERT INTO proposals (submitted_by, title, body, proposal_type, emergency, file_path, file_name) VALUES (:u, :t, :b, :tp, :e, :fp, :fn)');
        $stmt->execute([':u' => $user['id'], ':t' => $title, ':b' => $body, ':tp' => $type, ':e' => $emergency, ':fp' => $file_path, ':fn' => $file_name]);
        flash('success', 'Proposal submitted. A commissioner will review it.');
        redirect('proposals.php');
    }
}

require __DIR__ . '/includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="proposals.php">&larr; Proposals</a></p>
<h1>Submit Proposal</h1>
<p style="font-size:.9rem; color:var(--text-dim); margin-bottom:1.2rem;">Any member can submit a proposal. A commissioner must approve it before it opens for voting.</p>

<?php if ($error): ?>
  <div class="alert alert-error"><?= e($error) ?></div>
<?php endif; ?>

<form method="post" enctype="multipart/form-data" class="card">
  <?= csrf_field() ?>
  <div class="form-group">
    <label for="title">Title</label>
    <input type="text" id="title" name="title" required value="<?= e($_POST['title'] ?? '') ?>" placeholder="e.g., Increase FAAB budget to $200">
  </div>
  <div class="form-group">
    <label for="body">Description (optional if uploading a file)</label>
    <textarea id="body" name="body" placeholder="Explain the proposed change and your reasoning..."><?= e($_POST['body'] ?? '') ?></textarea>
  </div>
  <div class="form-group">
    <label for="attachment">Attach File (PDF, DOCX, images &mdash; max 10MB)</label>
    <input type="file" id="attachment" name="attachment" accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" style="font-size:.9rem;">
  </div>
  <div class="form-row">
    <div class="form-group">
      <label for="proposal_type">Type</label>
      <select id="proposal_type" name="proposal_type">
        <option value="rule">New Rule / Rule Change (51%)</option>
        <option value="amendment">Constitutional Amendment (75%)</option>
      </select>
    </div>
  </div>
  <div class="form-group">
    <label class="form-check">
      <input type="checkbox" name="emergency" value="1"> Emergency (mid-season, requires 83.34%)
    </label>
  </div>
  <button type="submit" class="btn btn-primary">Submit Proposal</button>
</form>

<?php require __DIR__ . '/includes/footer.php'; ?>
