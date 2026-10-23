// Links between the three ParkFlow pages: landing (home), command centre and driver app.
// On GitHub Pages, a local copy, or the landing artifact (which carries all three pages), the pages sit
// side by side, so links stay relative. In the stand-alone command-centre and driver artifacts there is
// no sibling page, so links go to the published artifacts instead (opening in a new tab).
(function () {
  var PAGE = window.PF_PAGE || '';
  var FILE = { home: 'index.html', command: 'command.html', driver: 'driver.html' };
  var ART = {
    home: 'https://claude.ai/artifact/8THudTk6iUnNwCDdYnVpdi',
    command: 'https://claude.ai/artifact/W7c5u2NbaxPYT3198u8oPu',
    driver: 'https://claude.ai/artifact/DMcbMgGuhv7SJkQ1hqoEWR'
  };
  var TITLE = { command: 'ParkFlow Command Centre', driver: 'ParkFlow Driver' };
  var local = location.protocol === 'file:' || /github\.io$/.test(location.hostname) || location.hostname === 'localhost';

  function fix(a) {
    var k = a.getAttribute('data-site');
    if (!FILE[k]) return;
    if (local) { a.setAttribute('href', FILE[k]); a.removeAttribute('target'); }
    else { a.setAttribute('href', ART[k]); a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener'); }
  }
  function fixAll() { document.querySelectorAll('a[data-site]').forEach(fix); }
  // the driver app re-renders its sheets, so also settle each link just before it is used
  ['pointerdown', 'focusin', 'mouseover'].forEach(function (ev) {
    document.addEventListener(ev, function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[data-site]') : null;
      if (a) fix(a);
    }, true);
  });
  window.pfSiteHref = function (k) { return local ? FILE[k] : ART[k]; };

  function probe() {
    // Is the other app published next to this page? Read the start of it and check its title.
    var other = PAGE === 'driver' ? 'command' : 'driver';
    if (local || !window.fetch) { fixAll(); return; }
    var ctl = window.AbortController ? new AbortController() : null;
    fetch(new URL(FILE[other], location.href).href, { cache: 'force-cache', signal: ctl ? ctl.signal : undefined })
      .then(function (r) {
        if (!r.ok || !r.body || !r.body.getReader) return r.ok ? r.text() : '';
        var rd = r.body.getReader(), dec = new TextDecoder(), txt = '';
        function pump() {
          return rd.read().then(function (c) {
            if (c.done) return txt;
            txt += dec.decode(c.value, { stream: true });
            if (txt.length > 6000) { try { ctl && ctl.abort(); } catch (e) {} return txt; }
            return pump();
          });
        }
        return pump();
      })
      .then(function (txt) { if (txt && txt.indexOf('<title>' + TITLE[other] + '</title>') !== -1) local = true; fixAll(); })
      .catch(function () { fixAll(); });
  }
  fixAll();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { fixAll(); probe(); });
  else probe();
})();
