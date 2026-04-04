<?php
$page_title = 'Change Password';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();
$error = '';
$forced = !empty($_SESSION['must_change_password']);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $current = $_POST['current'] ?? '';
    $new = $_POST['new'] ?? '';
    $confirm = $_POST['confirm'] ?? '';

    $stmt = db()->prepare('SELECT password_hash FROM users WHERE id = :id');
    $stmt->execute([':id' => $user['id']]);
    $row = $stmt->fetch();

    if (!$forced && !password_verify($current, $row['password_hash'])) {
        $error = 'Current password is incorrect.';
    } elseif (strlen($new) < 6) {
        $error = 'New password must be at least 6 characters.';
    } elseif ($new !== $confirm) {
        $error = 'Passwords do not match.';
    } else {
        $hash = password_hash($new, PASSWORD_DEFAULT);
        $stmt = db()->prepare('UPDATE users SET password_hash = :p, must_change_password = 0 WHERE id = :id');
        $stmt->execute([':p' => $hash, ':id' => $user['id']]);
        $_SESSION['must_change_password'] = false;
        flash('success', 'Password changed successfully.');
        redirect('dashboard.php');
    }
}

require __DIR__ . '/includes/header.php';
?>

<div class="login-wrap">
  <h1>Change Password</h1>
  <?php if ($forced): ?>
    <p class="subtitle">You must change your password before continuing.</p>
  <?php endif; ?>

  <?php if ($error): ?>
    <div class="alert alert-error"><?= e($error) ?></div>
  <?php endif; ?>

  <form method="post" class="card">
    <?= csrf_field() ?>
    <?php if (!$forced): ?>
    <div class="form-group">
      <label for="current">Current Password</label>
      <input type="password" id="current" name="current" required>
    </div>
    <?php endif; ?>
    <div class="form-group">
      <label for="new">New Password</label>
      <input type="password" id="new" name="new" required minlength="6">
    </div>
    <div class="form-group">
      <label for="confirm">Confirm New Password</label>
      <input type="password" id="confirm" name="confirm" required>
    </div>
    <button type="submit" class="btn btn-primary" style="width:100%">Change Password</button>
  </form>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
