<?php
$page_title = 'Proposals';
require_once __DIR__ . '/includes/auth.php';
$user = require_login();

$id = (int)($_GET['id'] ?? 0);
$stmt = db()->prepare('SELECT p.*, u.display_name AS submitter_name FROM proposals p JOIN users u ON p.submitted_by = u.id WHERE p.id = :id');
$stmt->execute([':id' => $id]);
$p = $stmt->fetch();
if (!$p) { http_response_code(404); die('Proposal not found.'); }

// Get votes
$votes_stmt = db()->prepare('SELECT v.*, u.display_name FROM votes v JOIN users u ON v.user_id = u.id WHERE v.proposal_id = :pid');
$votes_stmt->execute([':pid' => $id]);
$all_votes = $votes_stmt->fetchAll();
$vote_count = count($all_votes);
$yes_count = count(array_filter($all_votes, fn($v) => $v['vote'] === 'yes'));
$no_count = count(array_filter($all_votes, fn($v) => $v['vote'] === 'no'));
$abstain_count = count(array_filter($all_votes, fn($v) => $v['vote'] === 'abstain'));

// Current user's vote
$my_vote_stmt = db()->prepare('SELECT vote FROM votes WHERE proposal_id = :pid AND user_id = :uid');
$my_vote_stmt->execute([':pid' => $id, ':uid' => $user['id']]);
$my_vote = $my_vote_stmt->fetchColumn();

$needed = get_votes_needed($p['proposal_type'], (bool)$p['emergency']);
$is_closed = in_array($p['status'], ['passed', 'failed', 'rejected']);

require __DIR__ . '/includes/header.php';
?>

<p style="margin-bottom:1rem;"><a href="proposals.php">&larr; All Proposals</a></p>

<div class="card">
  <h1 style="margin-bottom:.3rem;"><?= e($p['title']) ?></h1>
  <div class="card-meta" style="margin-bottom:.4rem;">
    <?= type_badge($p['proposal_type']) ?> <?= status_badge($p['status']) ?>
    <?php if ($p['emergency']): ?><span class="badge badge-orange">Emergency</span><?php endif; ?>
  </div>
  <div class="card-meta" style="margin-bottom:1rem;">
    Submitted by <?= e($p['submitter_name']) ?> &middot; <?= format_datetime($p['created_at']) ?>
    <?php if ($p['opened_at']): ?> &middot; Opened <?= format_date($p['opened_at']) ?><?php endif; ?>
    <?php if ($p['closed_at']): ?> &middot; Closed <?= format_date($p['closed_at']) ?><?php endif; ?>
  </div>
  <?php if ($p['body']): ?>
  <div class="card-body" style="white-space:pre-wrap; margin-bottom:1rem;"><?= e($p['body']) ?></div>
  <?php endif; ?>

  <?php if (!empty($p['file_path'])): ?>
  <div style="margin-bottom:1.5rem;">
    <strong style="font-size:.85rem; color:var(--text-dim);">Attachment:</strong>
    <a href="<?= e($p['file_path']) ?>" target="_blank" class="btn btn-outline btn-sm" style="margin-left:.5rem;"><?= e($p['file_name']) ?></a>
  </div>
  <?php endif; ?>

  <?php if ($p['status'] === 'open'): ?>
    <div style="border-top:1px solid var(--border); padding-top:1rem;">
      <h2>Vote</h2>
      <p class="vote-tally"><?= $vote_count ?> of 12 votes cast &middot; <?= $needed ?> yes votes needed to pass</p>

      <?php if ($my_vote): ?>
        <p style="margin-top:.5rem;">You voted: <strong><?= e(ucfirst($my_vote)) ?></strong></p>
      <?php else: ?>
        <form method="post" action="vote.php">
          <?= csrf_field() ?>
          <input type="hidden" name="proposal_id" value="<?= $p['id'] ?>">
          <div class="vote-options">
            <label><input type="radio" name="vote" value="yes" required> Yes</label>
            <label><input type="radio" name="vote" value="no"> No</label>
            <label><input type="radio" name="vote" value="abstain"> Abstain</label>
          </div>
          <button type="submit" class="btn btn-primary btn-sm">Cast Vote</button>
        </form>
      <?php endif; ?>

      <?php if (is_commissioner()): ?>
        <form method="post" action="proposal_manage.php" style="margin-top:1rem;">
          <?= csrf_field() ?>
          <input type="hidden" name="id" value="<?= $p['id'] ?>">
          <button type="submit" name="action" value="close" class="btn btn-outline btn-sm" onclick="return confirm('Close voting and calculate result?');">Close Voting</button>
        </form>
      <?php endif; ?>
    </div>

  <?php elseif ($p['status'] === 'submitted'): ?>
    <?php if (is_commissioner()): ?>
    <div style="border-top:1px solid var(--border); padding-top:1rem;">
      <h2>Commissioner Action</h2>
      <p style="font-size:.9rem; color:var(--text-dim); margin-bottom:.8rem;">This proposal is awaiting commissioner review.</p>
      <form method="post" action="proposal_manage.php">
        <?= csrf_field() ?>
        <input type="hidden" name="id" value="<?= $p['id'] ?>">
        <div class="btn-row">
          <button type="submit" name="action" value="approve" class="btn btn-green btn-sm">Approve for Voting</button>
          <button type="submit" name="action" value="reject" class="btn btn-red btn-sm" onclick="return confirm('Reject this proposal?');">Reject</button>
        </div>
      </form>
    </div>
    <?php else: ?>
    <p style="color:var(--text-muted); font-style:italic; border-top:1px solid var(--border); padding-top:1rem;">This proposal is awaiting commissioner review.</p>
    <?php endif; ?>

  <?php elseif ($is_closed): ?>
    <div style="border-top:1px solid var(--border); padding-top:1rem;">
      <h2>Result</h2>
      <p class="vote-tally">
        <strong><?= $yes_count ?></strong> yes &middot;
        <strong><?= $no_count ?></strong> no &middot;
        <strong><?= $abstain_count ?></strong> abstain &middot;
        Threshold: <?= $needed ?>/12
      </p>
      <?php if ($vote_count > 0): ?>
      <div class="vote-bar" style="margin:.6rem 0;">
        <?php if ($yes_count): ?><div class="vote-bar-yes" style="width:<?= round($yes_count / 12 * 100) ?>%"></div><?php endif; ?>
        <?php if ($no_count): ?><div class="vote-bar-no" style="width:<?= round($no_count / 12 * 100) ?>%"></div><?php endif; ?>
        <?php if ($abstain_count): ?><div class="vote-bar-abstain" style="width:<?= round($abstain_count / 12 * 100) ?>%"></div><?php endif; ?>
      </div>
      <table class="vote-detail">
        <?php foreach ($all_votes as $v): ?>
        <tr>
          <td><?= e($v['display_name']) ?></td>
          <td><strong><?= e(ucfirst($v['vote'])) ?></strong></td>
        </tr>
        <?php endforeach; ?>
      </table>
      <?php endif; ?>
    </div>
  <?php endif; ?>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
