-- Trade Portal: 3 new tables
-- Run against your portal database

CREATE TABLE trades (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    submitted_by INT UNSIGNED NOT NULL,
    status ENUM('pending_acceptance','pending_review','approved','processed','rejected','cancelled') NOT NULL DEFAULT 'pending_acceptance',
    notes TEXT,
    reject_reason TEXT,
    reviewed_by INT UNSIGNED,
    reviewed_at DATETIME,
    processed_by INT UNSIGNED,
    processed_at DATETIME,
    accepted_at DATETIME,
    imessage_sent TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES users(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id),
    FOREIGN KEY (processed_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE trade_sides (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    trade_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    team_key VARCHAR(50) NOT NULL,
    is_submitter TINYINT(1) NOT NULL DEFAULT 0,
    accepted TINYINT(1) NOT NULL DEFAULT 0,
    accepted_at DATETIME,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_trade_user (trade_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE trade_assets (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    trade_side_id INT UNSIGNED NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    asset_type ENUM('player','pick','faab','other') NOT NULL DEFAULT 'player',
    FOREIGN KEY (trade_side_id) REFERENCES trade_sides(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
