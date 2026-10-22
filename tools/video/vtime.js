// Virtual clock for frame-exact capture: rAF, performance.now, timers and Web Animations all follow
// window.__advance(ms) instead of the wall clock, so every captured frame is evenly spaced.
(function () {
  var vnow = 0, rafQ = [], rafId = 0, timers = [], timerId = 0, seed = 20261022;
  var realNow = performance.now.bind(performance);
  var t0Date = Date.now();
  performance.now = function () { return vnow; };
  Date.now = function () { return t0Date + vnow; };
  Math.random = function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  window.requestAnimationFrame = function (cb) { rafQ.push({ id: ++rafId, cb: cb }); return rafId; };
  window.cancelAnimationFrame = function (id) { rafQ = rafQ.filter(function (r) { return r.id !== id; }); };
  function addTimer(fn, ms, args, repeat) { var id = ++timerId; timers.push({ id: id, at: vnow + Math.max(0, +ms || 0), fn: fn, args: args, every: repeat ? Math.max(1, +ms || 0) : 0 }); return id; }
  window.setTimeout = function (fn, ms) { return addTimer(fn, ms, Array.prototype.slice.call(arguments, 2), false); };
  window.setInterval = function (fn, ms) { return addTimer(fn, ms, Array.prototype.slice.call(arguments, 2), true); };
  window.clearTimeout = window.clearInterval = function (id) { timers = timers.filter(function (t) { return t.id !== id; }); };
  var tracked = new WeakSet();
  function syncAnimations() {
    var list = document.getAnimations ? document.getAnimations() : [];
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      if (!tracked.has(a)) { tracked.add(a); a.__vstart = vnow; try { a.pause(); } catch (e) {} }
      var ct = vnow - a.__vstart, end = Infinity;
      try { end = a.effect.getComputedTiming().endTime; } catch (e) {}
      try { if (ct >= end && isFinite(end)) a.finish(); else a.currentTime = ct; } catch (e) {}
    }
  }
  window.__advance = function (ms) {
    var target = vnow + ms;
    for (var guard = 0; guard < 500; guard++) {
      timers.sort(function (x, y) { return x.at - y.at; });
      var t = timers[0]; if (!t || t.at > target) break;
      vnow = Math.max(vnow, t.at);
      if (t.every) t.at += t.every; else timers.shift();
      try { typeof t.fn === 'function' ? t.fn.apply(null, t.args) : eval(t.fn); } catch (e) { console.error(e); }
    }
    vnow = target;
    var q = rafQ; rafQ = [];
    for (var i = 0; i < q.length; i++) { try { q[i].cb(vnow); } catch (e) { console.error(e); } }
    syncAnimations();
    return vnow;
  };
  window.__vnow = function () { return vnow; };
})();
