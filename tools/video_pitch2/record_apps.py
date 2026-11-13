"""Record the real driver app (docs/driver.html) and operator dashboard (docs/command.html) for the pitch film.
Virtual clock (tools/video/vtime.js), so every frame is evenly spaced.

Usage: python record_apps.py WORK [driver|command|all]
Writes WORK/drv/NNNN.jpg (390x844 @2x) + WORK/drv_meta.json (taps), WORK/cmd/NNNN.jpg (1920x1080 @1.5x) + WORK/cmd_meta.json (panel rects).
"""
import base64, json, math, pathlib, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
VT = (ROOT / 'tools' / 'video' / 'vtime.js').read_text()
FPS = 30
work = pathlib.Path(sys.argv[1]).resolve()
which = sys.argv[2] if len(sys.argv) > 2 else 'all'

CLICK_TEXT = r"""(t) => { const els = [...document.querySelectorAll('button,[role=button],a')].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  const e = els.find((x) => (x.innerText || x.getAttribute('aria-label') || '').trim().toLowerCase() === t.toLowerCase()) || els.find((x) => (x.innerText || '').toLowerCase().includes(t.toLowerCase()));
  if (!e) return null; const r = e.getBoundingClientRect(); e.click(); return [r.x + r.width / 2, r.y + r.height / 2, r.width, r.height]; }"""
PANEL = r"""(t) => { const all = [...document.querySelectorAll('h1,h2,h3,h4,div,span,b,p,button')].filter((e) => e.children.length < 4 && (e.innerText || '').trim().startsWith(t));
  const vis = all.filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }); if (!vis.length) return null;
  let e = vis[0]; while (e.parentElement && (e.getBoundingClientRect().width < 320 || e.getBoundingClientRect().height < 110)) e = e.parentElement;
  const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((v) => Math.round(v)); }"""


class Cap:
    def __init__(self, b, url, vp, dpr, mobile):
        self.ctx = b.new_context(viewport=vp, device_scale_factor=dpr, is_mobile=mobile, has_touch=mobile, color_scheme='light' if mobile else 'dark')
        self.pg = self.ctx.new_page(); self.pg.set_default_timeout(240000); self.errors = []
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        self.pg.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())  # Motion falls back to Web Animations, which follow the virtual clock
        self.pg.add_init_script(VT)
        self.pg.goto(url); self.cdp = self.ctx.new_cdp_session(self.pg)
    def adv(self, sec): self.pg.evaluate('(n) => { for (let i = 0; i < n; i++) __advance(1000 / 30); }', max(1, int(round(sec * FPS))))
    def shot(self, path, q):
        path.write_bytes(base64.b64decode(self.cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': q})['data']))


def record(c, out, seconds, actions, q):
    """actions: {frame: callable(frame) -> optional dict to log}"""
    out.mkdir(parents=True, exist_ok=True); log = []; t0 = time.time()
    for k in range(int(round(seconds * FPS))):
        for f in actions.get(k, []):
            r = f(k)
            if r: log.append({'f': k, **r})
        c.pg.evaluate('__advance(1000 / 30)')
        c.shot(out / f'{k:04d}.jpg', q)
        if k % 150 == 149: print(f'  {out.name} {k + 1} frames  {(time.time() - t0) / (k + 1):.2f}s/frame', flush=True)
    return log


def at(sec): return int(round(sec * FPS))


def driver(b):
    c = Cap(b, (ROOT / 'docs' / 'driver.html').as_uri(), {'width': 390, 'height': 844}, 2, True)
    c.adv(1.5)
    def tap(text, label):
        def f(k):
            r = c.pg.evaluate(CLICK_TEXT, text)
            print('  tap', text, r); return {'tap': label, 'xy': r}
        return f
    def set_time(k):
        r = c.pg.evaluate("""() => { const i = document.querySelector('input[type=time]'); if (!i) return null; const r = i.getBoundingClientRect();
            i.value = '12:00'; i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); return [r.x + r.width / 2, r.y + r.height / 2, r.width, r.height]; }""")
        print('  time', r); return {'tap': 'time', 'xy': r}
    scroll_el = """() => { const c = [...document.querySelectorAll('*')].filter((e) => { const s = getComputedStyle(e); return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 40; });
        c.sort((a, b) => b.clientHeight - a.clientHeight); return c[0] || document.scrollingElement; }"""
    def scroll(k):
        u = (k - at(11.8)) / (at(14.2) - at(11.8)); e = 0.5 - 0.5 * math.cos(math.pi * min(max(u, 0), 1))
        c.pg.evaluate(f'(y) => {{ const el = ({scroll_el})(); el.scrollTop = y; }}', round(e * 470))
    acts = {at(1.7): [tap('Reserve Parking', 'reserve')], at(3.3): [set_time], at(5.2): [tap('Confirm Booking', 'confirm')],
            at(10.0): [tap('View Priority Zone', 'zone')]}
    for k in range(at(11.8), at(14.3)): acts.setdefault(k, []).append(scroll)
    log = record(c, work / 'drv', 15.4, acts, 90)
    rects = c.pg.evaluate("() => { const e = [...document.querySelectorAll('*')].find((x) => (x.innerText || '').trim() === 'WXY 8812' && x.children.length === 0); return null; }")
    (work / 'drv_meta.json').write_text(json.dumps({'taps': log, 'size': [390, 844]}))
    print('driver done', len(log), 'events', 'errors', c.errors[:5]); c.ctx.close()


def command(b):
    c = Cap(b, (ROOT / 'docs' / 'command.html').as_uri(), {'width': 1920, 'height': 1080}, 1.5, False)
    c.adv(0.5)
    for _ in range(12):
        if c.pg.evaluate("(() => { const w = document.querySelector('#welcome'); return !w || w.hidden; })()"): break
        c.pg.evaluate("(() => { const e = document.querySelector('[data-welcome=\"close\"]'); if (e) e.click(); })()"); c.adv(0.3)
    c.pg.evaluate("(() => { const e = document.querySelector('[data-section=\"overview\"]'); if (e) e.click(); })()")
    c.adv(18)  # let the morning build up so the model and the log are busy
    print('  clock', c.pg.evaluate("(document.querySelector('#clock') || {}).innerText || ''"))
    meta = {}
    def panels(tag, names):
        def f(k):
            meta[tag] = {n: c.pg.evaluate(PANEL, n) for n in names}
            meta[tag]['canvas'] = c.pg.evaluate("() => { const v = [...document.querySelectorAll('canvas')].map((e) => e.getBoundingClientRect()).filter((r) => r.width > 300).sort((a, b) => b.width * b.height - a.width * a.height)[0]; return v ? [v.x, v.y, v.width, v.height].map(Math.round) : null; }")
            print('  panels', tag, meta[tag])
        return f
    def section(s):
        def f(k): c.pg.evaluate(f"(() => {{ const e = document.querySelector('[data-section=\"{s}\"]'); if (e) e.click(); }})()"); print('  section', s)
        return f
    def run_cmp(k): print('  compare', c.pg.evaluate(CLICK_TEXT, 'Run matched comparison'))
    acts = {at(0.2): [panels('overview', ['Occupancy', 'Arriving in 30 min', 'What just happened', 'Bays free by level', 'Parking occupancy'])],
            at(13.8): [section('forecast')], at(14.6): [panels('forecast', ['Where it fills first', 'Demand forecast'])],
            at(20.0): [section('impact')], at(20.4): [run_cmp], at(24.0): [panels('impact', ['Impact', 'Field validation'])]}
    record(c, work / 'cmd', 27.4, acts, 86)
    meta['clock_end'] = c.pg.evaluate("(document.querySelector('#clock') || {}).innerText || ''")
    meta['impact_text'] = c.pg.evaluate("(() => { const v = document.querySelector('#view-impact') || document.body; return v.innerText.slice(0, 900); })()")
    (work / 'cmd_meta.json').write_text(json.dumps(meta, indent=1))
    print('command done; errors', c.errors[:5]); c.ctx.close()


with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
    if which in ('driver', 'all'): driver(b)
    if which in ('command', 'all'): command(b)
    b.close()
