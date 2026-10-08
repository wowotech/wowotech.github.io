/* 站内全文搜索：索引是构建时生成的 /search-index.json，纯前端过滤，无后端。
   词之间按「都要出现」处理（AND）；中文按子串匹配，不做分词。 */
(function () {
  var statusEl = document.getElementById('status');
  var resultsEl = document.getElementById('results');
  var input = document.getElementById('q');
  var form = document.getElementById('search-form');
  var INDEX = null;
  var MAX = 40;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  function mark(escapedText, terms) {
    var out = escapedText;
    terms.forEach(function (t) {
      if (!t) return;
      out = out.replace(new RegExp(escRe(t), 'gi'), function (m) { return '<mark>' + m + '</mark>'; });
    });
    return out;
  }

  function snippet(text, terms) {
    var low = text.toLowerCase(), pos = -1;
    terms.forEach(function (t) {
      var i = low.indexOf(t);
      if (i >= 0 && (pos < 0 || i < pos)) pos = i;
    });
    if (pos < 0) return esc(text.slice(0, 140)) + '…';
    var start = Math.max(0, pos - 45);
    return (start ? '…' : '') + mark(esc(text.slice(start, start + 170)), terms) + '…';
  }

  function search(terms) {
    var hits = [];
    for (var i = 0; i < INDEX.length; i++) {
      var it = INDEX[i];
      var title = it.t.toLowerCase();
      var tags = (it.g || []).join(' ').toLowerCase();
      var cat = (it.c || '').toLowerCase();
      var body = it.lx;   // 预先转小写，避免每次击键都重算 541 篇的正文
      var score = 0, ok = true;
      for (var j = 0; j < terms.length; j++) {
        var t = terms[j];
        var inTitle = title.indexOf(t) >= 0;
        var count = body.split(t).length - 1;
        if (!inTitle && !count && tags.indexOf(t) < 0 && cat.indexOf(t) < 0) { ok = false; break; }
        score += (inTitle ? 30 : 0) + Math.min(count, 15);
        if (tags.indexOf(t) >= 0) score += 8;
        if (cat.indexOf(t) >= 0) score += 5;
      }
      if (ok && score > 0) hits.push([score, it]);
    }
    hits.sort(function (a, b) { return b[0] - a[0]; });
    return hits;
  }

  function render(terms) {
    if (!terms.length) {
      resultsEl.innerHTML = '';
      statusEl.textContent = '已载入 ' + INDEX.length + ' 篇的索引，输入关键词开始搜索。';
      return;
    }
    var hits = search(terms);
    statusEl.textContent = hits.length
      ? '命中 ' + hits.length + ' 篇，显示前 ' + Math.min(hits.length, MAX) + ' 篇。'
      : '没有匹配「' + terms.join(' ') + '」的内容。可以换更短的关键词试试。';
    resultsEl.innerHTML = hits.slice(0, MAX).map(function (h) {
      var it = h[1];
      var meta = [it.c, it.d].filter(Boolean).join(' · ');
      return '<li><a class="r-title" href="' + esc(it.u) + '">' + mark(esc(it.t), terms) + '</a>' +
             (meta ? '<span class="muted small">' + esc(meta) + '</span>' : '') +
             '<p class="r-snippet">' + snippet(it.x, terms) + '</p></li>';
    }).join('');
  }

  function run() {
    var q = (input.value || '').trim().toLowerCase();
    render(q ? q.split(/\s+/).filter(Boolean) : []);
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    history.replaceState(null, '', '/search/' + (input.value.trim() ? '?q=' + encodeURIComponent(input.value.trim()) : ''));
    run();
  });
  input.addEventListener('input', function () {
    clearTimeout(input._t);
    input._t = setTimeout(run, 180);
  });

  fetch('/search-index.json').then(function (r) { return r.json(); }).then(function (data) {
    INDEX = data.map(function (d) {
      return { u: d.u, t: d.t, c: d.c, g: d.g, d: d.d, x: d.x, lx: d.x.toLowerCase() };
    });
    var qs = new URLSearchParams(location.search).get('q');
    if (qs) input.value = qs;
    run();
  }).catch(function () {
    statusEl.textContent = '索引载入失败，请刷新重试。';
  });
})();
