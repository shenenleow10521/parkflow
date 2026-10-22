"""Capture app footage for the demo video with a virtual clock (tools/video/vtime.js).

Usage: python3 tools/video/capture.py OUT_DIR [operator|driver|all]

Operator (1920x1080): live JPEG sequences of the 3D overview and a selected car, 2x stills, and
tall 2x stills of Forecast / Reservations / Impact / Allocation for smooth scrolling in the video.
Driver (390x844 @3x): stills of each step and a short live clip of turn-by-turn guidance.
Also writes facts.json with the numbers the video quotes, read from the running app.
"""
import sys, json, time, base64, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
VT = (ROOT / 'tools' / 'video' / 'vtime.js').read_text()
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'video-capture')
WHAT = sys.argv[2] if len(sys.argv) > 2 else 'all'
FPS = 30
GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-gpu-compositing']
facts = {}
fp = OUT / 'facts.json'
if fp.exists():
    facts = json.loads(fp.read_text())


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Cap:
    def __init__(self, browser, url, viewport, dpr=1, mobile=False, init=''):
        self.ctx = browser.new_context(viewport=viewport, device_scale_factor=dpr, color_scheme='dark',
                                       is_mobile=mobile, has_touch=mobile)
        self.pg = self.ctx.new_page()
        self.errors = []
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        self.pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
        self.pg.add_init_script(VT + '\n' + init)
        self.pg.goto(url)
        self.cdp = self.ctx.new_cdp_session(self.pg)
        self.vp = viewport

    def adv(self, sec):
        n = max(1, int(round(sec * FPS)))
        self.pg.evaluate('n => { for (let i = 0; i < n; i++) __advance(1000 / 30); }', n)

    def shot(self, path, scale=1, q=90, clip=None):
        params = {'format': 'jpeg', 'quality': q}
        if scale != 1 or clip:
            x, y, w, h = clip or (0, 0, self.vp['width'], self.vp['height'])
            params['clip'] = {'x': x, 'y': y, 'width': w, 'height': h, 'scale': scale}
        r = self.cdp.send('Page.captureScreenshot', params)
        pathlib.Path(path).write_bytes(base64.b64decode(r['data']))

    def clip(self, name, seconds, before=None):
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        n = int(round(seconds * FPS))
        t0 = time.time()
        for i in range(n):
            if before:
                before(i)
            self.pg.evaluate('__advance(1000 / 30)')
            self.shot(d / f'{i:04d}.jpg', q=88)
            if i % 30 == 29:
                log(f'  {name} {i + 1}/{n}  {(time.time() - t0) / (i + 1):.2f}s/frame')
        return n

    def boxes(self, sels):
        return self.pg.evaluate('''sels => { const o = {}; for (const s of sels) { const e = document.querySelector(s);
            if (e) { const r = e.getBoundingClientRect(); o[s] = [r.x, r.y, r.width, r.height].map(Math.round); } } return o; }''', sels)


def tall(c, name, section):
    """Render a scrolling page at full height once, so the video can scroll it smoothly."""
    pg = c.pg
    pg.evaluate(f"document.querySelector('[data-section=\"{section}\"]').click()")
    c.adv(1.2)
    pg.evaluate("document.querySelector('#main').scrollTop = 0")
    h = pg.evaluate("(() => { const m = document.querySelector('#main'); return m.scrollHeight - m.clientHeight; })()")
    full = 1080 + max(0, h)
    c.ctx.pages[0].set_viewport_size({'width': 1920, 'height': full})
    c.vp = {'width': 1920, 'height': full}
    c.adv(0.8)
    boxes = pg.evaluate('''() => { const o = {}; document.querySelectorAll('#main section, #main .card, #main .kpi, #main h2, #main .big-cmp > div, #main .member-live, #main .member-hist').forEach((e, i) => {
        const r = e.getBoundingClientRect(); if (r.height < 20) return; const h = e.querySelector('h2, h3');
        o[i + ':' + (e.id || e.className.split(' ')[0]) + ':' + (h ? h.textContent.trim().slice(0, 48) : '')] = [r.x, r.y, r.width, r.height].map(Math.round); }); return o; }''')
    c.shot(OUT / f'{name}.jpg', scale=2, q=90)
    c.ctx.pages[0].set_viewport_size({'width': 1920, 'height': 1080})
    c.vp = {'width': 1920, 'height': 1080}
    c.adv(0.5)
    log(f'tall {name}: {full}px')
    return {'height': full, 'boxes': boxes}


def select_and_clip(c, layout):
    """Select a car that was just guided (newest Guidance event) and film it driving to its zone."""
    pg = c.pg
    for attempt in range(60):
        vid = pg.evaluate("""() => { const rows = [...document.querySelectorAll('#events-list [data-act="select-vehicle"]')];
            const r = rows.find(e => /^\\s*[0-9:]+\\s*Guidance/.test(e.innerText) || e.innerText.includes('Guidance'));
            return r ? r.dataset.id : null; }""")
        if vid:
            pg.evaluate("id => document.querySelector(`#events-list [data-act=\"select-vehicle\"][data-id=\"${id}\"]`).click()", vid)
            c.adv(0.3)
            pg.evaluate("document.querySelector('#side-tabs [data-tab=\"reasoning\"]')?.click()")
            c.adv(0.3)
            txt = pg.inner_text('#side-body')
            if 'Showing the latest decision' not in txt and 'holds a reservation' not in txt and 'Top candidate zones' in txt:
                log('selected vehicle', vid)
                break
        pg.keyboard.press('Escape')
        c.adv(0.8)
    facts['why_this_bay'] = pg.inner_text('#side-body')
    layout['selected'] = c.boxes(['#side', '#side-body', '#phone', '#viewport'])
    log('clip: selected car')
    c.clip('op_live_selected', 7.0)
    c.shot(OUT / 'op_selected_hi.jpg', scale=2)


def operator(browser):
    url = (ROOT / 'dist' / 'test.html').as_uri()
    init = "try { localStorage.setItem('parkflow.layers', JSON.stringify({ lights: true, cctv: false, route: true, autoRotate: true })); } catch (e) {}"
    c = Cap(browser, url, {'width': 1920, 'height': 1080}, init=init)
    pg = c.pg
    c.adv(0.3)
    pg.evaluate("document.querySelector('[data-welcome=\"close\"]')?.click()")
    c.adv(4.0)
    layout = {'overview': c.boxes(['#kpis', '#viewport', '#board', '#side', '#banner', '#card-chart', '#card-events', '#legend', '#rail', '#clock', '#run-compare', '#floor-seg'])}
    layout['kpi_cells'] = pg.evaluate("[...document.querySelectorAll('#kpis > *')].map(e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map(Math.round); })")

    log('clip: overview')
    c.clip('op_live_overview', 8.0)
    c.shot(OUT / 'op_overview_hi.jpg', scale=2)
    facts['overview_kpis'] = pg.inner_text('#kpis')
    facts['board'] = pg.inner_text('#board')

    select_and_clip(c, layout)
    pg.keyboard.press('Escape')
    c.adv(0.4)

    layout['forecast'] = tall(c, 'op_forecast_tall', 'forecast')
    facts['forecast_text'] = pg.inner_text('#view-forecast')[:4000]
    layout['reservations'] = tall(c, 'op_reservations_tall', 'reservations')
    facts['reservations_text'] = pg.inner_text('#view-reservations')[:3000]
    layout['allocation'] = tall(c, 'op_allocation_tall', 'allocation')

    pg.click('#run-compare')
    for i in range(40):
        c.adv(0.5)
        if pg.query_selector('#view-impact .big-cmp'):
            break
    c.adv(1.5)
    open_projection(c)
    layout['impact'] = tall(c, 'op_impact_tall', 'impact')
    facts['impact_text'] = pg.inner_text('#view-impact')[:6000]
    facts['kpis_after'] = pg.inner_text('#kpis')
    (OUT / 'layout_operator.json').write_text(json.dumps(layout, indent=1))
    facts['operator_errors'] = c.errors[:5]
    c.ctx.close()


def driver(browser):
    url = (ROOT / 'dist' / 'test-driver.html').as_uri()
    c = Cap(browser, url, {'width': 390, 'height': 844}, dpr=3, mobile=True)
    pg = c.pg

    def click(sel, wait=0.6):
        pg.click(sel)
        c.adv(wait)

    def still(name):
        c.shot(OUT / f'drv_{name}.jpg', q=92)
        log('still', name)

    c.adv(2.0)
    still('home')
    facts['drv_home'] = pg.inner_text('#tab-park')[:1500]
    # book first, while the second car is still free
    click('#tabbar [data-tab="reserve"]', 1.0)
    click('[data-act="res-type"][data-type="ladies"]', 0.8)
    if pg.query_selector('#res-elig'):
        pg.check('#res-elig')
        c.adv(0.5)
    still('reserve_ladies')
    click('[data-act="res-type"][data-type="member"]', 0.8)
    still('reserve_member')
    pg.click('#res-form-el button[type="submit"]')
    c.adv(4.0)
    still('ticket')
    facts['drv_ticket'] = pg.inner_text('#tab-reserve')[:1200]
    if pg.query_selector('[data-act="res-cancel"]'):
        click('[data-act="res-cancel"]', 0.8)
    click('#tabbar [data-tab="car"]', 1.0)
    still('mycar')
    click('#car-paybar [data-act="pay"]', 1.0)
    still('pay')
    facts['drv_pay'] = pg.inner_text('#sheet')[:800]
    click('[data-act="pay-confirm"]', 1.2)
    still('paid')
    click('[data-act="sheet-close"]', 0.8)
    click('[data-act="plan-new"]', 0.9)
    pg.click('[data-act="plan-car"][data-plate="WXY 8812"]')
    pg.click('[data-act="plan-dest"][data-v="cinema"]')
    pg.click('[data-act="plan-eta"][data-v="10"]')
    c.adv(0.6)
    still('plan')
    click('[data-act="start"]', 1.2)
    still('guide_pending')
    click('[data-act="arrive"]', 1.0)
    log('clip: driver guidance')
    c.clip('drv_live_guide', 6.0)
    still('guide_driving')
    for i in range(240):
        if pg.is_visible('#scr-parked'):
            break
        c.adv(0.5)
    c.adv(1.2)
    still('parked')
    click('[data-act="parked-done"]', 1.0)
    still('two_cars')
    facts['driver_errors'] = c.errors[:5]
    c.ctx.close()


def selected_only(browser):
    url = (ROOT / 'dist' / 'test.html').as_uri()
    init = "try { localStorage.setItem('parkflow.layers', JSON.stringify({ lights: true, cctv: false, route: true, autoRotate: true })); } catch (e) {}"
    c = Cap(browser, url, {'width': 1920, 'height': 1080}, init=init)
    c.adv(0.3)
    c.pg.evaluate("document.querySelector('[data-welcome=\"close\"]')?.click()")
    c.adv(12.0)
    lp = OUT / 'layout_operator.json'
    layout = json.loads(lp.read_text()) if lp.exists() else {}
    import shutil
    shutil.rmtree(OUT / 'op_live_selected', ignore_errors=True)
    select_and_clip(c, layout)
    lp.write_text(json.dumps(layout, indent=1))
    c.ctx.close()


def open_projection(c):
    c.pg.evaluate("""() => { document.querySelectorAll('#view-impact details').forEach(d => d.open = true); }""")
    c.adv(0.6)


def impact_only(browser):
    url = (ROOT / 'dist' / 'test.html').as_uri()
    c = Cap(browser, url, {'width': 1920, 'height': 1080})
    c.adv(0.3)
    c.pg.evaluate("document.querySelector('[data-welcome=\"close\"]')?.click()")
    c.adv(2.0)
    for k in range(10):
        if c.pg.evaluate("document.querySelector('#welcome').hidden"):
            break
        c.pg.evaluate("document.querySelector('[data-welcome=\"close\"]')?.click()")
        c.adv(0.5)
    lp = OUT / 'layout_operator.json'
    layout = json.loads(lp.read_text()) if lp.exists() else {}
    c.pg.evaluate("document.querySelector('#run-compare').click()")
    for i in range(40):
        c.adv(0.5)
        if c.pg.query_selector('#view-impact .big-cmp'):
            break
    c.adv(1.5)
    c.pg.evaluate("document.querySelector('[data-section=\"impact\"]').click()")
    c.adv(0.8)
    open_projection(c)
    layout['impact'] = tall(c, 'op_impact_tall', 'impact')
    facts['impact_text'] = c.pg.inner_text('#view-impact')[:6000]
    lp.write_text(json.dumps(layout, indent=1))
    c.ctx.close()


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=GL_ARGS)
        if WHAT in ('driver', 'all'):
            driver(b)
            fp.write_text(json.dumps(facts, indent=1))
        if WHAT == 'impact':
            impact_only(b)
            fp.write_text(json.dumps(facts, indent=1))
        if WHAT == 'selected':
            selected_only(b)
            fp.write_text(json.dumps(facts, indent=1))
        if WHAT in ('operator', 'all'):
            operator(b)
            fp.write_text(json.dumps(facts, indent=1))
        b.close()
    log('done')
