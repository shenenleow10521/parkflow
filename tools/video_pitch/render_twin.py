"""Render the forked 3D film (twin/) onto the pitch timeline: one JPEG per pitch frame that shows 3D.

  python render_twin.py WORK [--part 0/2] [--only 43.3,59.4]

WORK must hold foot/ (tools/video_v3/extract_footage.py). Writes WORK/twin/NNNNN.jpg (NNNNN = pitch frame
at 30 fps) and WORK/twin_meta.json with on-screen rects the compositor flies elements from.
"""
import argparse, functools, http.server, json, pathlib, shutil, threading, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FPS = 30
# pitch time -> fork time, linear between the anchors, clamped; [range of pitch frames to render]
SEGS = {
    'zone':  ((12.0, 0.0), (23.0, 7.9), (11.8, 24.1)),  # held on the last zone frame during the dive
    'phone': ((30.2, 8.3), (44.6, 18.0), (30.0, 44.8)),
    'tint':  ((52.8, 18.15), (60.2, 24.0), (52.5, 60.6)),
    'mech':  ((68.6, 24.0), (95.0, 50.4), (68.4, 95.0)),
    'entry': ((95.0, 50.4), (106.2, 58.85), (95.0, 106.4)),
    'close': ((113.6, 58.85), (117.6, 61.85), (113.4, 117.8)),
}
META_AT = {'plate': 43.3, 'dash': 59.4, 'clock': 69.4}


def fork_time(p):
    for (a0, f0), (a1, f1), (r0, r1) in SEGS.values():
        if r0 <= p < r1:
            return min(max(f0 + (p - a0) * (f1 - f0) / (a1 - a0), min(f0, f1)), max(f0, f1))
    return None


def frames():
    ks = sorted({k for (_, _, (r0, r1)) in SEGS.values() for k in range(round(r0 * FPS), round(r1 * FPS))})
    return [k for k in ks if fork_time(k / FPS) is not None]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--part', default='0/1'); ap.add_argument('--only', default=''); ap.add_argument('--range', default='')
    a = ap.parse_args()
    work = pathlib.Path(a.work).resolve(); out = work / 'twin'; out.mkdir(parents=True, exist_ok=True)
    for f in ('comp.html', 'comp.js'):
        shutil.copy(HERE / 'twin' / f, work / f)
    shutil.copytree(HERE / 'twin' / 'vendor', work / 'vendor', dirs_exist_ok=True)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.jpg': 'image/jpeg'}
        def log_message(self, *x): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(work)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    ks = [round(float(x) * FPS) for x in a.only.split(',')] if a.only else frames()
    if a.range:
        r0, r1 = (float(x) for x in a.range.split(','))
        ks = [k for k in ks if r0 * FPS <= k < r1 * FPS]
    i, n = (int(x) for x in a.part.split('/'))
    ks = ks[i::n]
    with sync_playwright() as p:
        br = p.chromium.launch(args=['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        pg = br.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{srv.server_address[1]}/comp.html')
        pg.wait_for_function('window.seek !== undefined', timeout=30000)
        pg.evaluate('window.ready')
        print('STATS', pg.evaluate('JSON.stringify(window.STATS)'), flush=True)
        st = time.time()
        for j, k in enumerate(ks):
            pg.evaluate(f'window.seek({fork_time(k / FPS):.5f})')
            pg.screenshot(path=str(out / f'{k:05d}.jpg'), type='jpeg', quality=90)
            if j % 200 == 0:
                print(f'{j}/{len(ks)} frames  {time.time() - st:.0f}s', flush=True)
        if i == 0 and not a.only and not a.range:
            meta = {}
            for name, pt in META_AT.items():
                pg.evaluate(f'window.seek({fork_time(pt):.5f})')
                meta[name] = pg.evaluate({'plate': 'window.plateRect()',
                                          'dash': "(() => { const r = document.getElementById('dash').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()",
                                          'clock': "(() => { const r = document.getElementById('clock').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()"}[name])
            (work / 'twin_meta.json').write_text(json.dumps(meta))
            print('META', meta)
        print('done', len(ks), 'frames', f'{time.time() - st:.0f}s', 'ERRORS', errs[:10], flush=True)
        br.close()
    srv.shutdown()
