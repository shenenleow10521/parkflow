"""Load the built page headlessly, report console errors, run interaction checks, and take screenshots."""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
url = (root / 'dist' / 'test.html').as_uri()
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/shots')
out.mkdir(parents=True, exist_ok=True)
steps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['overview']

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    pg.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    pg.goto(url)
    pg.wait_for_timeout(1500)
    if pg.is_visible('#welcome'):
        pg.screenshot(path=str(out / 'welcome.png')) if 'out' in dir() else None
        pg.click('[data-welcome="close"]')
        pg.wait_for_timeout(300)
    for s in steps:
        if s == 'overview':
            pg.screenshot(path=str(out / 'overview.png'))
        elif s in ('forecast', 'allocation', 'reservations', 'impact'):
            pg.click(f'#rail [data-section="{s}"]')
            pg.wait_for_timeout(800)
            pg.screenshot(path=str(out / f'{s}.png'), full_page=False)
            pg.evaluate("document.getElementById('main').scrollTop = 99999")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(out / f'{s}-bottom.png'))
            pg.evaluate("document.getElementById('main').scrollTop = 0")
        elif s == 'back':
            pg.click('#rail [data-section="overview"]')
            pg.wait_for_timeout(600)
        elif s == 'compare':
            pg.click('#run-compare')
            pg.wait_for_timeout(2500)
            pg.screenshot(path=str(out / 'compare.png'))
        elif s == 'select':
            pg.click('[data-act="pick-searching"]')
            pg.wait_for_timeout(1200)
            pg.screenshot(path=str(out / 'select.png'))
        elif s == 'reasoning':
            pg.click('[data-tab="reasoning"]')
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(out / 'reasoning.png'))
        elif s == 'actions':
            pg.click('[data-tab="actions"]')
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(out / 'actions.png'))
        elif s.startswith('floor'):
            f = s[5:]
            pg.click(f'#floor-seg [data-floorview="{f}"]')
            pg.wait_for_timeout(1200)
            pg.screenshot(path=str(out / f'floor-{f}.png'))
        elif s == 'present':
            pg.click('#present')
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(out / 'pres1.png'))
            for i in range(2, 7):
                pg.click('[data-pres="next"]')
                pg.wait_for_timeout(1600)
                pg.screenshot(path=str(out / f'pres{i}.png'))
            pg.click('[data-pres="exit"]')
        elif s == 'mobile':
            pg.set_viewport_size({'width': 400, 'height': 860})
            pg.wait_for_timeout(800)
            pg.screenshot(path=str(out / 'mobile.png'), full_page=True)
            sw = pg.evaluate('document.documentElement.scrollWidth')
            print('mobile scrollWidth', sw)
            pg.set_viewport_size({'width': 1440, 'height': 900})
        elif s.startswith('wait'):
            pg.wait_for_timeout(int(s[4:]))
        elif s.startswith('eval:'):
            print('eval', pg.evaluate(s[5:]))
    print('ERRORS', json.dumps(errors[:20], indent=1))
    b.close()
