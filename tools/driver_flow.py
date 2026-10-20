"""Driver app: end-to-end flow checks and screenshots (phone and desktop, light and dark)."""
import sys, json, pathlib, time
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
url = (root / 'dist' / 'test-driver.html').as_uri()
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/drv')
out.mkdir(parents=True, exist_ok=True)
ok = []
def check(name, cond, extra=''):
    ok.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name, extra)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.route('**/fonts.g*/**', lambda r: r.abort())
    pg.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / '01-home.png'))
    check('home shows level board', 'B1' in pg.inner_text('#park-sign') and 'Parking available' in pg.inner_text('#park-sign'))
    check('no horizontal scroll', pg.evaluate('document.documentElement.scrollWidth') <= 390)
    # demo clock 10x
    pg.click('[data-act="profile"]'); pg.wait_for_timeout(500)
    pg.click('[data-act="pace"][data-v="10"]'); pg.wait_for_timeout(200)
    pg.screenshot(path=str(out / '02-profile.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
    # plan
    pg.click('#park-cta [data-act="plan"]'); pg.wait_for_timeout(600)
    check('plan sheet open', pg.is_visible('#sheet') and 'Where are you going' in pg.inner_text('#sheet'))
    pg.click('[data-act="plan-dest"][data-v="cinema"]'); pg.wait_for_timeout(150)
    pg.click('[data-act="plan-eta"][data-v="10"]'); pg.wait_for_timeout(300)
    pg.screenshot(path=str(out / '03-plan.png'))
    pg.click('[data-act="start"]'); pg.wait_for_timeout(900)
    check('guidance screen open', pg.is_visible('#scr-guide'))
    g = pg.inner_text('#g-sign')
    check('pending guidance shows arrival time', 'Arrive at about' in g, g[:80])
    pg.screenshot(path=str(out / '04-guide-pending.png'))
    pg.click('[data-act="arrive"]'); pg.wait_for_timeout(4500)
    pg.screenshot(path=str(out / '05-guide-driving.png'))
    seen = set()
    t0 = time.time()
    while time.time() - t0 < 90:
        if pg.is_visible('#scr-parked'):
            break
        try:
            seen.add(pg.inner_text('#g-sign .dsign-t b'))
        except Exception:
            pass
        if len(seen) == 2: pg.screenshot(path=str(out / '06-guide-step.png'))
        pg.wait_for_timeout(700)
    print('instructions seen:', seen)
    check('driver reached a bay', pg.is_visible('#scr-parked'))
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(out / '07-parked.png'))
    check('parked screen shows bay', 'Bay' in pg.inner_text('#scr-parked'))
    pg.click('[data-act="parked-done"]'); pg.wait_for_timeout(900)
    check('my car tab shows find steps', 'Find your car' in pg.inner_text('#tab-car'))
    pg.screenshot(path=str(out / '08-mycar.png'))
    pg.evaluate("document.getElementById('tabview').scrollTop = 9999"); pg.wait_for_timeout(300)
    pg.screenshot(path=str(out / '09-mycar-bottom.png'))
    pg.click('[data-act="pay"]'); pg.wait_for_timeout(700)
    pg.screenshot(path=str(out / '10-pay.png'))
    pg.click('[data-act="pay-confirm"]'); pg.wait_for_timeout(1500)
    check('paid state shown', 'Paid at' in pg.inner_text('#tab-car'))
    # wait to leave
    t0 = time.time()
    while time.time() - t0 < 60 and 'Trip complete' not in pg.inner_text('#tab-car'):
        pg.wait_for_timeout(800)
    check('trip completes after leaving', 'Trip complete' in pg.inner_text('#tab-car'))
    pg.screenshot(path=str(out / '11-trip-complete.png'))
    # reserve
    pg.click('#tabbar [data-tab="reserve"]'); pg.wait_for_timeout(700)
    pg.screenshot(path=str(out / '12-reserve.png'))
    pg.click('[data-act="res-type"][data-type="member"]'); pg.wait_for_timeout(400)
    pg.click('#res-form-el button[type="submit"]'); pg.wait_for_timeout(500)
    check('eligibility is required', 'Confirm that you are eligible' in pg.inner_text('#tab-reserve'))
    pg.check('#res-elig'); pg.click('#res-form-el button[type="submit"]'); pg.wait_for_timeout(900)
    check('reservation ticket shown', pg.locator('#res-active .ticket').count() == 1, pg.inner_text('#tab-reserve')[:120])
    pg.screenshot(path=str(out / '13-ticket.png'))
    # assistance needs permit
    pg.evaluate("document.getElementById('tabview').scrollTop = 9999"); pg.wait_for_timeout(200)
    pg.click('#res-list [data-act="assist"]'); pg.wait_for_timeout(600)
    pg.click('[data-act="assist-send"]'); pg.wait_for_timeout(300)
    check('assistance asks for permit', pg.is_visible('#assist-err'))
    pg.check('#assist-permit'); pg.click('[data-act="assist-send"]'); pg.wait_for_timeout(700)
    check('assistance logged', 'AR-' in pg.inner_text('#tab-reserve'))
    check('no runtime errors', not errors, errors[:3])
    ctx.close()
    # dark theme, phone
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, color_scheme='dark', is_mobile=True, has_touch=True)
    pg = ctx.new_page(); pg.route('**/fonts.g*/**', lambda r: r.abort()); pg.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / '20-dark-home.png'))
    pg.click('#park-cta [data-act="plan"]'); pg.wait_for_timeout(500)
    pg.click('[data-act="start"]'); pg.wait_for_timeout(500)
    pg.click('[data-act="arrive"]'); pg.wait_for_timeout(6000)
    pg.screenshot(path=str(out / '21-dark-guide.png'))
    ctx.close()
    # desktop
    ctx = b.new_context(viewport={'width': 1440, 'height': 900})
    pg = ctx.new_page(); pg.route('**/fonts.g*/**', lambda r: r.abort()); pg.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / '30-desktop.png'))
    b.close()
print('SUMMARY', sum(ok), '/', len(ok))
