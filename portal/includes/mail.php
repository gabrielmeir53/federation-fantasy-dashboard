<?php
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/config.php';

/**
 * Send email via Gmail SMTP. Reliable delivery, no spam issues.
 */
function smtp_mail(string $to, string $subject, string $html_body): bool {
    $from = 'noreply@yourdomain.com';
    $user = SMTP_USER;
    $pass = SMTP_PASS;
    if (!$user || !$pass) return false;

    $boundary = md5(time());
    $headers = "From: Federation Portal <{$from}>\r\n"
        . "Reply-To: {$from}\r\n"
        . "MIME-Version: 1.0\r\n"
        . "Content-Type: text/html; charset=UTF-8\r\n";

    $msg = "Subject: {$subject}\r\n"
        . "To: {$to}\r\n"
        . $headers
        . "\r\n"
        . $html_body;

    $fp = fsockopen('ssl://smtp.gmail.com', 465, $errno, $errstr, 10);
    if (!$fp) return false;

    $resp = function() use ($fp) { return fgets($fp, 512); };
    $send = function(string $cmd) use ($fp, $resp) {
        fwrite($fp, $cmd . "\r\n");
        return $resp();
    };

    $resp(); // greeting
    $send("EHLO yourdomain.com");
    // read all EHLO lines
    while (true) {
        $line = $resp();
        if (!$line || $line[3] === ' ') break;
    }
    $send("AUTH LOGIN");
    $send(base64_encode($user));
    $send(base64_encode($pass));
    $send("MAIL FROM:<{$from}>");
    $send("RCPT TO:<{$to}>");
    $send("DATA");
    fwrite($fp, $msg . "\r\n.\r\n");
    $result = $resp();
    $send("QUIT");
    fclose($fp);

    return strpos($result, '250') !== false;
}

function portal_mail(array $to_emails, string $subject, string $body): bool {
    $html = '<!DOCTYPE html><html><body style="font-family:Georgia,serif;color:#1a1a1a;max-width:600px;margin:0 auto;padding:20px;">'
        . $body
        . '<hr style="border:none;border-top:1px solid #d4d3cc;margin:20px 0;">'
        . '<p style="font-size:12px;color:#888;">This is an automated message from the <a href="https://yourdomain.com/portal/" style="color:#7700b5;">Federation Portal</a>.</p>'
        . '</body></html>';

    $success = true;
    foreach ($to_emails as $email) {
        if (!$email) continue;
        if (!smtp_mail($email, $subject, $html)) {
            $success = false;
        }
    }
    return $success;
}

function notify_all_members(string $subject, string $body): bool {
    $emails = db()->query('SELECT email FROM users WHERE email IS NOT NULL AND notify_email = 1')
        ->fetchAll(PDO::FETCH_COLUMN);
    if (empty($emails)) return true;
    return portal_mail($emails, $subject, $body);
}
