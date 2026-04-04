-- Federation Portal — Database Schema
-- Run this first, then migration_trades.sql, then seed.php

CREATE TABLE users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    preferred_name VARCHAR(50) DEFAULT NULL,
    email VARCHAR(255) DEFAULT NULL,
    phone VARCHAR(30) DEFAULT NULL,
    team_key VARCHAR(30) DEFAULT NULL,
    role ENUM('commissioner','member') NOT NULL DEFAULT 'member',
    must_change_password TINYINT(1) NOT NULL DEFAULT 1,
    notify_email TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL,
    last_login_tz VARCHAR(50) DEFAULT NULL,
    telegram_chat_id VARCHAR(50) DEFAULT NULL,
    timezone VARCHAR(50) DEFAULT 'America/New_York'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE memos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    author_id INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL,
    FOREIGN KEY (author_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE proposals (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    submitted_by INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    proposal_type ENUM('amendment','rule') NOT NULL,
    status ENUM('submitted','open','passed','failed','rejected') NOT NULL DEFAULT 'submitted',
    emergency TINYINT(1) NOT NULL DEFAULT 0,
    file_path VARCHAR(255) DEFAULT NULL,
    file_name VARCHAR(255) DEFAULT NULL,
    opened_by INT UNSIGNED DEFAULT NULL,
    opened_at DATETIME DEFAULT NULL,
    closed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES users(id),
    FOREIGN KEY (opened_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE votes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    vote ENUM('yes','no','abstain') NOT NULL,
    voted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_vote (proposal_id, user_id),
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- See migration_trades.sql for trade tables
-- See seed.php for initial data population
