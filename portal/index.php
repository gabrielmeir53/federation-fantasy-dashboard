<?php
require_once __DIR__ . '/includes/auth.php';

if (is_logged_in()) {
    if (!empty($_SESSION['must_change_password'])) {
        redirect('password.php');
    }
    redirect('dashboard.php');
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';
    if (login($username, $password)) {
        if (!empty($_SESSION['must_change_password'])) {
            redirect('password.php');
        }
        redirect('dashboard.php');
    }
    $error = 'Invalid username or password.';
}

$page_title = 'Login';
require __DIR__ . '/includes/header.php';
?>

<div class="login-wrap">
  <h1>Federation Portal</h1>
  <p class="subtitle">Member Login</p>

  <?php if ($error): ?>
    <div class="alert alert-error"><?= e($error) ?></div>
  <?php endif; ?>

  <form method="post" class="card">
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" required autofocus>
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" required>
    </div>
    <input type="hidden" name="timezone" id="tz-field" value="">
    <button type="submit" class="btn btn-primary" style="width:100%">Log In</button>
  </form>
  <script>
  try { document.getElementById('tz-field').value = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch(e) {}
  </script>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
