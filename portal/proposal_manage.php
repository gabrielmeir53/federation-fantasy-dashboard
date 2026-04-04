<?php
require_once __DIR__ . '/includes/auth.php';
require_commissioner();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') redirect('proposals.php');
csrf_verify();

$id = (int)($_POST['id'] ?? 0);
$action = $_POST['action'] ?? '';
$user = current_user();

$stmt = db()->prepare('SELECT * FROM proposals WHERE id = :id');
$stmt->execute([':id' => $id]);
$p = $stmt->fetch();
if (!$p) { flash('error', 'Proposal not found.'); redirect('proposals.php'); }

switch ($action) {
    case 'approve':
        if ($p['status'] !== 'submitted') { flash('error', 'Can only approve submitted proposals.'); break; }
        $stmt = db()->prepare("UPDATE proposals SET status = 'open', opened_by = :uid, opened_at = NOW() WHERE id = :id");
        $stmt->execute([':uid' => $user['id'], ':id' => $id]);
        flash('success', 'Proposal opened for voting.');
        break;

    case 'reject':
        if (!in_array($p['status'], ['submitted', 'open'])) { flash('error', 'Cannot reject this proposal.'); break; }
        $stmt = db()->prepare("UPDATE proposals SET status = 'rejected', closed_at = NOW() WHERE id = :id");
        $stmt->execute([':id' => $id]);
        flash('success', 'Proposal rejected.');
        break;

    case 'close':
        if ($p['status'] !== 'open') { flash('error', 'Can only close open proposals.'); break; }
        $yes = db()->prepare("SELECT COUNT(*) FROM votes WHERE proposal_id = :pid AND vote = 'yes'");
        $yes->execute([':pid' => $id]);
        $yes_count = (int)$yes->fetchColumn();
        $needed = get_votes_needed($p['proposal_type'], (bool)$p['emergency']);
        $result = $yes_count >= $needed ? 'passed' : 'failed';
        $stmt = db()->prepare('UPDATE proposals SET status = :s, closed_at = NOW() WHERE id = :id');
        $stmt->execute([':s' => $result, ':id' => $id]);
        flash('success', "Proposal $result ($yes_count yes / $needed needed).");
        break;

    default:
        flash('error', 'Unknown action.');
}

redirect("proposal.php?id=$id");
