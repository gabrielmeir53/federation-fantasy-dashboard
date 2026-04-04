<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/db.php';

function send_telegram_to(string $chat_id, string $message): bool {
    $token = defined('TG_BOT_TOKEN') ? TG_BOT_TOKEN : '';
    if (!$token || !$chat_id) return false;

    $url = "https://api.telegram.org/bot{$token}/sendMessage";
    $data = http_build_query([
        'chat_id'    => $chat_id,
        'text'       => $message,
        'parse_mode' => 'HTML',
    ]);

    $ctx = stream_context_create([
        'http' => [
            'method'  => 'POST',
            'header'  => "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => $data,
            'timeout' => 10,
        ],
    ]);

    $result = @file_get_contents($url, false, $ctx);
    return $result !== false;
}

function send_telegram(string $message): bool {
    $commissioners = db()->query("SELECT telegram_chat_id FROM users WHERE role = 'commissioner' AND telegram_chat_id IS NOT NULL")->fetchAll(PDO::FETCH_COLUMN);
    if (empty($commissioners)) return false;

    $success = true;
    foreach ($commissioners as $chat_id) {
        if (!send_telegram_to($chat_id, $message)) {
            $success = false;
        }
    }
    return $success;
}
