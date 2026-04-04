  </div>
</main>

<footer class="footer">
  <div class="container">
    &copy; <?= date('Y') ?> Federation &middot; <a href="<?= MAIN_SITE_URL ?>">Main Site</a> &middot; <a href="<?= MAIN_SITE_URL ?>/constitution.html">Terms &amp; Conditions</a>
  </div>
</footer>

<script>
(function() {
  var btn = document.querySelector('.nav-hamburger');
  var links = document.querySelector('.nav-links');
  if (!btn || !links) return;
  btn.addEventListener('click', function() {
    btn.classList.toggle('open');
    links.classList.toggle('open');
  });
})();
</script>
</body>
</html>
