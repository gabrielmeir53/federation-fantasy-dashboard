<?php
$page_title = 'Admin';
require_once __DIR__ . '/../includes/auth.php';
$user = require_commissioner();

$users = db()->query('SELECT * FROM users ORDER BY role DESC, display_name ASC')->fetchAll();

require __DIR__ . '/../includes/header.php';
?>

<div style="display:flex; align-items:center; gap:1rem; margin-bottom:1.2rem;">
  <h1 style="margin-bottom:0;">Manage Members</h1>
  <a href="trade_deadlines.php" class="btn btn-outline btn-sm">Trade Deadlines</a>
  <a href="user_edit.php" class="btn btn-primary btn-sm">Add User</a>
</div>

<div class="card" style="overflow-x:auto;">
  <table class="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Username</th>
        <th>Team</th>
        <th>Role</th>
        <th>Last Login</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($users as $u): ?>
      <tr>
        <td><?= e($u['display_name']) ?></td>
        <td><?= e($u['username']) ?></td>
        <td><?= e(team_name($u['team_key'])) ?></td>
        <td><?= $u['role'] === 'commissioner' ? '<span class="badge badge-purple">Commissioner</span>' : '<span class="badge badge-gray">Member</span>' ?></td>
        <td style="font-size:.85rem; color:var(--text-muted);"><?= $u['last_login'] ? format_datetime($u['last_login']) : 'Never' ?></td>
        <td><a href="user_edit.php?id=<?= $u['id'] ?>" class="btn btn-outline btn-sm">Edit</a></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>

<?php require __DIR__ . '/../includes/footer.php'; ?>
