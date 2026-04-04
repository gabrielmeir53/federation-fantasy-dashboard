<?php
$page_title = 'Profile';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$stmt = db()->prepare('SELECT * FROM users WHERE id = :id');
$stmt->execute([':id' => $user['id']]);
$profile = $stmt->fetch();

$error = '';
$success = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $display_name = trim($_POST['display_name'] ?? '');
    $email = trim($_POST['email'] ?? '') ?: null;
    $phone = trim($_POST['phone'] ?? '') ?: null;
    $username = trim($_POST['username'] ?? '');
    $notify = !empty($_POST['notify_email']) ? 1 : 0;

    if (!$display_name || !$username) {
        $error = 'Display name and username are required.';
    } else {
        // Check username uniqueness if changed
        if ($username !== $profile['username']) {
            $check = db()->prepare('SELECT id FROM users WHERE username = :u AND id != :id');
            $check->execute([':u' => $username, ':id' => $user['id']]);
            if ($check->fetch()) {
                $error = 'That username is already taken.';
            }
        }

        if (!$error) {
            $stmt = db()->prepare('UPDATE users SET username = :u, display_name = :d, email = :e, phone = :p, notify_email = :n WHERE id = :id');
            $stmt->execute([':u' => $username, ':d' => $display_name, ':e' => $email, ':p' => $phone, ':n' => $notify, ':id' => $user['id']]);
            // Update session
            $_SESSION['username'] = $username;
            $_SESSION['display_name'] = $display_name;
            flash('success', 'Profile updated.');
            redirect('profile.php');
        }
    }
}

require __DIR__ . '/includes/header.php';
?>

<h1>Profile</h1>

<?php if ($error): ?>
  <div class="alert alert-error"><?= e($error) ?></div>
<?php endif; ?>

<form method="post" class="card">
  <?= csrf_field() ?>
  <div class="form-row">
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" required value="<?= e($profile['username']) ?>">
    </div>
    <div class="form-group">
      <label for="display_name">Display Name</label>
      <input type="text" id="display_name" name="display_name" required value="<?= e($profile['display_name']) ?>">
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label for="email">Email</label>
      <input type="email" id="email" name="email" value="<?= e($profile['email'] ?? '') ?>" placeholder="your@email.com">
    </div>
    <div class="form-group">
      <label for="phone">Phone Number</label>
      <input type="tel" id="phone" name="phone" value="<?= e($profile['phone'] ?? '') ?>" placeholder="(555) 555-5555">
    </div>
  </div>
  <div class="form-group">
    <label>Team</label>
    <input type="text" disabled value="<?= e(team_name($profile['team_key'])) ?>" style="background:#f0efe8;">
  </div>
  <div class="form-group">
    <label class="form-check">
      <input type="checkbox" name="notify_email" value="1" <?= $profile['notify_email'] ? 'checked' : '' ?>> Receive email notifications for memos and proposals
    </label>
  </div>
  <div class="btn-row">
    <button type="submit" class="btn btn-primary">Save Profile</button>
    <a href="password.php" class="btn btn-outline">Change Password</a>
  </div>
</form>

<script>
(function() {
  var ph = document.getElementById('phone');
  if (!ph) return;
  ph.addEventListener('input', function() {
    var d = this.value.replace(/\D/g, '').substring(0, 10);
    if (d.length === 0) { this.value = ''; }
    else if (d.length <= 3) { this.value = '(' + d; }
    else if (d.length <= 6) { this.value = '(' + d.substring(0,3) + ') ' + d.substring(3); }
    else { this.value = '(' + d.substring(0,3) + ') ' + d.substring(3,6) + '-' + d.substring(6); }
  });
  // Format on page load if value exists
  if (ph.value) { ph.dispatchEvent(new Event('input')); }
})();
</script>
<?php require __DIR__ . '/includes/footer.php'; ?>
