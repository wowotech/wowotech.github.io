/* 站内全文搜索：两层索引，解决「5.8MB 整包下载完才能开始查」的等待。
 *   1) /search-head.json  标题/分类/标签/摘要，很小，先出「标题命中」结果
 *   2) /search-body/N.json 正文纯文本分块，并行加载（失败自动重试 3 次），
 *      到齐后自动升级为全文检索
 * 多个关键词按「都要出现」（AND）；中文按子串匹配，不做分词。 */
(function () {
  var statusEl = document.getElementById('status');
  var resultsEl = document.getElementById('results');
  var input = document.getElementById('q');
  var form = document.getElementById('search-form');
  var MAX = 40;
  var RETRY = 3;

  var entries = null;   // 标题层
  var chunks = null;    // 正文分块 [from, to)
  var bodies = null;    // 正文原文（用于摘要）
  var lower = null;     // 小写正文（用于匹配，构建一次）
  var loaded = 0;
  var hasFull = false;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function mark(escaped, terms) {
    terms.forEach(function (t) {
      if (t) escaped = escaped.replace(new RegExp(escRe(t), 'gi'), function (m) {
        return '<mark>' + m + '</mark>';
      });
    });
    return escaped;
  }
  function countIn(hay, needle, cap) {
    var n = 0, i = hay.indexOf(needle);
    while (i >= 0 && n < cap) {
      n++;
      i = hay.indexOf(needle, i + needle.length);
    }
    return n;
  }
  /* 空洞（某分块彻底加载失败）给空串：对应文章只做标题匹配，绝不报错 */
  function lowerBodies() {
    if (!lower) {
      lower = bodies.map(function (b) { return b ? b.toLowerCase() : ''; });
    }
    return lower;
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
    var lows = hasFull ? lowerBodies() : null;
    var hits = [];
    for (var i = 0; i < entries.length; i++) {
      var it = entries[i];
      var body = lows ? lows[i] : null;
      var score = 0, ok = true;
      for (var j = 0; j < terms.length; j++) {
        var t = terms[j];
        var inTitle = it.lt.indexOf(t) >= 0;
        var inTags = it.lg.indexOf(t) >= 0;
        var inCat = it.lc.indexOf(t) >= 0;
        var inSum = it.ls.indexOf(t) >= 0;
        var n = body ? countIn(body, t, 16) : 0;
        if (!inTitle && !inTags && !inCat && !inSum && !n) { ok = false; break; }
        score += (inTitle ? 30 : 0) + (inTags ? 8 : 0) + (inCat ? 5 : 0) + (inSum ? 6 : 0)
               + Math.min(n, 15);
      }
      if (ok && score > 0) hits.push([score, i]);
    }
    hits.sort(function (a, b) { return b[0] - a[0]; });
    return hits;
  }

  function render(terms) {
    if (!terms.length) {
      resultsEl.innerHTML = '';
      statusEl.textContent = hasFull
        ? '就绪：可全文检索 ' + entries.length + ' 篇（文章、页面与讨论区存档）。'
        : '已载入 ' + entries.length + ' 篇的标题索引；正文索引载入中（'
          + loaded + '/' + chunks.length + '）……';
      return;
    }
    var hits = search(terms);
    if (hasFull) {
      statusEl.textContent = hits.length
        ? '全文命中 ' + hits.length + ' 篇，显示前 ' + Math.min(hits.length, MAX) + ' 篇。'
        : '全文没有匹配「' + terms.join(' ') + '」的内容。可以换更短的关键词试试。';
    } else {
      statusEl.textContent = hits.length
        ? '快速命中 ' + hits.length + ' 篇（标题/摘要）；正文索引载入中（'
          + loaded + '/' + chunks.length + '），完成后结果自动更新。'
        : '正文索引载入中（' + loaded + '/' + chunks.length + '）……';
    }
    resultsEl.innerHTML = hits.slice(0, MAX).map(function (h) {
      var idx = h[1], it = entries[idx];
      var src = (hasFull && bodies[idx]) ? bodies[idx] : it.s;
      return '<li><a class="r-title" href="' + esc(it.u) + '">' + mark(esc(it.t), terms) + '</a>' +
             '<span class="muted small">' + esc([it.c, it.d].filter(Boolean).join(' · ')) + '</span>' +
             '<p class="r-snippet">' + snippet(src, terms) + '</p></li>';
    }).join('');
  }

  function run() {
    var q = (input.value || '').trim().toLowerCase();
    render(q ? q.split(/\s+/).filter(Boolean) : []);
  }

  function fetchChunk(ck, attempt, bodyUrl) {
    return fetch(bodyUrl)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (texts) {
        for (var j = 0; j < texts.length; j++) bodies[ck.from + j] = texts[j];
      })
      .catch(function (e) {
        if (attempt < RETRY) {
          return new Promise(function (res) { setTimeout(res, 700 * (attempt + 1)); })
            .then(function () { return fetchChunk(ck, attempt + 1, bodyUrl); });
        }
        window._chunkFail = (window._chunkFail || 0) + 1;   // 调试用：记录彻底失败的分块数
      });
  }

  function loadChunks() {
    var urls = (window.SEARCH_URLS && window.SEARCH_URLS.body) || null;
    chunks.forEach(function (ck, i) {
      fetchChunk(ck, 0, urls ? urls[i] : null).finally(function () {
        loaded++;
        if (loaded === chunks.length) {
          lowerBodies();          // 有防护：空洞按空串处理，不会抛错
          hasFull = true;
          run();
        }
      });
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var q = (input.value || '').trim();
    history.replaceState(null, '', '/search/' + (q ? '?q=' + encodeURIComponent(q) : ''));
    run();
  });
  input.addEventListener('input', function () {
    clearTimeout(input._t);
    input._t = setTimeout(run, 160);
  });

  fetch((window.SEARCH_URLS && window.SEARCH_URLS.head) || '/search-head.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      entries = data.entries.map(function (d) {
        return { u: d.u, t: d.t, c: d.c || '', g: d.g || [], d: d.d, s: d.s || '',
                 lt: d.t.toLowerCase(), lg: (d.g || []).join(' ').toLowerCase(),
                 lc: (d.c || '').toLowerCase(), ls: (d.s || '').toLowerCase() };
      });
      chunks = data.chunks;
      bodies = new Array(entries.length);
      var qs = new URLSearchParams(location.search).get('q');
      if (qs) input.value = qs;
      run();
      loadChunks();
    })
    .catch(function (e) {
      statusEl.textContent = ('索引载入失败：' + ((e && e.stack) || e)).slice(0, 600);
    });
})();
