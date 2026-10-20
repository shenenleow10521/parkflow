"""Functional checks against acceptance criteria using the real page."""
import pathlib
from playwright.sync_api import sync_playwright

url = (pathlib.Path(__file__).resolve().parent.parent / 'dist' / 'test.html').as_uri()
ok = []
def check(name, cond, extra=''):
    ok.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name, extra)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.route('**/fonts.g*/**', lambda r: r.abort())
    pg.goto(url)
    pg.wait_for_timeout(1200)
    check('welcome shown on first visit', pg.is_visible('#welcome'))
    pg.click('[data-welcome="close"]')
    pg.wait_for_timeout(300)
    # pause for deterministic checks
    pg.click('#play'); pg.wait_for_timeout(300)
    kpi = pg.inner_text('#kpis')
    clock = pg.inner_text('#clock')
    floors = pg.inner_text('#floors-body')
    # reset determinism
    pg.click('#reset'); pg.wait_for_timeout(500)
    if pg.get_attribute('#play', 'aria-label') == 'Pause simulation':
        pg.click('#play'); pg.wait_for_timeout(300)
    check('reset restores same clock', pg.inner_text('#clock') == 'Sat 14:08', pg.inner_text('#clock'))
    # 3D totals vs dashboard: floor card general-free sums equal KPI
    import re
    fl = [int(x) for x in re.findall(r'(\d+) general free', pg.inner_text('#floors-body'))]
    k = int(re.search(r'(\d+) of \d+ free', pg.inner_text('#board-total')).group(1))
    check('level board rows add up to the board total', sum(fl) == k, f'{fl} vs {k}')
    lbl = pg.inner_text('#vp-labels')
    check('3D floor labels match the board', all(f'{n} free' in lbl for n in fl) or 'free' not in lbl, lbl[:120])
    # layers popover toggles a layer and closes on Escape
    pg.click('#layers-btn'); pg.wait_for_timeout(200)
    check('layers popover opens', pg.is_visible('#layers-pop'))
    pg.click('#layers-pop label:has([data-layer="cctv"])'); pg.wait_for_timeout(200)
    check('camera coverage layer toggles', pg.is_checked('#layers-pop [data-layer="cctv"]'))
    pg.click('#layers-pop label:has([data-layer="cctv"])'); pg.wait_for_timeout(100)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    check('layers popover closes on Escape', not pg.is_visible('#layers-pop'))
    # clicking a level on the board isolates that floor, clicking again returns to all floors
    pg.click('#floors-body [data-floor="1"]'); pg.wait_for_timeout(300)
    check('board level isolates floor', pg.get_attribute('#floor-seg [data-floorview="1"]', 'aria-pressed') == 'true')
    pg.click('#floors-body [data-floor="1"]'); pg.wait_for_timeout(300)
    check('board level toggles back to all floors', pg.get_attribute('#floor-seg [data-floorview="all"]', 'aria-pressed') == 'true')
    # select vehicle -> phone + reasoning
    pg.click('[data-act="pick-latest"]'); pg.wait_for_timeout(600)
    code = pg.inner_text('#side-body .code')
    check('selection updates driver preview', code in pg.inner_text('#phone-screen'), code)
    pg.click('[data-tab="reasoning"]'); pg.wait_for_timeout(300)
    check('reasoning shows candidates', pg.locator('#side-body .cand').count() >= 1)
    # floor controls
    pg.click('#floor-seg [data-floorview="2"]'); pg.wait_for_timeout(300)
    check('floor control B3 pressed', pg.get_attribute('#floor-seg [data-floorview="2"]', 'aria-pressed') == 'true')
    pg.click('#floor-seg [data-floorview="all"]')
    # operator action needs confirmation
    pg.click('[data-tab="actions"]'); pg.wait_for_timeout(300)
    pg.click('[data-act="review-action"][data-id="later"]'); pg.wait_for_timeout(300)
    check('review shows confirm button', pg.locator('[data-act="confirm-action"]').count() == 1)
    pg.click('[data-act="confirm-action"]'); pg.wait_for_timeout(400)
    check('action applied after confirm', 'Applied' in pg.inner_text('#side-body'))
    # forecast: members vs non-members, live and past (sim is paused here, so the numbers are stable)
    pg.click('#rail [data-section="forecast"]'); pg.wait_for_timeout(900)
    live = pg.locator('.mem-card').first
    mem = int(live.locator('.ft-mem b').inner_text()); non = int(live.locator('.ft-non b').inner_text())
    lv = [int(x) for x in re.findall(r'(\d+) \+ (\d+)', live.locator('.mem-levels').inner_text()) for x in x]
    check('member panel levels add up to the live totals', sum(lv[0::2]) == mem and sum(lv[1::2]) == non, f'{mem}+{non} vs {lv}')
    past = pg.locator('.mem-card').nth(1)
    check('member history shows a live bar and past bars', past.locator('.mem-now').count() == 1 and past.locator('.mem-col').count() >= 2)
    # reservations: create, quota
    pg.click('#rail [data-section="reservations"]'); pg.wait_for_timeout(500)
    pg.select_option('#res-type', 'member'); pg.wait_for_timeout(100)
    pg.click('#res-form button[type="submit"]'); pg.wait_for_timeout(500)
    check('eligibility required', 'Confirm the driver is eligible' in pg.inner_text('#view-reservations'))
    pg.check('#res-elig'); pg.wait_for_timeout(100)
    pg.click('#res-form button[type="submit"]'); pg.wait_for_timeout(700)
    txt = pg.inner_text('#view-reservations')
    check('member reservation created', 'R-91 confirmed' in txt, txt[txt.find('R-9'):txt.find('R-9')+80] if 'R-9' in txt else '')
    pg.click('[data-act="res-cancel"][data-id="R-91"]'); pg.wait_for_timeout(500)
    check('cancel releases', 'R-91 cancelled' in pg.inner_text('#view-reservations'))
    # OKU assistance needs permit
    pg.click('#assist-form button[type="submit"]'); pg.wait_for_timeout(400)
    check('OKU request needs permit', 'needs an OKU permit' in pg.inner_text('#view-reservations'))
    # field validation
    pg.click('#rail [data-section="impact"]'); pg.wait_for_timeout(500)
    check('field empty state', 'Field validation — pending' in pg.inner_text('#view-impact'))
    pg.fill('#f-id', 'OBS-01'); pg.fill('#f-date', '2026-10-24'); pg.fill('#f-in', '14:05:20'); pg.fill('#f-out', '14:02:00'); pg.fill('#f-zone', 'B1 Zone A')
    pg.click('#field-form button[type="submit"]'); pg.wait_for_timeout(500)
    check('rejects reversed timestamps', 'must be after gate entry' in pg.inner_text('#view-impact'))
    pg.fill('#f-out', '14:09:02')
    pg.click('#field-form button[type="submit"]'); pg.wait_for_timeout(500)
    t = pg.inner_text('#view-impact')
    check('accepts valid observation', 'Observation OBS-01 added' in t and 'Exploratory sample' in t)
    pg.fill('#f-csv', 'observation_id,date,gate_entry,parking_complete,floor_zone,note\nOBS-02,2026-10-24,14:10:00,14:12:30,B2 Zone C,\nOBS-03,2026-13-40,14:10,14:12,B2,\nOBS-04,2026-10-24,15:00,15:03,,')
    pg.click('[data-act="field-import"]'); pg.wait_for_timeout(500)
    t = pg.inner_text('#view-impact')
    check('CSV import partial accept', '1 row imported, 2 rejected' in t, t[t.find('row'):t.find('row')+120])
    # comparison
    pg.click('[data-act="run-compare"]'); pg.wait_for_timeout(2500)
    t = pg.inner_text('#view-impact')
    check('comparison table present', 'Matched-run results' in t)
    check('field data still separate', 'Field validation · 2 observations' in t)
    check('no runtime errors', not errors, errors[:3])
    b.close()
print('SUMMARY', sum(1 for _, v in ok if v), '/', len(ok))
