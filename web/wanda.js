/* Wanda in the browser: same algorithm as src/wanda (kept identical by tests/test_web_parity.py). */
(function (root) {
  'use strict';
  var DIG = ['ng', 'ny', 'dh', 'th', 'kh', 'sy'];
  function norm(w) { return w.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/['\u2019]/g, ''); }
  function units(w) {
    w = norm(w); var u = [], i = 0;
    while (i < w.length) { if (DIG.indexOf(w.substr(i, 2)) >= 0) { u.push(w.substr(i, 2)); i += 2; } else { u.push(w[i]); i++; } }
    return u;
  }
  var SUB = {};
  [['a','o',.35],['u','o',.5],['e','i',.5],['d','dh',.2],['t','th',.2],['dh','th',.5],['k','kh',.2],['s','sy',.3],['b','p',.5],['d','t',.5],['g','k',.5],['c','j',.5]]
    .forEach(function (r) { SUB[r[0] + '|' + r[1]] = r[2]; SUB[r[1] + '|' + r[0]] = r[2]; });
  function sub(a, b) { return a === b ? 0 : (SUB[a + '|' + b] !== undefined ? SUB[a + '|' + b] : 1); }
  function indel(u) { return u === 'h' || u === 'k' ? 0.3 : 1; }
  function dist(a, b) {
    var prev = [0], j, i;
    for (j = 0; j < b.length; j++) prev.push(prev[prev.length - 1] + indel(b[j]));
    for (i = 0; i < a.length; i++) {
      var cur = [prev[0] + indel(a[i])];
      for (j = 1; j <= b.length; j++) cur.push(Math.min(prev[j] + indel(a[i]), cur[j - 1] + indel(b[j - 1]), prev[j - 1] + sub(a[i], b[j - 1])));
      prev = cur;
    }
    return prev[prev.length - 1];
  }
  function similarity(a, b) {
    var ua = units(a), ub = units(b), n = Math.max(ua.length, ub.length);
    return n === 0 ? 1 : Math.max(0, 1 - dist(ua, ub) / n);
  }
  function matchCase(o, r) {
    if (o.length > 1 && o === o.toUpperCase() && o !== o.toLowerCase()) return r.toUpperCase();
    if (o[0] !== o[0].toLowerCase()) return r.charAt(0).toUpperCase() + r.slice(1);
    return r;
  }
  function uniq(list) { return list.filter(function (x, i) { return list.indexOf(x) === i; }); }

  function create(data, opts) {
    data = data || root.WANDA_DATA; opts = opts || {};
    var minConf = opts.minConfidence !== undefined ? opts.minConfidence : 0.75;
    var fuzzy = opts.fuzzy !== false, ratio = 0.34;
    var index = new Map(), phr = new Map(), maxPhrase = 1, TOK = /\p{L}+(?:['\u2019]\p{L}+)*/gu;
    data.entries.forEach(function (r) {
      var e = { form: r[0], register: r[1], dialect: r[2], indonesian: r[3], status: r[4] };
      var keys = [r[0]].concat((r[5] || '').split(',').map(function (v) { return v.trim(); }).filter(Boolean));
      keys.forEach(function (k) {
        var t = (k.match(TOK) || []).map(norm);
        if (t.length >= 2) {
          var pk = t.join(' '); if (!phr.has(pk)) phr.set(pk, []); if (phr.get(pk).indexOf(e) < 0) phr.get(pk).push(e);
          maxPhrase = Math.max(maxPhrase, t.length);
        } else {
          k = norm(k); if (!index.has(k)) index.set(k, []); if (index.get(k).indexOf(e) < 0) index.get(k).push(e);
        }
      });
    });
    var prot = new Set(data.protected.map(norm)); index.forEach(function (_, k) { prot.delete(k); });
    var forms = Array.from(index.keys()), formUnits = forms.map(units);

    function result(word, kind, score, hits) {
      var gl = uniq(hits.map(function (h) { return h.indonesian; }));
      var res = { original: word, kind: kind, score: score, entry: hits[0], alternatives: gl.length > 1 ? hits.slice(1) : [], applied: score >= minConf && gl.length === 1 };
      res.output = res.applied ? matchCase(word, hits[0].indonesian) : word; return res;
    }
    function word(w) {
      var n = norm(w), hits = index.get(n);
      if (hits) return result(w, 'exact', 1, hits);
      if (prot.has(n)) return { original: w, kind: 'protected', score: 1, entry: null, alternatives: [], applied: false, output: w };
      var u = units(w);
      if (fuzzy && u.length >= 3) {
        var best = null, bc = null, tied = [];
        for (var i = 0; i < forms.length; i++) {
          var c = dist(u, formUnits[i]);
          if (c > ratio * Math.max(u.length, formUnits[i].length)) continue;
          if (best === null || c < bc - 1e-9) { best = forms[i]; bc = c; tied = [forms[i]]; }
          else if (Math.abs(c - bc) <= 1e-9) tied.push(forms[i]);
        }
        if (best !== null) {
          var res = result(w, 'fuzzy', similarity(w, best), index.get(best));
          var all = []; tied.forEach(function (t) { all = all.concat(index.get(t)); });
          if (uniq(all.map(function (e) { return e.indonesian; })).length > 1) { res.alternatives = all; res.applied = false; res.output = w; }
          return res;
        }
      }
      return { original: w, kind: 'unknown', score: 0, entry: null, alternatives: [], applied: false, output: w };
    }
    var RE = /\p{L}+(?:['\u2019]\p{L}+)*/gu;
    function analyze(text) {
      var ms = [], m; RE.lastIndex = 0;
      while ((m = RE.exec(text)) !== null) ms.push({ s: m[0], i: m.index });
      var out = [], i = 0, r;
      while (i < ms.length) {
        var done = false;
        for (var L = Math.min(maxPhrase, ms.length - i); L >= 2 && !done; L--) {
          var ok = true;
          for (var k = 0; k < L - 1; k++) { if (text.slice(ms[i + k].i + ms[i + k].s.length, ms[i + k + 1].i).trim() !== '') { ok = false; break; } }
          if (!ok) continue;
          var hits = phr.get(ms.slice(i, i + L).map(function (x) { return norm(x.s); }).join(' '));
          if (hits) {
            var st = ms[i].i, en = ms[i + L - 1].i + ms[i + L - 1].s.length;
            r = result(text.slice(st, en), 'phrase', 1, hits); r.start = st; r.end = en; out.push(r); i += L; done = true;
          }
        }
        if (!done) { r = word(ms[i].s); r.start = ms[i].i; r.end = ms[i].i + ms[i].s.length; out.push(r); i++; }
      }
      return out;
    }
    function normalize(text) {
      var out = '', last = 0;
      analyze(text).forEach(function (r) { out += text.slice(last, r.start) + r.output; last = r.end; });
      return out + text.slice(last);
    }
    function llmContext(text) {
      var toks = analyze(text), c = '[STT transcript, may contain Javanese or dialect words]: ' + text + '\n[Probable Indonesian meaning]: ' + normalize(text);
      var notes = toks.filter(function (t) { return t.applied; }).map(function (t) { return t.original + ' -> ' + t.output + ' (' + t.entry.register + ', ' + t.entry.dialect + ', ' + t.kind + ' ' + t.score.toFixed(2) + ')'; });
      var amb = toks.filter(function (t) { return t.alternatives.length; }).map(function (t) { return t.original + ': ambiguous between ' + uniq([t.entry].concat(t.alternatives).map(function (e) { return e.indonesian; })).sort().join(', '); });
      if (notes.length) c += '\n[Rewrites]: ' + notes.join('; ');
      if (amb.length) c += '\n[Ambiguous, check context]: ' + amb.join('; ');
      return c;
    }
    return { analyze: analyze, normalize: normalize, llmContext: llmContext, size: data.entries.length };
  }
  var api = { create: create };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.WANDA = api;
})(typeof window !== 'undefined' ? window : globalThis);
