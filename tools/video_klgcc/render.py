"""Render the KLGCC composition frame by frame.

  python render.py WORK --stills 3,12,24,40,58
  python render.py WORK --video part0.mp4 --from 0 --to 60

WORK must hold foot/ from extract_footage.py. Frames go to ffmpeg as JPEG at 1920x1080.
"""
import argparse, functools, http.server, pathlib, shutil, subprocess, threading, time, json
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('--stills', default=''); ap.add_argument('--video', default='')
ap.add_argument('--from', dest='t0', type=float, default=0.0); ap.add_argument('--to', dest='t1', type=float, default=None)
ap.add_argument('--fps', type=int, default=30)
a = ap.parse_args()
work = pathlib.Path(a.work).resolve()
for f in ('comp.html', 'comp.js'):
    shutil.copy(HERE / f, work / f)
shutil.copytree(HERE / 'vendor', work / 'vendor', dirs_exist_ok=True)

class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.html': 'text/html', '.jpg': 'image/jpeg'}
    def log_message(self, *x): pass
handler = functools.partial(Quiet, directory=str(work))
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_address[1]}/comp.html'
duration = a.t1 if a.t1 is not None else json.loads((HERE / 'timeline.json').read_text())['duration']

with sync_playwright() as p:
    br = p.chromium.launch(args=['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
    pg = br.new_page(viewport={'width': 1920, 'height': 1080})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url)
    try:
        pg.wait_for_function('window.seek !== undefined', timeout=30000)
    except Exception:
        print('LOAD FAILED', errs); raise
    pg.evaluate('window.ready')
    print('STATS', pg.evaluate('JSON.stringify(window.STATS)'))
    if a.stills:
        out = work / 'stills'; out.mkdir(exist_ok=True)
        for t in [float(x) for x in a.stills.split(',')]:
            pg.evaluate(f'window.seek({t})')
            pg.screenshot(path=str(out / f'still_{t:06.1f}.png'))
            print('still', t)
    if a.video:
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        proc = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(a.fps), '-c:v', 'mjpeg', '-i', '-',
                                 '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', str(work / a.video)], stdin=subprocess.PIPE)
        k0, k1 = round(a.t0 * a.fps), round(duration * a.fps)
        st = time.time()
        for k in range(k0, k1):
            pg.evaluate(f'window.seek({k / a.fps})')
            proc.stdin.write(pg.screenshot(type='jpeg', quality=93))
            if (k - k0) % 300 == 0:
                print(f'frame {k}/{k1}  {time.time() - st:.0f}s', flush=True)
        proc.stdin.close(); proc.wait()
        print('wrote', work / a.video)
    print('ERRORS', errs[:20])
    br.close()
srv.shutdown()
