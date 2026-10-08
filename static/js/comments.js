/* 评论流的客户端过滤：按关键词或作者筛，命中任何一个就算（OR）。 */
(function () {
  var input = document.getElementById('cfilter');
  var cards = Array.prototype.slice.call(document.querySelectorAll('#comment-stream .ccard'));
  var none = document.getElementById('cnone');
  if (!input || !cards.length) return;

  function apply() {
    var q = (input.value || '').trim().toLowerCase();
    var terms = q ? q.split(/\s+/).filter(Boolean) : [];
    var shown = 0;
    cards.forEach(function (card) {
      if (!terms.length) { card.hidden = false; shown++; return; }
      var hay = card.textContent.toLowerCase();
      var hit = terms.some(function (t) { return hay.indexOf(t) >= 0; });
      card.hidden = !hit;
      if (hit) shown++;
    });
    none.hidden = shown !== 0;
    if (shown !== cards.length) {
      input.setAttribute('aria-live', 'polite');
    }
  }

  var t;
  input.addEventListener('input', function () {
    clearTimeout(t);
    t = setTimeout(apply, 120);
  });

  /* 支持 /comments/?q=workqueue 直接带过滤条件进来 */
  var qs = new URLSearchParams(location.search).get('q');
  if (qs) input.value = qs;
  apply();
})();
