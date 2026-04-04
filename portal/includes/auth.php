<?php
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/functions.php';
require_once __DIR__ . '/csrf.php';

function init_session(): void {
    if (session_status() === PHP_SESSION_NONE) {
        session_set_cookie_params([
            'lifetime' => 86400 * 7,
            'path' => '/portal/',
            'secure' => true,
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }
}

function is_logged_in(): bool {
    init_session();
    return !empty($_SESSION['user_id']);
}

function current_user(): ?array {
    if (!is_logged_in()) return null;
    return [
        'id' => $_SESSION['user_id'],
        'username' => $_SESSION['username'],
        'display_name' => $_SESSION['display_name'],
        'preferred_name' => $_SESSION['preferred_name'] ?? '',
        'role' => $_SESSION['role'],
        'team_key' => $_SESSION['team_key'],
        'last_login_prev' => $_SESSION['last_login_prev'] ?? null,
        'last_login_tz_prev' => $_SESSION['last_login_tz_prev'] ?? 'America/New_York',
        'timezone' => $_SESSION['timezone'] ?? 'America/New_York',
    ];
}

function require_login(): array {
    if (!is_logged_in()) {
        header('Location: index.php');
        exit;
    }
    return current_user();
}

function require_role(string $role): array {
    $user = require_login();
    if ($user['role'] !== $role) {
        http_response_code(403);
        die('<h1>403 Forbidden</h1><p>You do not have access to this page.</p>');
    }
    return $user;
}

function require_commissioner(): array {
    return require_role('commissioner');
}

function require_user(int $id): array {
    $user = require_login();
    if ((int)$user['id'] !== $id) {
        http_response_code(403);
        die('<h1>403 Forbidden</h1><p>You do not have access to this page.</p>');
    }
    return $user;
}

function is_commissioner(): bool {
    $user = current_user();
    return $user && $user['role'] === 'commissioner';
}

function is_admin(): bool {
    $user = current_user();
    return $user && (int)$user['id'] === (defined('GABE_USER_ID') ? GABE_USER_ID : 1);
}

function login(string $username, string $password): bool {
    $stmt = db()->prepare('SELECT * FROM users WHERE username = :u');
    $stmt->execute([':u' => $username]);
    $user = $stmt->fetch();
    if (!$user || !password_verify($password, $user['password_hash'])) {
        return false;
    }
    session_regenerate_id(true);
    $_SESSION['user_id'] = $user['id'];
    $_SESSION['username'] = $user['username'];
    $_SESSION['display_name'] = $user['display_name'];
    $_SESSION['preferred_name'] = $user['preferred_name'] ?? '';
    $_SESSION['role'] = $user['role'];
    $_SESSION['team_key'] = $user['team_key'];
    $_SESSION['must_change_password'] = (bool)$user['must_change_password'];
    $_SESSION['last_login_prev'] = $user['last_login'];
    $_SESSION['last_login_tz_prev'] = $user['last_login_tz'] ?? $user['timezone'] ?? 'America/New_York';

    // Save timezone from login form
    $tz = trim($_POST['timezone'] ?? '');
    if ($tz && in_array($tz, timezone_identifiers_list())) {
        $_SESSION['timezone'] = $tz;
        $stmt = db()->prepare('UPDATE users SET timezone = :tz, last_login_tz = :ltz, last_login = NOW() WHERE id = :id');
        $stmt->execute([':tz' => $tz, ':ltz' => $tz, ':id' => $user['id']]);
    } else {
        $_SESSION['timezone'] = $user['timezone'] ?? 'America/New_York';
        $stmt = db()->prepare('UPDATE users SET last_login = NOW(), last_login_tz = timezone WHERE id = :id');
        $stmt->execute([':id' => $user['id']]);
    }
    return true;
}

function logout(): void {
    init_session();
    $_SESSION = [];
    session_destroy();
    header('Location: index.php');
    exit;
}

function e(string $str): string {
    return htmlspecialchars($str, ENT_QUOTES, 'UTF-8');
}
