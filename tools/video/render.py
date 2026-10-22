"""Render the demo video composition (tools/video/comp.html) frame by frame.

Usage:
  python3 tools/video/render.py WORK --stills 3.5,20,45        # PNG stills for review
  python3 tools/video/render.py WORK --video out.mp4 [--from 0 --to 298] [--part 0/2]

WORK must contain cap/ from capture.py. Frames are piped to ffmpeg as JPEG (1920x1080, 30 fps).
"""
import sys, json, re, time, base64, shutil, argparse, pathlib, subprocess
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('work')
ap.add_argument('--stills', default='')
ap.add_argument('--video', default='')
ap.add_argument('--from', dest='t0', type=float, default=0.0)
ap.add_argument('--to', dest='t1', type=float, default=None)
ap.add_argument('--part', default='0/1')
ap.add_argument('--fps', type=int, default=30)
a = ap.parse_args()

work = pathlib.Path(a.work).resolve()
shutil.copy(HERE / 'comp.html', work / 'comp.html')
script = json.loads((HERE / 'script.json').read_text())
layout = json.loads((work / 'cap' / 'layout_operator.json').read_text()) if (work / 'cap' / 'layout_operator.json').exists() else {}
facts = json.loads((work / 'cap' / 'facts.json').read_text()) if (work / 'cap' / 'facts.json').exists() else {}
m = re.search(r'Scenario projection, per year\s*([\d.,]+)\s*t', facts.get('impact_text', ''))
if m:
    facts['co2_year_t'] = f"{float(m.group(1).replace(',', '')):.1f}"
def jl(name):
    q = work / 'cap' / name
    return json.loads(q.read_text()) if q.exists() else {}


init = (f'window.SCRIPT = {json.dumps(script)}; window.LAYOUT = {json.dumps(layout)}; window.FACTS = {json.dumps(facts)};'
        f'window.FACTS2 = {json.dumps(jl("facts2.json"))}; window.LAYOUT2 = {json.dumps(jl("layout2.json"))};'
        f'window.TAPS = {json.dumps(jl("taps2.json"))}; window.FORECAST = {json.dumps(jl("forecast_1408.json") or None)};')
duration = a.t1 if a.t1 is not None else script['duration']


def log(*x):
    print(time.strftime('%H:%M:%S'), *x, flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(args=['--disable-gpu', '--force-color-profile=srgb', '--disable-lcd-text'])
    ctx = b.new_context(viewport={'width': 1920, 'height': 1080})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.add_init_script(init)
    pg.goto((work / 'comp.html').as_uri())
    pg.evaluate('window.ready')
    cdp = ctx.new_cdp_session(pg)

    def frame(t, fmt='jpeg', q=94):
        pg.evaluate(f'window.seek({t:.5f})')
        r = cdp.send('Page.captureScreenshot', {'format': fmt, 'quality': q} if fmt == 'jpeg' else {'format': 'png'})
        return base64.b64decode(r['data'])

    if a.stills:
        out = work / 'stills'
        out.mkdir(exist_ok=True)
        for t in [float(x) for x in a.stills.split(',') if x]:
            (out / f't{t:07.2f}.png').write_bytes(frame(t, 'png'))
        log('stills done', a.stills)
    if a.video:
        k, n = [int(x) for x in a.part.split('/')]
        f0, f1 = int(round(a.t0 * a.fps)), int(round(duration * a.fps))
        span = f1 - f0
        s0, s1 = f0 + span * k // n, f0 + span * (k + 1) // n
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(a.fps), '-c:v', 'mjpeg', '-i', '-',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-tune', 'animation',
               '-x264-params', 'keyint=60', '-movflags', '+faststart', a.video]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t_start = time.time()
        for i in range(s0, s1):
            ff.stdin.write(frame(i / a.fps))
            if (i - s0) % 150 == 149:
                el = time.time() - t_start
                log(f'frame {i - s0 + 1}/{s1 - s0}  {el / (i - s0 + 1):.3f}s/frame  eta {el / (i - s0 + 1) * (s1 - i) / 60:.1f} min')
        ff.stdin.close()
        ff.wait()
        log('video done', a.video, s0, s1)
    if errs:
        print('PAGE ERRORS:', errs[:8])
    b.close()
