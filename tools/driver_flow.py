"""Driver app: end-to-end flow checks and screenshots (phone and desktop, light and dark)."""
import sys, re, pathlib, time
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
url = (root / 'dist' / 'test-driver.html').as_uri()
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/drv')
out.mkdir(parents=True, exist_ok=True)
ok = []
def check(name, cond, extra=''):
    ok.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name, extra)

def new_ctx(b, **kw):
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, **kw)
    pg = ctx.new_page()
    pg.route('**/fonts.g*/**', lambda r: r.abort())
    pg.route('**/cdn.jsdelivr.net/**', lambda r: r.abort())
    return ctx, pg

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = new_ctx(b)
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / '01-home.png'))
    home = pg.inner_text('#tab-park')
    check('home shows level board', 'Parking available' in pg.inner_text('#park-sign'))
    check('home shows the already-parked car with time and fee', 'VKL 2026 is in' in home and 'so far' in home, home[home.find('VKL'):home.find('VKL') + 70])
    check('no horizontal scroll', pg.evaluate('document.documentElement.scrollWidth') <= 390)

    # account: membership card instead of a tick box, add a car, faster clock
    pg.click('[data-act="profile"]'); pg.wait_for_timeout(500)
    sheet = pg.inner_text('#sheet')
    check('account shows membership card and points', 'KL East Mall Rewards' in sheet and '2,340' in sheet)
    pg.click('[data-act="pace"][data-v="10"]'); pg.wait_for_timeout(150)
    pg.click('#sheet [data-act="car-add"]'); pg.wait_for_timeout(200)
    pg.fill('#new-plate', 'bkn 4410'); pg.click('[data-act="car-add-save"]'); pg.wait_for_timeout(300)
    check('new car added to garage', 'BKN 4410' in pg.inner_text('#sheet'))
    pg.screenshot(path=str(out / '02-account.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(500)

    # my car: real stay, pay bar, pay with points
    pg.click('#tabbar [data-tab="car"]'); pg.wait_for_timeout(800)
    car = pg.inner_text('#tab-car')
    check('my car shows parked since, duration and fee', 'Parked since' in car and 'Fee so far' in car)
    check('pay button visible in my car', pg.is_visible('#car-paybar [data-act="pay"]'))
    pg.screenshot(path=str(out / '03-mycar.png'))
    pg.click('#car-paybar [data-act="pay"]'); pg.wait_for_timeout(700)
    s = pg.inner_text('#sheet')
    check('payment offers wallet, cards and points', 'KL East Mall wallet' in s and 'Debit card ending 4821' in s and 'Use member points' in s)
    pg.screenshot(path=str(out / '04-pay.png'))
    pg.click('[data-act="pay-confirm"]'); pg.wait_for_timeout(900)
    s = pg.inner_text('#sheet')
    check('paid with points, receipt shown', 'Paid' in s and 'Points used' in s, s[:120])
    pg.screenshot(path=str(out / '05-paid.png'))
    pg.click('[data-act="sheet-close"]'); pg.wait_for_timeout(600)
    check('car shows paid state', 'Paid at' in pg.inner_text('#tab-car'))

    # wallet top up from my car
    pg.click('#car-wallet [data-act="topup"]'); pg.wait_for_timeout(600)
    pg.click('[data-act="top-amt"][data-v="50"]'); pg.click('[data-act="top-from"][data-v="credit"]'); pg.wait_for_timeout(200)
    pg.screenshot(path=str(out / '06-topup.png'))
    pg.click('[data-act="topup-confirm"]'); pg.wait_for_timeout(1200)
    check('wallet topped up', 'RM 62.50' in pg.inner_text('#car-wallet'), pg.inner_text('#car-wallet'))

    # park a new car with guidance
    pg.click('[data-act="plan-new"]'); pg.wait_for_timeout(600)
    s = pg.inner_text('#sheet')
    check('plan sheet asks which car and shows member status from account', 'Which car?' in s and 'Gold member' in s and 'WXY 8812' in s)
    pg.click('[data-act="plan-car"][data-plate="WXY 8812"]'); pg.click('[data-act="plan-dest"][data-v="cinema"]'); pg.click('[data-act="plan-eta"][data-v="10"]'); pg.wait_for_timeout(300)
    pg.screenshot(path=str(out / '07-plan.png'))
    pg.click('[data-act="start"]'); pg.wait_for_timeout(900)
    check('guidance screen open', pg.is_visible('#scr-guide'))
    pg.screenshot(path=str(out / '08-guide-pending.png'))
    pg.click('[data-act="arrive"]'); pg.wait_for_timeout(4500)
    pg.screenshot(path=str(out / '09-guide-driving.png'))
    t0 = time.time()
    while time.time() - t0 < 90 and not pg.is_visible('#scr-parked'):
        pg.wait_for_timeout(700)
    check('new car reached a bay', pg.is_visible('#scr-parked'))
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(out / '10-parked.png'))
    pg.click('[data-act="parked-done"]'); pg.wait_for_timeout(900)
    tabs = pg.inner_text('#car-tabs')
    check('my car lists both cars', 'VKL 2026' in tabs and 'WXY 8812' in tabs, tabs.replace('\n', ' '))
    pg.screenshot(path=str(out / '11-two-cars.png'))
    # non-member pays by card
    pg.click('[data-act="profile"]'); pg.wait_for_timeout(400); pg.click('[data-act="member-toggle"]'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
    pg.click('#car-paybar [data-act="pay"]'); pg.wait_for_timeout(600)
    pg.click('[data-act="pay-method"][data-v="debit"]'); pg.wait_for_timeout(200)
    s = pg.inner_text('#sheet')
    check('non-member pays the full first hour by card', 'RM 3.00' in s and 'Debit card ending 4821' in s, s[:160])
    pg.click('[data-act="pay-confirm"]'); pg.wait_for_timeout(800); pg.click('[data-act="sheet-close"]'); pg.wait_for_timeout(500)
    t0 = time.time()
    while time.time() - t0 < 60 and 'has left' not in pg.inner_text('#tab-car'):
        pg.wait_for_timeout(800)
    check('car leaves after paying', 'has left' in pg.inner_text('#tab-car'))
    # reserve: member bay is locked for non-members; EV needs a declaration unless the car is electric
    pg.click('#tabbar [data-tab="reserve"]'); pg.wait_for_timeout(700)
    pg.click('[data-act="res-type"][data-type="member"]'); pg.wait_for_timeout(400)
    check('member bay locked for non-members', 'Members only' in pg.inner_text('#tab-reserve'))
    pg.click('[data-act="profile"]'); pg.wait_for_timeout(400); pg.click('[data-act="member-toggle"]'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
    t = pg.inner_text('#tab-reserve')
    check('member eligibility verified from the account', 'Verified: Gold member' in t)
    pg.click('#res-form-el button[type="submit"]'); pg.wait_for_timeout(900)
    check('reservation ticket shown', pg.locator('#res-active .ticket').count() == 1)
    pg.screenshot(path=str(out / '12-ticket.png'))
    check('no runtime errors', not errors, errors[:3])
    ctx.close()
    # dark theme
    ctx, pg = new_ctx(b, color_scheme='dark')
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.click('#tabbar [data-tab="car"]'); pg.wait_for_timeout(900)
    pg.screenshot(path=str(out / '20-dark-mycar.png'))
    pg.click('#car-paybar [data-act="pay"]'); pg.wait_for_timeout(800)
    pg.screenshot(path=str(out / '21-dark-pay.png'))
    ctx.close()
    b.close()
print('SUMMARY', sum(ok), '/', len(ok))
