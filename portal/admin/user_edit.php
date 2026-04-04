<?php
$page_title = 'Admin';
require_once __DIR__ . '/../includes/auth.php';
$admin = require_commissioner();

$id = (int)($_GET['id'] ?? 0);
$edit_user = null;
if ($id) {
    $stmt = db()->prepare('SELECT * FROM users WHERE id = :id');
    $stmt->execute([':id' => $id]);
    $edit_user = $stmt->fetch();
    if (!$edit_user) { http_response_code(404); die('User not found.'); }
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $username = trim($_POST['username'] ?? '');
    $display_name = trim($_POST['display_name'] ?? '');
    $email = trim($_POST['email'] ?? '') ?: null;
    $team_key = trim($_POST['team_key'] ?? '') ?: null;
    $role = $_POST['role'] ?? 'member';
    $password = $_POST['password'] ?? '';
    if (!in_array($role, ['commissioner', 'member'])) $role = 'member';

    if (!$username || !$display_name) {
        $error = 'Username and display name are required.';
    } elseif (!$edit_user && !$password) {
        $error = 'Password is required for new users.';
    } else {
        if ($edit_user) {
            $sql = 'UPDATE users SET username=:u, display_name=:d, email=:e, team_key=:t, role=:r';
            $params = [':u' => $username, ':d' => $display_name, ':e' => $email, ':t' => $team_key, ':r' => $role, ':id' => $id];
            if ($password) {
                $sql .= ', password_hash=:p, must_change_password=1';
                $params[':p'] = password_hash($password, PASSWORD_DEFAULT);
            }
            $sql .= ' WHERE id=:id';
            db()->prepare($sql)->execute($params);
            flash('success', 'User updated.' . ($password ? ' Password reset — they must change it on next login.' : ''));
        } else {
            $hash = password_hash($password, PASSWORD_DEFAULT);
            $stmt = db()->prepare('INSERT INTO users (username, password_hash, display_name, email, team_key, role, must_change_password) VALUES (:u, :p, :d, :e, :t, :r, 1)');
            $stmt->execute([':u' => $username, ':p' => $hash, ':d' => $display_name, ':e' => $email, ':t' => $team_key, ':r' => $role]);
            flash('success', 'User created.');
        }
        redirect('users.php');
    }
}

require __DIR__ . '/../includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="users.php">&larr; All Members</a></p>
<h1><?= $edit_user ? 'Edit User' : 'Add User' ?></h1>

<?php if ($error): ?>
  <div class="alert alert-error"><?= e($error) ?></div>
<?php endif; ?>

<form method="post" class="card">
  <?= csrf_field() ?>
  <div class="form-row">
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" required value="<?= e($edit_user['username'] ?? '') ?>">
    </div>
    <div class="form-group">
      <label for="display_name">Display Name</label>
      <input type="text" id="display_name" name="display_name" required value="<?= e($edit_user['display_name'] ?? '') ?>">
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label for="email">Email</label>
      <input type="email" id="email" name="email" value="<?= e($edit_user['email'] ?? '') ?>">
    </div>
    <div class="form-group">
      <label for="team_key">Team Key</label>
      <input type="text" id="team_key" name="team_key" value="<?= e($edit_user['team_key'] ?? '') ?>" placeholder="e.g., team_01">
    </div>
  </div>
  <div class="form-group">
    <label for="role">Role</label>
    <select id="role" name="role">
      <option value="member" <?= ($edit_user['role'] ?? '') === 'member' ? 'selected' : '' ?>>Member</option>
      <option value="commissioner" <?= ($edit_user['role'] ?? '') === 'commissioner' ? 'selected' : '' ?>>Commissioner</option>
    </select>
  </div>
  <div class="form-group">
    <label for="password"><?= $edit_user ? 'Reset Password (leave blank to keep current)' : 'Password' ?></label>
    <input type="password" id="password" name="password" <?= $edit_user ? '' : 'required' ?> minlength="6">
  </div>
  <button type="submit" class="btn btn-primary"><?= $edit_user ? 'Save Changes' : 'Create User' ?></button>
</form>

<?php require __DIR__ . '/../includes/footer.php'; ?>
