<?php
require_once __DIR__ . '/includes/auth.php';
require_commissioner();
if ($_SERVER['REQUEST_METHOD'] !== 'POST') redirect('memos.php');
csrf_verify();
$id = (int)($_POST['id'] ?? 0);
$stmt = db()->prepare('DELETE FROM memos WHERE id = :id');
$stmt->execute([':id' => $id]);
flash('success', 'Memo deleted.');
redirect('memos.php');
