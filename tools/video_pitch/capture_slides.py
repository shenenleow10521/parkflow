"""Capture deck pages 05-09 for the pitch film: a full screenshot, a 'base' with the animated parts hidden,
and the rect of every part, at 2x so the film can zoom in without blur.
Usage: python capture_slides.py WORK   (writes WORK/slides/*.png and WORK/slides/parts.json)"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
DECK = (ROOT / 'site-consulting' / 'index-v3.html').as_uri()
out = pathlib.Path(sys.argv[1]).resolve() / 'slides'; out.mkdir(parents=True, exist_ok=True)
T = 'h2.slide-title'
def nth(base, n): return f'{base}:nth-child({n})'
PARTS = {
  'service': {'title': T, 'sub': 'p.sv-sub', 'map': 'figure.sv-map', 'howh': '.sv-how > h3',
              's1': nth('.sv-how ol > li', 1), 's2': nth('.sv-how ol > li', 2), 's3': nth('.sv-how ol > li', 3),
              'cap': '.sv-capacity', 'ben': '.sv-benefits'},
  'member': {'title': T, 'ph1': nth('.v3-phones > li', 1), 'a1': nth('.v3-phones > li', 2), 'ph2': nth('.v3-phones > li', 3),
             'a2': nth('.v3-phones > li', 4), 'ph3': nth('.v3-phones > li', 5), 'a3': nth('.v3-phones > li', 6),
             'ph4': nth('.v3-phones > li', 7), 'fnh': '.v3-fns > h3', 'fn1': '.v3-fns > div.v3-fn:nth-of-type(1)',
             'fn2': '.v3-fns > div.v3-fn:nth-of-type(2)', 'fn3': '.v3-fns > div.v3-fn:nth-of-type(3)'},
  'mechanism': {'title': T, 'col1': nth('.mc-grid > div', 1), 'arr1': nth('.mc-grid > div', 2), 'ctl': nth('.mc-grid > div', 3),
                'arr2': nth('.mc-grid > div', 4), 'col2': nth('.mc-grid > div', 5), 'ptab': '.mc-price > h4', 'pfee': '.mc-price > p',
                'ptbl': '.mc-price .mc-tblwrap', 'pbox': '.mc-price .v4-box', 'rule': '.v3-sowhat'},
  'admission': {'title': T, 'lh': '.rh-left > h3', 'chart': '.rh-left > svg', 'rh': '.rh-right > h3', 'key': '.rh-right > p.rh-key',
                **{f'{k}{i}': f'.rh-right > div.rh-row:nth-of-type({i}) {sel}' for i in (1, 2, 3) for k, sel in (('t', '.rh-time'), ('x', '.rh-body > b'), ('bar', '.rh-bar'))},
                **{f'L{i}': nth('.v4-strip > article', i) for i in (1, 2, 3, 4)}},
  'operator': {'title': T, 'fig': '.operator-composition figure', 'ah': '.operator-composition aside > h3',
               **{f'd{i}': nth('.operator-composition aside dl > div', i) for i in (1, 2, 3, 4)}, 'note': '.operator-composition aside > p.note'},
}
EXTRA = {  # rects used for highlights and flights only (not hidden)
  'service': {'c1': nth('.sv-how ol > li', 1) + ' .sv-card', 'c2': nth('.sv-how ol > li', 2) + ' .sv-card', 'c3': nth('.sv-how ol > li', 3) + ' .sv-card', 'art': '.sv-map__art'},
  'member': {'fig1': nth('.v3-phones > li', 1) + ' figure img', 'phones': '.v3-phones'},
  'mechanism': {'appcard': nth('.mc-grid > div', 1) + ' .mc-node:nth-of-type(1)', 'tbl': '.mc-price .mc-tbl'},
  'admission': {'rows': '.rh-right'},
  'operator': {'img': '.operator-composition figure img', 'dl': '.operator-composition aside dl'},
}
rect_js = """([sid, sel]) => { const s = document.querySelector('section#' + sid), R = s.getBoundingClientRect();
  const e = s.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  return [r.left - R.left, r.top - R.top, r.width, r.height].map(v => Math.round(v * 10) / 10); }"""
hide_js = """([sid, sels, on]) => { const s = document.querySelector('section#' + sid);
  sels.forEach(q => { const e = s.querySelector(q); if (e) e.style.visibility = on ? 'hidden' : ''; }); }"""
meta = {}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2)
    pg.goto(DECK); pg.wait_for_timeout(2500)
    for sid, parts in PARTS.items():
        sec = pg.locator('section#' + sid).first; sec.scroll_into_view_if_needed(); pg.wait_for_timeout(1500)
        rects = {}
        for k, q in {**parts, **EXTRA[sid]}.items():
            r = pg.evaluate(rect_js, [sid, q])
            if r is None: raise SystemExit(f'missing {sid} {k} {q}')
            rects[k] = r
        sec.screenshot(path=str(out / f'{sid}_full.png'))
        pg.evaluate(hide_js, [sid, list(parts.values()), True]); pg.wait_for_timeout(200)
        sec.screenshot(path=str(out / f'{sid}_base.png'))
        pg.evaluate(hide_js, [sid, list(parts.values()), False])
        meta[sid] = rects
        print(sid, len(parts), 'parts')
    b.close()
(out / 'parts.json').write_text(json.dumps(meta, indent=1))
