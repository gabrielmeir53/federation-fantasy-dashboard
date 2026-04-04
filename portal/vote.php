<?php
require_once __DIR__ . '/includes/auth.php';
$user = require_login();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') redirect('proposals.php');
csrf_verify();

$proposal_id = (int)($_POST['proposal_id'] ?? 0);
$vote = $_POST['vote'] ?? '';
if (!in_array($vote, ['yes', 'no', 'abstain'])) {
    flash('error', 'Invalid vote.');
    redirect("proposal.php?id=$proposal_id");
}

// Verify proposal is open
$stmt = db()->prepare("SELECT status FROM proposals WHERE id = :id AND status = 'open'");
$stmt->execute([':id' => $proposal_id]);
if (!$stmt->fetch()) {
    flash('error', 'This proposal is not open for voting.');
    redirect('proposals.php');
}

// Check not already voted
$stmt = db()->prepare('SELECT id FROM votes WHERE proposal_id = :pid AND user_id = :uid');
$stmt->execute([':pid' => $proposal_id, ':uid' => $user['id']]);
if ($stmt->fetch()) {
    flash('error', 'You have already voted on this proposal.');
    redirect("proposal.php?id=$proposal_id");
}

$stmt = db()->prepare('INSERT INTO votes (proposal_id, user_id, vote) VALUES (:pid, :uid, :v)');
$stmt->execute([':pid' => $proposal_id, ':uid' => $user['id'], ':v' => $vote]);
flash('success', 'Vote cast.');
redirect("proposal.php?id=$proposal_id");
