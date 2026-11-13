"""Audio for the pitch film: narration (edge-tts, online neural voice), generated sound effects and the music bed.

Usage: python audio.py WORK [VOICE]
Writes WORK/mix_narrated.wav (voice + ducked music + effects) and WORK/mix_music.wav (music + effects).
"""
import asyncio, json, pathlib, subprocess, sys, wave
import numpy as np
import edge_tts, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = pathlib.Path(__file__).resolve().parent
work = pathlib.Path(sys.argv[1]).resolve()
voice = sys.argv[2] if len(sys.argv) > 2 else 'en-US-AndrewNeural'
SR, DUR = 48000, 120.0
lines = json.loads((HERE / 'narration.json').read_text(encoding='utf-8'))
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

for t, d, f0, f1, g in [(3.55, 0.8, 200, 4000, 0.45), (11.4, 0.9, 250, 2600, 0.4), (22.95, 0.9, 300, 3600, 0.45), (29.85, 0.7, 400, 2800, 0.35),
                        (43.3, 0.8, 500, 3200, 0.35), (59.35, 0.8, 400, 3000, 0.35), (68.1, 0.75, 450, 3000, 0.35), (94.5, 0.9, 3500, 250, 0.6),
                        (104.75, 0.9, 2600, 300, 0.4), (112.95, 1.2, 300, 5000, 0.4)]:
    put(t, whoosh(d, f0, f1, g), pan=0.0)
for t in (32.50, 34.28, 35.69, 39.18):  # phone taps
    put(t, click(0.4))
put(52.2, whoosh(0.6, 2500, 180, 0.35) + np.pad(tone(110, 0.6, 0.25, 0.25), (0, 0))[: int(0.6 * SR)])  # controller beam drops into the floor
put(40.15, tone(1046, 0.9, 0.35, 0.16)); put(40.27, tone(1568, 0.9, 0.4, 0.13))  # booking confirmed
put(97.25, tone(880, 1.2, 0.4, 0.2)); put(97.4, tone(1318, 1.2, 0.45, 0.17))  # booking verified at the gate
put(86.0, tone(660, 1.0, 0.35, 0.16)); put(86.12, tone(990, 1.0, 0.4, 0.12))  # no-show released
put(89.8, tone(196, 0.5, 0.12, 0.22, (1, 0.6, 0.4, 0.2)))  # walk-in closed blip
for a, b in ((76.2, 81.3), (87.95, 90.1)):  # time-lapse clock ticks
    for t in np.arange(a, b, 0.11): put(float(t), tick(0.10 + 0.04 * float(np.sin(t * 9))))
for t in (5.75, 6.9, 8.0, 26.0, 27.8, 45.6, 47.3, 49.7, 51.2, 61.0, 63.2, 66.3, 106.9, 107.7, 108.5, 109.4, 110.6):  # highlight boxes
    put(t, tone(1760, 0.18, 0.04, 0.05, (1, 0.2)))
for i, f in enumerate((523, 659, 784, 1046)):  # end-card shimmer
    put(117.35 + i * 0.09, tone(f, 1.6, 0.6, 0.07))
fx = np.clip(fx, -1, 1)
with wave.open(str(work / 'sfx.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((fx * 32767).astype('<i2').tobytes())

# ---------------------------------------------------------------- music bed and the two mixes
subprocess.run([sys.executable, str(HERE.parent / 'video' / 'music.py'), str(work / 'music120.wav'), str(DUR)], check=True)
music = '[0:a]aresample=48000,loudnorm=I={I}:TP=-3:LRA=11,afade=t=in:st=0:d=1.2,afade=t=out:st=117.5:d=2.5[m]'
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', str(work / 'music120.wav'), '-i', str(work / 'voice.wav'), '-i', str(work / 'sfx.wav'), '-filter_complex',
                music.format(I=-22) + ';[1:a]asplit=2[vk][vm];[m][vk]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[md];'
                '[2:a]volume=0.8[s];[md][vm][s]amix=inputs=3:normalize=0,alimiter=limit=0.89[a]', '-map', '[a]', '-t', str(DUR), str(work / 'mix_narrated.wav')], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', str(work / 'music120.wav'), '-i', str(work / 'sfx.wav'), '-filter_complex',
                music.format(I=-17) + ';[1:a]volume=0.8[s];[m][s]amix=inputs=2:normalize=0,alimiter=limit=0.89[a]', '-map', '[a]', '-t', str(DUR), str(work / 'mix_music.wav')], check=True)
print('wrote mix_narrated.wav and mix_music.wav')
