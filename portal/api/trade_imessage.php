<?php
require_once __DIR__ . '/../includes/config.php';
require_once __DIR__ . '/../includes/db.php';
require_once __DIR__ . '/../includes/functions.php';

header('Content-Type: application/json');

// API key auth (no session required)
$key = $_SERVER['HTTP_X_API_KEY'] ?? $_GET['key'] ?? '';
if (!$key || !defined('IMESSAGE_API_KEY') || !hash_equals(IMESSAGE_API_KEY, $key)) {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

$pdo = db();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    // Return approved trades not yet sent via iMessage
    $trades = $pdo->query("
        SELECT t.id, t.status, t.approved_at
        FROM trades t
        WHERE t.status IN ('approved','processed')
          AND t.imessage_sent = 0
        ORDER BY t.reviewed_at ASC
    ")->fetchAll();

    $results = [];
    foreach ($trades as $t) {
        $results[] = [
            'trade_id' => (int)$t['id'],
            'summary'  => strip_tags(format_trade_summary($pdo, $t['id'])),
        ];
    }

    echo json_encode(['trades' => $results]);

} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Mark a trade as iMessage sent
    $input = json_decode(file_get_contents('php://input'), true);
    $trade_id = (int)($input['trade_id'] ?? 0);
    if (!$trade_id) {
        http_response_code(400);
        echo json_encode(['error' => 'trade_id required']);
        exit;
    }

    $pdo->prepare('UPDATE trades SET imessage_sent = 1 WHERE id = :id')->execute([':id' => $trade_id]);
    echo json_encode(['ok' => true]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
}
