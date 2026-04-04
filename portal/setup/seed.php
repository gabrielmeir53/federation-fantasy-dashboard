<?php
/**
 * Federation Portal — Seed Data
 * Run after schema.sql and migration_trades.sql.
 *
 * Usage: php seed.php
 *
 * Creates 12 members (3 commissioners + 9 members) with default
 * password "changeme" (forced password change on first login).
 *
 * Customize the team keys, display names, and emails below to match
 * your league. Team keys must match the keys in functions.php.
 */

require_once __DIR__ . '/../includes/config.php';
require_once __DIR__ . '/../includes/db.php';

$hash = password_hash('changeme', PASSWORD_DEFAULT);

$users = [
    // Commissioners
    ['owner1',  $hash, 'Owner One',     'team_01', 'commissioner', 'owner1@example.com',  'Owner 1'],
    ['owner2',  $hash, 'Owner Two',     'team_02', 'commissioner', 'owner2@example.com',  'Owner 2'],
    ['owner3',  $hash, 'Owner Three',   'team_03', 'commissioner', 'owner3@example.com',  'Owner 3'],
    // Members
    ['owner4',  $hash, 'Owner Four',    'team_04', 'member', 'owner4@example.com',  'Owner 4'],
    ['owner5',  $hash, 'Owner Five',    'team_05', 'member', 'owner5@example.com',  'Owner 5'],
    ['owner6',  $hash, 'Owner Six',     'team_06', 'member', 'owner6@example.com',  'Owner 6'],
    ['owner7',  $hash, 'Owner Seven',   'team_07', 'member', 'owner7@example.com',  'Owner 7'],
    ['owner8',  $hash, 'Owner Eight',   'team_08', 'member', 'owner8@example.com',  'Owner 8'],
    ['owner9',  $hash, 'Owner Nine',    'team_09', 'member', 'owner9@example.com',  'Owner 9'],
    ['owner10', $hash, 'Owner Ten',     'team_10', 'member', 'owner10@example.com', 'Owner 10'],
    ['owner11', $hash, 'Owner Eleven',  'team_11', 'member', 'owner11@example.com', 'Owner 11'],
    ['owner12', $hash, 'Owner Twelve',  'team_12', 'member', 'owner12@example.com', 'Owner 12'],
];

$stmt = db()->prepare('INSERT INTO users (username, password_hash, display_name, team_key, role, email, preferred_name) VALUES (?, ?, ?, ?, ?, ?, ?)');
foreach ($users as $u) {
    $stmt->execute($u);
    echo "Created: {$u[0]} ({$u[4]})\n";
}

// Seed trade deadlines
$leagues = [
    ['fed_fl', 'FedFL'],
    ['fed_ba', 'FedBA'],
    ['fed_hl', 'FedHL'],
    ['fed_lb', 'FedLB'],
];
$stmt = db()->prepare('INSERT INTO trade_deadlines (league_key, league_name) VALUES (?, ?)');
foreach ($leagues as $l) {
    $stmt->execute($l);
}
echo "Trade deadline rows created.\n";

echo "\nDone! All users have password: changeme\n";
echo "They will be prompted to change it on first login.\n";
