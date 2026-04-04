<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/mail.php';
require_once __DIR__ . '/includes/telegram.php';
$user = require_login();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { redirect('trades.php'); }
csrf_verify();

$trade_id = (int)($_POST['trade_id'] ?? 0);
$action = $_POST['action'] ?? '';
if (!$trade_id || !in_array($action, ['accept', 'reject'])) { redirect('trades.php'); }

$pdo = db();

// Verify trade exists and is pending acceptance
$trade = $pdo->prepare("SELECT * FROM trades WHERE id = :id AND status = 'pending_acceptance'");
$trade->execute([':id' => $trade_id]);
$trade = $trade->fetch();
if (!$trade) {
    flash('error', 'Trade not found or no longer pending.');
    redirect('trades.php');
}

// Verify user is a counter-party (not submitter) who hasn't accepted yet
$my_side = $pdo->prepare('SELECT * FROM trade_sides WHERE trade_id = :tid AND user_id = :uid AND is_submitter = 0');
$my_side->execute([':tid' => $trade_id, ':uid' => $user['id']]);
$my_side = $my_side->fetch();
if (!$my_side) {
    flash('error', 'You are not a counter-party on this trade.');
    redirect("trade.php?id={$trade_id}");
}
if ($my_side['accepted']) {
    flash('error', 'You have already accepted this trade.');
    redirect("trade.php?id={$trade_id}");
}

if ($action === 'reject') {
    // Cancel the entire trade
    $pdo->prepare("UPDATE trades SET status = 'cancelled' WHERE id = :id")->execute([':id' => $trade_id]);

    // Notify all parties
    $parties = $pdo->prepare('SELECT u.email, u.display_name FROM trade_sides ts JOIN users u ON ts.user_id = u.id WHERE ts.trade_id = :tid AND u.notify_email = 1');
    $parties->execute([':tid' => $trade_id]);
    $all_parties = $parties->fetchAll();
    $emails = array_column($all_parties, 'email');
    portal_mail(
        array_filter($emails),
        'Federation Trade #' . $trade_id . ' — Rejected',
        '<h2>Trade Rejected</h2>'
        . '<p>' . e($user['display_name']) . ' has rejected the trade.</p>'
        . '<p><a href="' . SITE_URL . '/trade.php?id=' . $trade_id . '">View Trade &rarr;</a></p>'
    );

    flash('success', 'Trade rejected and cancelled.');
    redirect("trade.php?id={$trade_id}");
}

// Accept
$pdo->prepare('UPDATE trade_sides SET accepted = 1, accepted_at = NOW() WHERE id = :id')->execute([':id' => $my_side['id']]);

// Check if all parties have now accepted
$pending = $pdo->prepare('SELECT COUNT(*) FROM trade_sides WHERE trade_id = :tid AND accepted = 0');
$pending->execute([':tid' => $trade_id]);
$remaining = $pending->fetchColumn();

if ($remaining == 0) {
    // All accepted — move to pending_review
    $pdo->prepare("UPDATE trades SET status = 'pending_review', accepted_at = NOW() WHERE id = :id")->execute([':id' => $trade_id]);

    // Build trade summary for notifications
    $summary = format_trade_summary($pdo, $trade_id);

    // Notify commissioners via email + Telegram
    $commissioners = $pdo->query("SELECT email, display_name FROM users WHERE role = 'commissioner' AND notify_email = 1")->fetchAll();
    $comm_emails = array_filter(array_column($commissioners, 'email'));
    portal_mail(
        $comm_emails,
        'Federation Trade #' . $trade_id . ' — Ready for Review',
        '<h2>Trade Ready for Commission Review</h2>'
        . '<p>All parties have accepted. The 48-hour review period has begun.</p>'
        . $summary
        . '<p><a href="' . SITE_URL . '/trade.php?id=' . $trade_id . '">Review Trade &rarr;</a></p>'
    );

    send_telegram(
        "🔔 <b>Trade #{$trade_id} — Ready for Review</b>\n\n"
        . strip_tags($summary) . "\n\n"
        . "All parties accepted. 48-hour review period started.\n"
        . SITE_URL . "/trade.php?id={$trade_id}"
    );

    flash('success', 'Trade accepted. All parties agreed — sent to Commission for review.');
} else {
    flash('success', 'Trade accepted. Waiting for remaining parties.');
}

redirect("trade.php?id={$trade_id}");
