<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/mail.php';
require_once __DIR__ . '/includes/telegram.php';
$user = require_commissioner();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { redirect('trades.php'); }
csrf_verify();

$trade_id = (int)($_POST['trade_id'] ?? 0);
$action = $_POST['action'] ?? '';
if (!$trade_id || !in_array($action, ['approve', 'reject', 'process'])) { redirect('trades.php'); }

$pdo = db();

$trade = $pdo->prepare('SELECT * FROM trades WHERE id = :id');
$trade->execute([':id' => $trade_id]);
$trade = $trade->fetch();
if (!$trade) {
    flash('error', 'Trade not found.');
    redirect('trades.php');
}

// Get all party emails
$parties = $pdo->prepare('SELECT u.email, u.display_name FROM trade_sides ts JOIN users u ON ts.user_id = u.id WHERE ts.trade_id = :tid AND u.notify_email = 1');
$parties->execute([':tid' => $trade_id]);
$all_parties = $parties->fetchAll();
$party_emails = array_filter(array_column($all_parties, 'email'));

$summary = format_trade_summary($pdo, $trade_id);

if ($action === 'approve' && $trade['status'] === 'pending_review') {
    $pdo->prepare("UPDATE trades SET status = 'approved', reviewed_by = :uid, reviewed_at = NOW() WHERE id = :id")
        ->execute([':uid' => $user['id'], ':id' => $trade_id]);

    portal_mail(
        $party_emails,
        'Federation Trade #' . $trade_id . ' — Approved',
        '<h2>Trade Approved</h2>'
        . '<p>The Commission has approved this trade.</p>'
        . $summary
        . '<p><a href="' . SITE_URL . '/trade.php?id=' . $trade_id . '">View Trade &rarr;</a></p>'
    );

    send_telegram(
        "✅ <b>Trade #{$trade_id} — Approved</b>\n\n"
        . strip_tags($summary) . "\n\n"
        . "Approved by " . e($user['display_name'])
    );

    flash('success', 'Trade approved. Parties notified.');

} elseif ($action === 'reject' && $trade['status'] === 'pending_review') {
    $reason = trim($_POST['reject_reason'] ?? '');
    $pdo->prepare("UPDATE trades SET status = 'rejected', reviewed_by = :uid, reviewed_at = NOW(), reject_reason = :r WHERE id = :id")
        ->execute([':uid' => $user['id'], ':id' => $trade_id, ':r' => $reason ?: null]);

    portal_mail(
        $party_emails,
        'Federation Trade #' . $trade_id . ' — Rejected by Commission',
        '<h2>Trade Rejected</h2>'
        . '<p>The Commission has rejected this trade.</p>'
        . ($reason ? '<p><strong>Reason:</strong> ' . e($reason) . '</p>' : '')
        . $summary
        . '<p><a href="' . SITE_URL . '/trade.php?id=' . $trade_id . '">View Trade &rarr;</a></p>'
    );

    send_telegram(
        "❌ <b>Trade #{$trade_id} — Rejected</b>\n\n"
        . strip_tags($summary) . "\n\n"
        . "Rejected by " . e($user['display_name'])
        . ($reason ? "\nReason: {$reason}" : '')
    );

    flash('success', 'Trade rejected. Parties notified.');

} elseif ($action === 'process' && $trade['status'] === 'approved') {
    $pdo->prepare("UPDATE trades SET status = 'processed', processed_by = :uid, processed_at = NOW() WHERE id = :id")
        ->execute([':uid' => $user['id'], ':id' => $trade_id]);

    portal_mail(
        $party_emails,
        'Federation Trade #' . $trade_id . ' — Processed',
        '<h2>Trade Processed</h2>'
        . '<p>This trade has been entered on Fantrax and is now complete.</p>'
        . $summary
    );

    flash('success', 'Trade marked as processed.');

} else {
    flash('error', 'Invalid action for current trade status.');
}

redirect("trade.php?id={$trade_id}");
