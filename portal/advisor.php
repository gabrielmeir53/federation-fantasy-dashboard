<?php
$page_title = 'Advisor';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/Parsedown.php';

$user = require_login();
if (!is_admin()) {
    http_response_code(403);
    die('<h1>403 Forbidden</h1><p>Advisor reports are restricted.</p>');
}

$report_names = [
    'brief.md'    => 'Executive Brief',
    'response.md' => 'Full Analysis',
    'trades.md'   => 'Trade Recommendations',
    'waivers.md'  => 'Waiver Wire',
    'dynasty.md'  => 'Dynasty Outlook',
];

$reports_dir = defined('ADVISOR_REPORTS_DIR') ? ADVISOR_REPORTS_DIR : __DIR__ . '/../advisor/data/';
$available = [];
foreach ($report_names as $file => $label) {
    $path = $reports_dir . $file;
    if (file_exists($path)) {
        $available[$file] = [
            'label' => $label,
            'path' => $path,
            'modified' => filemtime($path),
        ];
    }
}

$selected = $_GET['report'] ?? '';
$content = '';
if ($selected && isset($available[$selected])) {
    $parsedown = new Parsedown();
    $parsedown->setSafeMode(true);
    $content = $parsedown->text(file_get_contents($available[$selected]['path']));
}

require __DIR__ . '/includes/header.php';
?>

<h1>Advisor Reports</h1>

<?php if (empty($available)): ?>
  <p style="color:var(--text-muted);">No advisor reports found. Run the advisor pipeline to generate reports.</p>
<?php else: ?>
  <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
    <div style="min-width:180px;">
      <ul class="report-list">
        <?php foreach ($available as $file => $info): ?>
        <li>
          <a href="?report=<?= e($file) ?>" <?= $selected === $file ? 'style="font-weight:700;"' : '' ?>>
            <?= e($info['label']) ?>
          </a>
          <div style="font-size:.75rem; color:var(--text-muted);"><?= date('M j, g:i A', $info['modified']) ?></div>
        </li>
        <?php endforeach; ?>
      </ul>
    </div>

    <?php if ($content): ?>
    <div style="flex:1; min-width:0;">
      <div class="card">
        <div class="report-content"><?= $content ?></div>
      </div>
    </div>
    <?php endif; ?>
  </div>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
