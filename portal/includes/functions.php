<?php
function team_name(?string $team_key): string {
    static $teams = [
        'team_01' => 'Alpha F.C.',
        'team_02' => 'Bravo United',
        'team_03' => 'Charlie S.C.',
        'team_04' => 'Delta Athletic',
        'team_05' => 'Echo Rangers',
        'team_06' => 'Foxtrot City',
        'team_07' => 'Golf Town',
        'team_08' => 'Hotel F.C.',
        'team_09' => 'India United',
        'team_10' => 'Juliet S.C.',
        'team_11' => 'Kilo Athletic',
        'team_12' => 'Lima Rovers',
    ];
    return $teams[$team_key] ?? ($team_key ?? '—');
}

function get_threshold(string $type, bool $emergency): float {
    if ($emergency) return 5 / 6; // 83.34%
    return $type === 'amendment' ? 0.75 : 0.51;
}

function get_votes_needed(string $type, bool $emergency, int $total = 12): int {
    return (int)ceil($total * get_threshold($type, $emergency));
}

function format_date(string $date): string {
    return date('M j, Y', strtotime($date));
}

function format_datetime(string $date): string {
    return date('M j, Y g:i A', strtotime($date));
}

function format_datetime_tz(string $date, string $tz = 'America/New_York'): string {
    try {
        $dt = new DateTime($date, new DateTimeZone('America/New_York'));
        $dt->setTimezone(new DateTimeZone($tz));
        return $dt->format('M j, Y g:i A T');
    } catch (Exception $e) {
        return date('M j, Y g:i A', strtotime($date));
    }
}

function status_badge(string $status): string {
    $classes = [
        'submitted' => 'badge-gray',
        'open' => 'badge-blue',
        'passed' => 'badge-green',
        'failed' => 'badge-red',
        'rejected' => 'badge-orange',
    ];
    $cls = $classes[$status] ?? 'badge-gray';
    return '<span class="badge ' . $cls . '">' . e(ucfirst($status)) . '</span>';
}

function type_badge(string $type): string {
    $cls = $type === 'amendment' ? 'badge-purple' : 'badge-teal';
    return '<span class="badge ' . $cls . '">' . e(ucfirst($type)) . '</span>';
}

function get_championship_end_from_data(string $league_key): ?string {
    if (!defined('DATA_DIR')) return null;
    $path = DATA_DIR . "league_{$league_key}.json";
    if (!file_exists($path)) return null;
    $data = json_decode(file_get_contents($path), true);
    $periods = $data['schedule_meta']['periods'] ?? [];
    $latest_end = null;
    foreach ($periods as $p) {
        if (!empty($p['is_playoff']) && !empty($p['end'])) {
            if (!$latest_end || $p['end'] > $latest_end) {
                $latest_end = $p['end'];
            }
        }
    }
    return $latest_end ? ($latest_end . ' 23:59:59') : null;
}

function get_trade_deadlines(): array {
    $rows = db()->query('SELECT league_key, deadline, championship_end FROM trade_deadlines')->fetchAll();
    $deadlines = [];
    foreach ($rows as $r) {
        // Auto-pull championship end from scraper data if not manually set
        $champ_end = $r['championship_end'];
        if (!$champ_end) {
            $champ_end = get_championship_end_from_data($r['league_key']);
        }
        $deadlines[$r['league_key']] = [
            'deadline' => $r['deadline'],
            'championship_end' => $champ_end,
        ];
    }
    return $deadlines;
}

function is_league_trade_locked(string $league_key): bool {
    static $deadlines = null;
    if ($deadlines === null) $deadlines = get_trade_deadlines();
    $dl = $deadlines[$league_key] ?? null;
    if (!$dl || !$dl['deadline']) return false;
    $now = time();
    $deadline = strtotime($dl['deadline']);
    $champ_end = $dl['championship_end'] ? strtotime($dl['championship_end']) : null;
    // Locked between deadline and championship end
    if ($now >= $deadline) {
        // No championship end detected = season already ended and rolled over → unlocked
        if (!$champ_end) return false;
        if ($now <= $champ_end) return true;
    }
    return false;
}

function trade_status_badge(string $status): string {
    $map = [
        'pending_acceptance' => ['badge-gray', 'Pending Acceptance'],
        'pending_review'     => ['badge-blue', 'Pending Review'],
        'approved'           => ['badge-green', 'Approved'],
        'processed'          => ['badge-green', 'Processed'],
        'rejected'           => ['badge-red', 'Rejected'],
        'cancelled'          => ['badge-orange', 'Cancelled'],
    ];
    [$cls, $label] = $map[$status] ?? ['badge-gray', ucfirst($status)];
    return '<span class="badge ' . $cls . '">' . e($label) . '</span>';
}

function asset_type_badge_class(string $type): string {
    return match ($type) {
        'player' => 'badge-blue',
        'pick'   => 'badge-purple',
        'faab'   => 'badge-teal',
        default  => 'badge-gray',
    };
}

function format_trade_summary(PDO $pdo, int $trade_id): string {
    $sides = $pdo->prepare('
        SELECT ts.team_key, u.display_name
        FROM trade_sides ts
        JOIN users u ON ts.user_id = u.id
        WHERE ts.trade_id = :tid
        ORDER BY ts.is_submitter DESC, ts.id
    ');
    $sides->execute([':tid' => $trade_id]);
    $sides = $sides->fetchAll();

    $html = '';
    foreach ($sides as $side) {
        $assets = $pdo->prepare('
            SELECT ta.asset_name, ta.asset_type
            FROM trade_assets ta
            JOIN trade_sides ts ON ta.trade_side_id = ts.id
            WHERE ts.trade_id = :tid AND ts.team_key = :tk
        ');
        $assets->execute([':tid' => $trade_id, ':tk' => $side['team_key']]);
        $items = $assets->fetchAll();

        $html .= '<p><strong>' . e($side['display_name']) . '</strong> (' . e(team_name($side['team_key'])) . ') acquires:<br>';
        foreach ($items as $item) {
            $html .= '&bull; ' . e($item['asset_name']) . ' <em>(' . e($item['asset_type']) . ')</em><br>';
        }
        $html .= '</p>';
    }
    return $html;
}

function redirect(string $url): void {
    header('Location: ' . $url);
    exit;
}

function flash(string $type, string $msg): void {
    $_SESSION['flash'] = ['type' => $type, 'msg' => $msg];
}

function render_flash(): string {
    if (empty($_SESSION['flash'])) return '';
    $f = $_SESSION['flash'];
    unset($_SESSION['flash']);
    return '<div class="alert alert-' . e($f['type']) . '">' . e($f['msg']) . '</div>';
}
