<?php
// Database
define('DB_HOST', 'localhost');
define('DB_NAME', 'your_database_name');
define('DB_USER', 'your_database_user');
define('DB_PASS', 'your_database_password');

// Site
define('SITE_NAME', 'Federation Portal');
define('SITE_URL', 'https://yourdomain.com/portal');
define('MAIN_SITE_URL', 'https://yourdomain.com');

// Data (path to scraper JSON output on server)
define('DATA_DIR', '/home/YOUR_CPANEL_USERNAME/yourdomain.com/data/');

// Advisor
define('ADVISOR_REPORTS_DIR', '/home/YOUR_CPANEL_USERNAME/repo/scraper/reports/');
define('GABE_USER_ID', 1); // Change to your admin user ID

// Telegram (set on production server)
define('TG_BOT_TOKEN', '');

// iMessage polling API (generate a random key for production)
define('IMESSAGE_API_KEY', '');

// Email
define('SMTP_HOST', 'smtp.gmail.com');
define('SMTP_PORT', 587);
define('SMTP_USER', 'your_email@yourdomain.com');
define('SMTP_PASS', 'your_app_password');
define('MAIL_FROM', 'Federation Portal <noreply@yourdomain.com>');
