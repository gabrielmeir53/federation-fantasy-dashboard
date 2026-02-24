<?php
/**
 * Federation Dashboard Scraper — Manual Trigger
 * ==============================================
 * Visit: https://yourdomain.com/trigger.php?token=YOUR_SECRET
 *
 * This kicks off the scraper immediately. Useful when you've
 * just made a trade or want fresh data before checking standings.
 *
 * Bookmark this URL on your phone for one-tap refresh.
 */

// ── CONFIGURATION ─────────────────────────────────────
$SECRET = 'CHANGE_THIS_TO_A_RANDOM_STRING';              // ← Set a strong random token
$SCRIPT = '/home/YOUR_CPANEL_USERNAME/scraper/run_scraper.sh';  // ← Update with your username
// ─────────────────────────────────────────────────────

// Security: check token
$token = isset($_GET['token']) ? $_GET['token'] : '';
if ($token !== $SECRET) {
    http_response_code(403);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!DOCTYPE html><html><body style="background:#0b1120;color:#c06060;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><div style="text-align:center"><h1>403</h1><p>Invalid or missing token.</p></div></body></html>';
    exit;
}

// Rate limit: no more than once per 2 minutes
$lockfile = sys_get_temp_dir() . '/fed_trigger.lock';
if (file_exists($lockfile) && (time() - filemtime($lockfile)) < 120) {
    $wait = 120 - (time() - filemtime($lockfile));
    header('Content-Type: text/html; charset=utf-8');
    echo '<!DOCTYPE html><html><body style="background:#0b1120;color:#f0c040;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0"><div style="text-align:center"><h1>&#9203;</h1><p>Scraper ran recently. Try again in ' . $wait . ' seconds.</p><p><a href="/" style="color:#f0c040">&larr; Back to Dashboard</a></p></div></body></html>';
    exit;
}
touch($lockfile);

// Run the scraper in the background
$logfile = dirname($SCRIPT) . '/trigger.log';
$cmd = "bash $SCRIPT >> $logfile 2>&1 &";
exec($cmd);

// Show success page
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Federation — Scraper Triggered</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b1120;color:#e4e8f0;font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;height:100vh}
.card{text-align:center;background:#111827;border:1px solid #2d3a50;border-radius:12px;padding:2.5rem;max-width:420px}
h1{font-size:2rem;margin-bottom:.5rem}
.spinner{width:40px;height:40px;border:3px solid #2d3a50;border-top-color:#f0c040;border-radius:50%;animation:spin .8s linear infinite;margin:1.5rem auto}
@keyframes spin{to{transform:rotate(360deg)}}
p{color:#8892a8;font-size:.9rem;line-height:1.6;margin-top:.5rem}
.note{font-size:.78rem;color:#556078;margin-top:1.2rem;padding-top:.8rem;border-top:1px solid #2d3a50}
a{color:#f0c040;text-decoration:none}
a:hover{text-decoration:underline}
.btn{display:inline-block;margin-top:1.2rem;padding:.5rem 1.5rem;background:#f0c040;color:#0b1120;border-radius:6px;font-weight:600;font-size:.85rem}
.btn:hover{background:#ffd700;text-decoration:none}
</style>
</head>
<body>
<div class="card">
  <h1>&#9889; Scraper Triggered</h1>
  <div class="spinner"></div>
  <p>The scraper is running in the background.<br>Data will refresh in 1–3 minutes.</p>
  <a href="/" class="btn">&larr; Back to Dashboard</a>
  <div class="note">
    Tip: Bookmark this URL for one-tap refresh.<br>
    Rate limited to once per 2 minutes.
  </div>
</div>
<script>
// Auto-redirect to dashboard after 90 seconds
setTimeout(function(){ window.location.href = '/'; }, 90000);
</script>
</body>
</html>
