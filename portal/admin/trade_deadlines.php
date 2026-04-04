<?php
$page_title = 'Admin';
require_once __DIR__ . '/../includes/auth.php';
$user = require_commissioner();

$pdo = db();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_verify();
    $leagues = ['ysf_fl', 'ysf_ba', 'ysf_hl', 'ysf_lb'];
    $stmt = $pdo->prepare('UPDATE trade_deadlines SET deadline = :d, championship_end = :c, updated_by = :u, updated_at = NOW() WHERE league_key = :lk');
    foreach ($leagues as $lk) {
        $deadline = trim($_POST["deadline_{$lk}"] ?? '') ?: null;
        $champ_end = trim($_POST["champ_{$lk}"] ?? '') ?: null;
        $stmt->execute([':d' => $deadline, ':c' => $champ_end, ':u' => $user['id'], ':lk' => $lk]);
    }
    flash('success', 'Trade deadlines updated.');
    redirect(SITE_URL . '/admin/trade_deadlines.php');
}

$deadlines = $pdo->query('SELECT td.*, u.display_name AS updater FROM trade_deadlines td LEFT JOIN users u ON td.updated_by = u.id ORDER BY league_key')->fetchAll();

// Auto-pull championship end dates from scraper data
$auto_champ = [];
foreach ($deadlines as $dl) {
    $auto_champ[$dl['league_key']] = get_championship_end_from_data($dl['league_key']);
}

require __DIR__ . '/../includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="<?= SITE_URL ?>/admin/users.php">&larr; Admin</a></p>
<h1>Trade Deadlines</h1>
<p style="font-size:.9rem; color:var(--text-dim); margin-bottom:1.2rem;">
  Set the trade deadline for each league. Championship end dates are auto-detected from playoff schedules. Players and draft picks from a league cannot be traded between its deadline and championship end.
</p>

<form method="post" class="card">
  <?= csrf_field() ?>

  <?php foreach ($deadlines as $dl): ?>
  <?php
    $lk = $dl['league_key'];
    $auto = $auto_champ[$lk] ?? null;
    $effective_champ = $dl['championship_end'] ?: $auto;
    $is_locked = is_league_trade_locked($lk);
  ?>
  <fieldset class="trade-side" style="margin-bottom:1rem;">
    <legend>
      <?= e($dl['league_name']) ?>
      <?php if ($is_locked): ?>
        <span class="badge badge-red" style="margin-left:.5rem;">Locked</span>
      <?php endif; ?>
    </legend>
    <div class="form-row">
      <div class="form-group">
        <label for="deadline_<?= $lk ?>">Trade Deadline</label>
        <input type="datetime-local" id="deadline_<?= $lk ?>" name="deadline_<?= $lk ?>"
               value="<?= $dl['deadline'] ? date('Y-m-d\TH:i', strtotime($dl['deadline'])) : '' ?>">
      </div>
      <div class="form-group">
        <label for="champ_<?= $lk ?>">Championship End (optional override)</label>
        <input type="datetime-local" id="champ_<?= $lk ?>" name="champ_<?= $lk ?>"
               value="<?= $dl['championship_end'] ? date('Y-m-d\TH:i', strtotime($dl['championship_end'])) : '' ?>">
        <?php if ($auto && !$dl['championship_end']): ?>
          <span style="font-size:.75rem; color:var(--text-muted); display:block; margin-top:.2rem;">
            Auto-detected: <?= format_date(substr($auto, 0, 10)) ?>
          </span>
        <?php endif; ?>
      </div>
    </div>
    <?php if ($dl['updated_by']): ?>
    <p style="font-size:.75rem; color:var(--text-muted);">Last updated by <?= e($dl['updater']) ?> on <?= format_datetime($dl['updated_at']) ?></p>
    <?php endif; ?>
  </fieldset>
  <?php endforeach; ?>

  <button type="submit" class="btn btn-primary">Save Deadlines</button>
</form>

<?php require __DIR__ . '/../includes/footer.php'; ?>
