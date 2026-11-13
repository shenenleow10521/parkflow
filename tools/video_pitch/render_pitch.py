"""Render the pitch compositor (pitch.html) frame by frame.

  python render_pitch.py WORK --stills 2,8,24             # PNG stills for review
  python render_pitch.py WORK --video raw0.mp4 --from 0 --to 60

WORK must hold slides/ (capture_slides.py), twin/ and twin_meta.json (render_twin.py).
"""
import argparse, base64, functools, http.server, json, pathlib, shutil, subprocess, threading, time
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--stills', default=''); ap.add_argument('--video', default='')
ap.add_argument('--from', dest='t0', type=float, default=0.0); ap.add_argument('--to', dest='t1', type=float, default=120.0); ap.add_argument('--fps', type=int, default=30)
a = ap.parse_args()
work = pathlib.Path(a.work).resolve()
for f in ('pitch.html', 'pitch.js'):
    shutil.copy(HERE / f, work / f)
parts = json.loads((work / 'slides' / 'parts.json').read_text())
meta = json.loads((work / 'twin_meta.json').read_text())
frames = sorted(int(p.stem) for p in (work / 'twin').glob('*.jpg'))
init = f'window.PARTS = {json.dumps(parts)}; window.META = {json.dumps(meta)}; window.TWIN_FRAMES = {json.dumps(frames)};'


class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.jpg': 'image/jpeg', '.png': 'image/png'}
    def log_message(self, *x): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(work)))
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    br = p.chromium.launch(args=['--force-color-profile=srgb'])
    ctx = br.new_context(viewport={'width': 1920, 'height': 1080})
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.add_init_script(init)
    pg.goto(f'http://127.0.0.1:{srv.server_address[1]}/pitch.html')
    pg.wait_for_function('window.seek !== undefined', timeout=60000)
    pg.evaluate('window.ready')
    cdp = ctx.new_cdp_session(pg)

    def shot(t, fmt='jpeg'):
        pg.evaluate(f'window.seek({t:.5f})')
        r = cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 95} if fmt == 'jpeg' else {'format': 'png'})
        return base64.b64decode(r['data'])

    if a.stills:
        out = work / 'pstills'; out.mkdir(exist_ok=True)
        for t in [float(x) for x in a.stills.split(',') if x]:
            (out / f'p{t:07.2f}.png').write_bytes(shot(t, 'png'))
        print('stills done')
    if a.video:
        ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(a.fps), '-c:v', 'mjpeg', '-i', '-',
                               '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', str(work / a.video)], stdin=subprocess.PIPE)
        k0, k1 = round(a.t0 * a.fps), round(a.t1 * a.fps); st = time.time()
        for k in range(k0, k1):
            ff.stdin.write(shot(k / a.fps))
            if (k - k0) % 300 == 0:
                print(f'frame {k}/{k1}  {time.time() - st:.0f}s', flush=True)
        ff.stdin.close(); ff.wait(); print('wrote', a.video, f'{time.time() - st:.0f}s')
    print('ERRORS', errs[:10])
    br.close()
srv.shutdown()
