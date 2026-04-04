<?php
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/csrf.php';
require_once __DIR__ . '/functions.php';
$_user = current_user();
$_page = $GLOBALS['page_title'] ?? 'Portal';
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= e($_page) ?> | <?= SITE_NAME ?></title>
  <!-- Replace with your Adobe Fonts (Typekit) project URL for the shuttleblock font, or swap --ui in portal.css to a different sans-serif -->
  <!-- <link rel="stylesheet" href="https://use.typekit.net/YOUR_TYPEKIT_ID.css"> -->
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= SITE_URL ?>/css/portal.css">
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="<?= MAIN_SITE_URL ?>" class="nav-brand" title="Back to main site">ySF</a>
    <span class="nav-sep">|</span>
    <a href="<?= SITE_URL ?>/dashboard.php" class="nav-brand-sub">Portal</a>
    <button class="nav-hamburger" aria-label="Toggle navigation">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav-links">
      <?php if ($_user): ?>
      <li><a href="<?= SITE_URL ?>/dashboard.php" <?= $_page === 'Dashboard' ? 'class="active"' : '' ?>>Dashboard</a></li>
      <li><a href="<?= SITE_URL ?>/memos.php" <?= $_page === 'Memos' ? 'class="active"' : '' ?>>Memos</a></li>
      <li><a href="<?= SITE_URL ?>/proposals.php" <?= $_page === 'Proposals' ? 'class="active"' : '' ?>>Proposals</a></li>
      <li><a href="<?= SITE_URL ?>/trades.php" <?= $_page === 'Trades' ? 'class="active"' : '' ?>>Trades</a></li>
      <?php if (is_admin()): ?>
      <li><a href="<?= SITE_URL ?>/advisor.php" <?= $_page === 'Advisor' ? 'class="active"' : '' ?>>Advisor</a></li>
      <?php endif; ?>
      <?php if (is_commissioner()): ?>
      <li><a href="<?= SITE_URL ?>/admin/users.php" <?= $_page === 'Admin' ? 'class="active"' : '' ?>>Admin</a></li>
      <?php endif; ?>
      <li class="nav-user">
        <a href="<?= SITE_URL ?>/profile.php" class="nav-username"><?= e($_user['display_name']) ?></a>
        <a href="<?= SITE_URL ?>/logout.php" class="nav-logout">Logout</a>
      </li>
      <?php endif; ?>
    </ul>
  </div>
</nav>

<main class="page">
  <div class="container">
    <?= render_flash() ?>
