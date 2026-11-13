"""Audio for the pitch film v2: narration (edge-tts, online neural voice), generated sound effects and the music bed.

Usage: python audio.py WORK [VOICE]
Writes WORK/mix_narrated.wav (voice + ducked music + effects) and WORK/mix_music.wav (music + effects).
"""
import asyncio, json, pathlib, subprocess, sys, wave
import numpy as np
import edge_tts, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = pathlib.Path(__file__).resolve().parent
work = pathlib.Path(sys.argv[1]).resolve()
voice = next((a for a in sys.argv[2:] if not a.startswith('--')), 'en-US-AndrewNeural')
REUSE = '--reuse-voice' in sys.argv and (work / 'voice.wav').exists()  # keep the narration already generated
SR, DUR = 48000, 120.0
lines = json.loads((HERE / 'narration2.json').read_text(encoding='utf-8'))
vo = work / 'vo'; vo.mkdir(exist_ok=True)


def dur(p):
    r = subprocess.run([FF, '-i', str(p)], capture_output=True, text=True).stderr
    h, m, s = r.split('Duration: ')[1].split(',')[0].split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


async def synth(text, path, rate):
    for attempt in range(5):  # the service sometimes stalls or returns nothing; retry
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, voice, rate=f'{rate:+d}%').save(str(path)), timeout=25); return
        except (edge_tts.exceptions.NoAudioReceived, asyncio.TimeoutError):
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'no audio for: {text}')

# ---------------------------------------------------------------- narration, each line fitted to its slot
if not REUSE:
    placed = []
    for i, (t0, t1, text) in enumerate(lines):
        p, rate = vo / f'l{i:02d}.mp3', -3
        for _ in range(7):
            asyncio.run(synth(text, p, rate)); d = dur(p)
            if d <= (t1 - t0) or rate >= 20: break
            rate += max(3, int(((d / (t1 - t0)) - 1) * 100) + 2)
        print(f'{t0:6.1f}-{t1:6.1f}  {d:5.2f}s  {rate:+d}%  {text}', flush=True)
        placed.append((t0, p))
    inputs, chains = [], []
    for i, (t0, p) in enumerate(placed):
        inputs += ['-i', str(p)]; ms = int(t0 * 1000)
        chains.append(f'[{i}:a]aresample={SR},adelay={ms}|{ms},apad=whole_dur={DUR}[v{i}]')
    fc = ';'.join(chains) + ';' + ''.join(f'[v{i}]' for i in range(len(placed))) + f'amix=inputs={len(placed)}:normalize=0,atrim=0:{DUR},loudnorm=I=-16:TP=-1.5:LRA=7[o]'
    subprocess.run([FF, '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc, '-map', '[o]', '-ac', '2', '-ar', str(SR), str(work / 'voice.wav')], check=True)

# ---------------------------------------------------------------- sound effects
rng = np.random.default_rng(11)
N = int(DUR * SR); fx = np.zeros((N, 2), np.float32)
def put(t, sig, pan=0.0, gain=1.0):
    i = int(t * SR); sig = sig[: max(0, N - i)] * gain
    fx[i:i + len(sig), 0] += sig * (1 - max(0, pan)); fx[i:i + len(sig), 1] += sig * (1 + min(0, pan))
def env(n, a, r):
    e = np.ones(n, np.float32); ai, ri = int(a * SR), int(r * SR)
    e[:ai] = np.linspace(0, 1, ai); e[-ri:] = np.linspace(1, 0, ri) ** 2; return e
def bandnoise(n, f0, f1, q=0.35):
    """noise through a bandpass that sweeps f0 -> f1 (one-pole pair, cheap)"""
    x = rng.standard_normal(n).astype(np.float32); y = np.zeros(n, np.float32); lo = hi = 0.0
    fs = np.geomspace(f0, f1, n)
    for k in range(0, n, 64):
        a = 1 - np.exp(-2 * np.pi * fs[k] / SR); b = 1 - np.exp(-2 * np.pi * fs[k] * (1 + q) / SR)
        for j in range(k, min(k + 64, n)):
            lo += a * (x[j] - lo); hi += b * (x[j] - hi); y[j] = hi - lo
    return y / (np.abs(y).max() + 1e-6)
def whoosh(d=0.7, f0=300, f1=3200, g=0.5):
    n = int(d * SR); e = np.sin(np.linspace(0, np.pi, n)) ** 1.6; return bandnoise(n, f0, f1) * e * g
def tone(f, d, decay, g=0.3, harm=(1, 0.35, 0.12)):
    n = int(d * SR); t = np.arange(n) / SR
    s = sum(h * np.sin(2 * np.pi * f * (k + 1) * t) for k, h in enumerate(harm)); return (s * np.exp(-t / decay) * env(n, 0.004, 0.05) * g).astype(np.float32)
def click(g=0.35):
    n = int(0.05 * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006) * g + rng.standard_normal(n) * np.exp(-t / 0.002) * 0.15 * g).astype(np.float32)
def tick(g=0.12):
    n = int(0.02 * SR); t = np.arange(n) / SR; return (rng.standard_normal(n) * np.exp(-t / 0.003) * g).astype(np.float32)

def coin(t, g=0.11):  # a soft "earned" ding
    put(t, tone(1318, 0.7, 0.18, g)); put(t + 0.07, tone(1976, 0.8, 0.22, g * 0.8))
for t, d, f0, f1, g in [(3.55, 0.8, 200, 4000, 0.45), (9.3, 0.6, 400, 2400, 0.3), (12.95, 0.9, 250, 3200, 0.42), (19.8, 0.7, 300, 2600, 0.35),
                        (34.2, 0.8, 500, 3000, 0.35), (50.6, 0.8, 400, 3000, 0.35), (57.2, 0.75, 450, 3000, 0.35), (81.5, 0.9, 3500, 250, 0.6),
                        (83.1, 0.8, 300, 3400, 0.4), (88.7, 0.9, 2600, 300, 0.4), (95.0, 0.6, 300, 2200, 0.3), (102.4, 0.5, 2200, 400, 0.25), (115.9, 1.2, 300, 5000, 0.4)]:
    put(t, whoosh(d, f0, f1, g))
put(45.2, whoosh(0.6, 2500, 180, 0.35) + tone(110, 0.6, 0.25, 0.25)[: int(0.6 * SR)])  # controller beam drops into the 3D floor
for t in (21.7, 23.3, 25.2, 30.0):  # taps in the real driver app
    put(t, click(0.4))
put(25.45, tone(1046, 0.9, 0.35, 0.15)); put(25.57, tone(1568, 0.9, 0.4, 0.12))  # booking confirmed
coin(26.25); coin(73.25); coin(75.35)  # booking fee = new income; no-show fee kept; bay re-sold
put(82.35, tone(1200, 0.25, 0.06, 0.1, (1, 0.3)))  # plate camera scan
put(84.17, tone(880, 1.2, 0.4, 0.2)); put(84.32, tone(1318, 1.2, 0.45, 0.17))  # booking verified at the gate
put(78.6, tone(196, 0.5, 0.12, 0.22, (1, 0.6, 0.4, 0.2)))  # walk-in closed
for a, b in ((64.4, 69.0), (76.9, 78.8)):  # time-lapse ticks
    for t in np.arange(a, b, 0.11): put(float(t), tick(0.10 + 0.04 * float(np.sin(t * 9))))
for t in (37.6, 38.4, 39.2, 40.0, 54.8, 55.4, 56.0, 56.6, 104.4, 110.7):  # modules, layers, highlights
    put(t, tone(1760, 0.18, 0.04, 0.05, (1, 0.2)))
for t in (95.8, 97.6, 99.4, 101.2):  # revenue streams light up
    coin(t, 0.07)
# transitions: impact ring, flash cuts, light sweeps
put(45.8, tone(55, 0.9, 0.3, 0.45, (1, 0.5, 0.2)) + (rng.standard_normal(int(0.9 * SR)) * np.exp(-np.arange(int(0.9 * SR)) / SR / 0.06) * 0.12).astype(np.float32))
for t in (81.9, 83.5):
    put(t, whoosh(0.35, 6000, 1500, 0.3))
put(108.8, whoosh(0.6, 400, 3200, 0.3)); put(102.65, whoosh(0.5, 600, 3600, 0.22)); put(13.65, whoosh(0.5, 700, 4200, 0.2))
for i, f in enumerate((523, 659, 784, 1046)):  # end-card shimmer and the four chips
    put(118.0 + i * 0.09, tone(f, 1.6, 0.6, 0.07)); put(115.25 + i * 0.12, tone(f * 2, 0.4, 0.12, 0.05))
fx = np.clip(fx, -1, 1)
with wave.open(str(work / 'sfx.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((fx * 32767).astype('<i2').tobytes())

# ---------------------------------------------------------------- music bed and the two mixes
subprocess.run([sys.executable, str(HERE.parent / 'video' / 'music.py'), str(work / 'music120.wav'), str(DUR)], check=True)
music = '[0:a]aresample=48000,loudnorm=I={I}:TP=-3:LRA=11,afade=t=in:st=0:d=1.2,afade=t=out:st=117.8:d=2.2[m]'
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', str(work / 'music120.wav'), '-i', str(work / 'voice.wav'), '-i', str(work / 'sfx.wav'), '-filter_complex',
                music.format(I=-22) + ';[1:a]asplit=2[vk][vm];[m][vk]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[md];'
                '[2:a]volume=0.8[s];[md][vm][s]amix=inputs=3:normalize=0,alimiter=limit=0.89[a]', '-map', '[a]', '-t', str(DUR), str(work / 'mix_narrated.wav')], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', str(work / 'music120.wav'), '-i', str(work / 'sfx.wav'), '-filter_complex',
                music.format(I=-17) + ';[1:a]volume=0.8[s];[m][s]amix=inputs=2:normalize=0,alimiter=limit=0.89[a]', '-map', '[a]', '-t', str(DUR), str(work / 'mix_music.wav')], check=True)
print('wrote mix_narrated.wav and mix_music.wav')
