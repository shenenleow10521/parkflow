"""Footage for demo video v2 (follows the v2 script): driver-app screen recordings with taps,
operator clips (a reserved car, a car entering, camera coverage) and states later in the afternoon.

Usage: python3 tools/video/capture2.py OUT_DIR [driver|operator|pressure|all]
Writes into OUT_DIR (the same cap/ folder capture.py uses): JPEG clips, 2x stills,
taps2.json (finger taps per driver clip), layout2.json and facts2.json.
"""
import sys, json, time, base64, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
VT = (ROOT / 'tools' / 'video' / 'vtime.js').read_text()
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'video-capture')
WHAT = sys.argv[2] if len(sys.argv) > 2 else 'all'
FPS = 30
GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-gpu-compositing']


def jload(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else {}


facts = jload('facts2.json')
layout = jload('layout2.json')
taps = jload('taps2.json')


def save():
    (OUT / 'facts2.json').write_text(json.dumps(facts, indent=1))
    (OUT / 'layout2.json').write_text(json.dumps(layout, indent=1))
    (OUT / 'taps2.json').write_text(json.dumps(taps, indent=1))


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Cap:
    def __init__(self, browser, url, viewport, dpr=1, mobile=False, init=''):
        self.ctx = browser.new_context(viewport=viewport, device_scale_factor=dpr, color_scheme='dark', is_mobile=mobile, has_touch=mobile)
        self.pg = self.ctx.new_page()
        self.pg.set_default_timeout(240000)
        self.errors = []
        self.pg.on('pageerror', lambda e: self.errors.append(str(e)))
        self.pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
        self.pg.add_init_script(VT + '\n' + init)
        self.pg.goto(url)
        self.cdp = self.ctx.new_cdp_session(self.pg)
        self.vp = viewport

    def adv(self, sec, step=1000 / 30):
        n = max(1, int(round(sec * 1000 / step)))
        self.pg.evaluate('([n, s]) => { for (let i = 0; i < n; i++) __advance(s); }', [n, step])

    def shot(self, path, scale=1, q=90):
        params = {'format': 'jpeg', 'quality': q}
        if scale != 1:
            params['clip'] = {'x': 0, 'y': 0, 'width': self.vp['width'], 'height': self.vp['height'], 'scale': scale}
        r = self.cdp.send('Page.captureScreenshot', params)
        pathlib.Path(path).write_bytes(base64.b64decode(r['data']))

    def js_click(self, sel):
        return self.pg.evaluate("""s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
            e.click(); return [r.x + r.width / 2, r.y + r.height / 2]; }""", sel)

    def text(self, sel):
        return self.pg.evaluate("s => { const e = document.querySelector(s); return e ? e.innerText : ''; }", sel)

    def boxes(self, sels):
        return self.pg.evaluate('''sels => { const o = {}; for (const s of sels) { const e = document.querySelector(s);
            if (e) { const r = e.getBoundingClientRect(); o[s] = [r.x, r.y, r.width, r.height].map(Math.round); } } return o; }''', sels)


class Rec:
    """Records a driver-app clip: frames at 30 fps while a script of taps runs."""
    def __init__(self, c, name):
        self.c, self.name, self.i = c, name, 0
        self.d = OUT / name
        self.d.mkdir(parents=True, exist_ok=True)
        taps[name] = []

    def wait(self, sec):
        for _ in range(int(round(sec * FPS))):
            self.c.pg.evaluate('__advance(1000 / 30)')
            self.c.shot(self.d / f'{self.i:04d}.jpg', q=90)
            self.i += 1

    def tap(self, sel, label=''):
        xy = self.c.js_click(sel)
        if xy is None:
            log('  missing', sel)
            return
        taps[self.name].append({'f': self.i, 'x': round(xy[0], 1), 'y': round(xy[1], 1), 'label': label})

    def key(self, k):
        self.c.pg.keyboard.press(k)

    def done(self):
        log(f'clip {self.name}: {self.i} frames')
        facts[self.name + '_frames'] = self.i


# ---------------------------------------------------------------- driver app
def driver_ctx(b, member=True, pace=4):
    init = f"try {{ localStorage.setItem('parkflow.driver.v2', JSON.stringify({{ pace: {pace} }})); }} catch (e) {{}}"
    c = Cap(b, (ROOT / 'dist' / 'test-driver.html').as_uri(), {'width': 390, 'height': 844}, dpr=2, mobile=True, init=init)
    c.adv(1.5)
    if not member:
        c.js_click('[data-act="profile"]'); c.adv(0.6)
        c.js_click('[data-act="member-toggle"]'); c.adv(0.4)
        c.pg.keyboard.press('Escape'); c.adv(1.2)
    return c


def driver(b):
    # D1: getting around the app
    c = driver_ctx(b)
    r = Rec(c, 'd_nav')
    r.wait(2.2); r.tap('#tabbar [data-tab="reserve"]', 'Reserve'); r.wait(2.8)
    r.tap('#tabbar [data-tab="car"]', 'My car'); r.wait(2.8)
    r.tap('[data-act="profile"]', 'Account'); r.wait(2.8)
    r.key('Escape'); r.wait(0.8)
    r.tap('#tabbar [data-tab="park"]', 'Park'); r.wait(2.4)
    r.done(); c.ctx.close()

    # D2 / D3: the same trip as a member and as a non-member
    for member, name in ((True, 'd_trip_member'), (False, 'd_trip_non')):
        c = driver_ctx(b, member)
        r = Rec(c, name)
        r.wait(0.8); r.tap('[data-act="plan"]', "I'm on my way"); r.wait(1.4)
        r.tap('[data-act="plan-dest"][data-v="cinema"]', 'Cinema'); r.wait(0.7)
        r.tap('[data-act="plan-eta"][data-v="10"]', '10 min'); r.wait(2.6)
        facts[name + '_plan'] = c.text('#sheet')[:900]
        r.key('Escape'); r.wait(0.8)
        r.tap('#tabbar [data-tab="reserve"]', 'Reserve'); r.wait(1.0)
        r.tap('[data-act="res-type"][data-type="member"]', 'Designated member'); r.wait(2.4)
        facts[name + '_reserve'] = c.text('#tab-reserve')[:900]
        if member:
            r.tap('#res-form-el button[type="submit"]', 'Reserve'); r.wait(3.4)
            facts[name + '_ticket'] = c.text('#tab-reserve')[:700]
        else:
            r.wait(1.8)
        r.done(); c.ctx.close()

    # D4: the arrival time changes the plan
    c = driver_ctx(b)
    r = Rec(c, 'd_eta')
    r.wait(0.6); r.tap('[data-act="plan"]', "I'm on my way"); r.wait(1.2)
    r.tap('[data-act="plan-dest"][data-v="cinema"]', 'Cinema'); r.wait(0.8)
    for v in ('0', '10', '20', '30'):
        r.tap(f'[data-act="plan-eta"][data-v="{v}"]', 'Now' if v == '0' else v + ' min'); r.wait(2.0)
        facts['d_eta_' + v] = c.text('#sheet .preview')
    r.done(); c.ctx.close()

    # D5 / D6: paying as a member and as a non-member
    for member, name in ((True, 'd_pay_member'), (False, 'd_pay_non')):
        c = driver_ctx(b, member)
        r = Rec(c, name)
        r.wait(0.6); r.tap('#tabbar [data-tab="car"]', 'My car'); r.wait(1.4)
        r.tap('#car-paybar [data-act="pay"]', 'Pay'); r.wait(2.2)
        if not member:
            r.tap('[data-act="pay-method"][data-v="debit"]', 'Debit card'); r.wait(1.4)
        facts[name + '_sheet'] = c.text('#sheet')[:800]
        r.tap('[data-act="pay-confirm"]', 'Pay'); r.wait(2.6)
        facts[name + '_done'] = c.text('#sheet')[:500]
        r.done(); c.ctx.close()

    # D7: the Park tab later in the afternoon, when the forecast says it will fill
    c = driver_ctx(b, True, pace=40)
    found = None
    for k in range(80):
        c.adv(2.5, step=250)
        txt = c.text('#tab-park')
        clock = c.text('header') or ''
        if 'Nearly full' in txt:
            found = txt
            break
    c.pg.evaluate("document.querySelector('#tab-park')?.scrollTo(0, 0)")
    c.adv(0.4)
    c.shot(OUT / 'd_full_home.jpg', q=92)
    facts['d_full_home'] = (found or c.text('#tab-park'))[:900]
    log('driver nearly-full state found:', bool(found))
    c.ctx.close()
    save()


# ---------------------------------------------------------------- operator, Weekend surge
def op_boot(b):
    init = "try { localStorage.setItem('parkflow.layers', JSON.stringify({ lights: true, cctv: false, route: true, autoRotate: true })); } catch (e) {}"
    c = Cap(b, (ROOT / 'dist' / 'test.html').as_uri(), {'width': 1920, 'height': 1080}, init=init)
    c.adv(0.3)
    for k in range(10):
        if c.pg.evaluate("document.querySelector('#welcome').hidden"):
            break
        c.js_click('[data-welcome="close"]'); c.adv(0.3)
    return c


def clip(c, name, seconds):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    n = int(round(seconds * FPS)); t0 = time.time()
    for i in range(n):
        c.pg.evaluate('__advance(1000 / 30)')
        c.shot(d / f'{i:04d}.jpg', q=88)
        if i % 60 == 59:
            log(f'  {name} {i + 1}/{n}  {(time.time() - t0) / (i + 1):.2f}s/frame')
    facts[name + '_frames'] = n


def fast_forward(c, until_label, speed='30'):
    """Run the simulation with the 3D view hidden (cheap) until the clock reads until_label (HH:MM)."""
    c.js_click('[data-section="forecast"]'); c.adv(0.2)
    c.js_click(f'[data-speed="{speed}"]')
    for k in range(4000):
        c.adv(0.75, step=250)
        clk = c.text('#clock')
        hm = clk.split()[1] if len(clk.split()) > 1 else ''
        if hm >= until_label:
            break
    c.js_click('[data-speed="5"]')
    c.adv(0.1)
    log('  clock now', c.text('#clock'))


def entry_clip(c):
    """A car entering from the gate: picked the moment a new gate decision appears, followed until it parks."""
    pg = c.pg
    c.js_click('[data-section="allocation"]'); c.adv(0.3)
    first_id = pg.evaluate("""() => document.querySelector('#view-allocation tbody tr[data-act="select-vehicle"]')?.dataset.id || null""")
    picked = None; row = ''
    for k in range(1200):
        c.adv(1 / 10)
        cur = pg.evaluate("""() => { const r = document.querySelector('#view-allocation tbody tr[data-act="select-vehicle"]');
            return r ? [r.dataset.id, r.innerText] : null; }""")
        if cur and cur[0] != first_id and 'Reserved' not in cur[1] and 'Parked' not in cur[1]:
            row = cur[1]
            picked = pg.evaluate("""() => { const r = document.querySelector('#view-allocation tbody tr[data-act="select-vehicle"]'); r.click(); return r.dataset.id; }""")
            break
    c.js_click('[data-section="overview"]'); c.adv(0.1)
    c.js_click('#side-tabs [data-tab="reasoning"]')
    c.js_click('#focus-btn')
    c.adv(0.1)
    facts['entry_row'] = row if picked else ''
    facts['entry_why'] = c.text('#side-body')[:900]
    layout['entry'] = c.boxes(['#side', '#side-body', '#phone', '#viewport', '#card-events', '#board', '#kpis'])
    log('clip: car entering', picked, row.replace('\t', ' '))
    clip(c, 'op2_entry', 13.0)
    # let it finish parking (if it has not yet) before the high-resolution still
    for k in range(120):
        if picked and f'Parked {picked} parked' in c.text('#events-list'):
            break
        c.adv(0.25, step=250)
    c.shot(OUT / 'op2_entry_hi.jpg', scale=2)
    facts['entry_events'] = c.text('#events-list')[:1500]
    facts['entry_side'] = c.text('#side-body')[:900]
    pg.keyboard.press('Escape'); c.adv(0.3)
    save()


def operator(b):
    c = op_boot(b)
    pg = c.pg
    c.adv(0.4)
    # O1: the reserved car (R-01 checks in at 14:08 and drives to its held bay)
    vid = pg.evaluate("""() => { const r = [...document.querySelectorAll('#events-list [data-act="select-vehicle"]')].find(e => e.innerText.includes('R-01'));
        return r ? r.dataset.id : null; }""")
    if vid:
        pg.evaluate("id => document.querySelector(`#events-list [data-act=\"select-vehicle\"][data-id=\"${id}\"]`).click()", vid)
    c.adv(0.5)
    facts['res_vehicle'] = c.text('#side-body')[:600]
    layout['res'] = c.boxes(['#side', '#phone', '#viewport', '#card-events', '#events-list'])
    log('clip: reserved car', vid)
    clip(c, 'op2_res', 6.0)
    c.shot(OUT / 'op2_res_hi.jpg', scale=2)
    facts['res_events'] = c.text('#events-list')[:1500]
    pg.keyboard.press('Escape'); c.adv(0.3)

    entry_clip(c)

    # O3: camera coverage layer
    c.js_click('#reset-cam'); c.adv(0.3)
    c.js_click('#layers-btn'); c.adv(0.2)
    c.js_click('#layers-pop [data-layer="cctv"]'); c.adv(0.2)
    c.js_click('#layers-btn'); c.adv(0.5)
    log('clip: camera coverage')
    clip(c, 'op2_cctv', 4.5)
    c.shot(OUT / 'op2_cctv_hi.jpg', scale=2)
    c.js_click('#layers-btn'); c.adv(0.2)
    c.js_click('#layers-pop [data-layer="cctv"]'); c.adv(0.2)
    c.js_click('#layers-btn'); c.adv(0.2)
    save()

    # O4: 14:41, R-02 has expired as a no-show
    fast_forward(c, '14:41')
    c.js_click('[data-section="reservations"]'); c.adv(0.6)
    c.shot(OUT / 'op2_res_page.jpg', scale=2)
    facts['res_page_1441'] = c.text('#view-reservations')[:2500]
    layout['res_page'] = c.pg.evaluate("""() => { const o = {}; document.querySelectorAll('#view-reservations .card, #view-reservations table tr').forEach((e, i) => {
        const r = e.getBoundingClientRect(); if (r.height < 10 || r.y > 1080) return; o[i + ':' + e.innerText.slice(0, 40).replace(/\\s+/g, ' ')] = [r.x, r.y, r.width, r.height].map(Math.round); }); return o; }""")

    # O5: 14:43, the operator actions are recommended; review and apply two of them
    fast_forward(c, '14:43')
    c.js_click('[data-section="overview"]'); c.adv(0.3)
    c.js_click('#side-tabs [data-tab="actions"]'); c.adv(0.4)
    c.shot(OUT / 'op2_actions.jpg', scale=2)
    facts['actions_1443'] = c.text('#side-body')[:2000]
    facts['kpis_1443'] = c.text('#kpis')
    layout['actions'] = c.boxes(['#side', '#side-body', '#kpis', '#card-events', '#banner'])
    c.js_click('[data-act="review-action"][data-id="offer"]'); c.adv(0.4)
    c.shot(OUT / 'op2_actions_review.jpg', scale=2)
    layout['actions_review'] = c.boxes(['#side', '#side-body'])
    c.js_click('[data-act="confirm-action"][data-id="offer"]'); c.adv(0.5)
    c.js_click('[data-act="review-action"][data-id="later"]'); c.adv(0.3)
    c.js_click('[data-act="confirm-action"][data-id="later"]'); c.adv(0.8)
    c.shot(OUT / 'op2_actions_done.jpg', scale=2)
    facts['actions_done'] = c.text('#side-body')[:1500]
    facts['events_after_actions'] = c.text('#events-list')[:1500]
    facts['op_errors'] = c.errors[:5]
    save()
    c.ctx.close()


# ---------------------------------------------------------------- operator, Capacity pressure
def pressure(b):
    c = op_boot(b)
    pg = c.pg
    pg.select_option('#scenario', 'pressure')
    c.adv(0.6)
    fast_forward(c, '15:21')
    c.js_click('[data-section="overview"]'); c.adv(0.3)
    c.js_click('#reset-cam'); c.adv(0.4)
    layout['pressure'] = c.boxes(['#kpis', '#viewport', '#board', '#side', '#side-body', '#card-events', '#events-list', '#banner'])
    log('clip: capacity pressure')
    clip(c, 'op2_full', 5.0)
    c.shot(OUT / 'op2_full_hi.jpg', scale=2)
    facts['full_kpis'] = c.text('#kpis')
    facts['full_board'] = c.text('#board')
    facts['full_events'] = c.text('#events-list')[:1800]
    c.js_click('#side-tabs [data-tab="actions"]'); c.adv(0.4)
    c.js_click('[data-act="review-action"][data-id="overflow"]'); c.adv(0.5)
    c.shot(OUT / 'op2_full_overflow.jpg', scale=2)
    facts['full_actions'] = c.text('#side-body')[:2000]
    layout['pressure_actions'] = c.boxes(['#side', '#side-body'])
    facts['pressure_errors'] = c.errors[:5]
    save()
    c.ctx.close()


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=GL_ARGS)
        if WHAT in ('driver', 'all'):
            driver(b)
        if WHAT in ('pressure', 'all'):
            pressure(b)
        if WHAT in ('operator', 'all'):
            operator(b)
        if WHAT == 'entry':
            c = op_boot(b); c.adv(0.4); c.adv(6.5); entry_clip(c); c.ctx.close()
        save()
        b.close()
    log('done')
