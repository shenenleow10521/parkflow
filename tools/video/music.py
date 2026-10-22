"""Original background score for the ParkFlow demo video, synthesised with numpy (no samples, royalty free).

Usage: python3 tools/video/music.py OUT.wav [duration_s]
D major, 100 BPM, vi-IV-I-V. Layers enter and leave with the video's chapters.
"""
import sys, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 298.0
N = int(DUR * SR)
BPM = 100.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_points(points):
    """Piecewise-linear automation over the whole track: [(t, value), ...]."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return np.interp(t_all, xs, ys).astype(np.float32)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def place(dst, src, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(dst) or i + len(src) <= 0:
        return
    s0 = max(0, -i)
    j = min(len(dst), i + len(src))
    dst[max(i, 0):j] += src[s0:s0 + j - max(i, 0)] * gain


CHORDS = [  # (bass midi, pad notes)
    (47, [59, 62, 66, 69]),  # Bm7
    (43, [55, 59, 62, 66]),  # Gmaj7
    (50, [57, 62, 66, 69]),  # D
    (45, [57, 61, 64, 69]),  # A
]
nbars = int(np.ceil(DUR / BAR)) + 1


def chord_at(bar):
    return CHORDS[bar % 4]


# ---------------------------------------------------------------- pad (detuned saws, two filter states)
pad = np.zeros(N, np.float32)
padR = np.zeros(N, np.float32)
for b in range(nbars):
    t0 = b * BAR
    L = BAR + 1.6
    tt = np.arange(int(L * SR)) / SR
    e = np.minimum(1, tt / 0.9) * np.where(tt > BAR, np.exp(-(tt - BAR) / 0.55), 1.0)
    segL = np.zeros_like(tt)
    segR = np.zeros_like(tt)
    for m in chord_at(b)[1]:
        for k, d in enumerate((-0.11, 0.0, 0.12)):
            f = hz(m) * 2 ** (d / 12)
            ph = rng.random()
            saw = 2 * ((tt * f + ph) % 1.0) - 1
            w = 0.6 if k == 1 else 0.45
            if k == 0:
                segL += saw * w
            elif k == 2:
                segR += saw * w
            else:
                segL += saw * w * 0.7
                segR += saw * w * 0.7
    place(pad, (segL * e).astype(np.float32), t0)
    place(padR, (segR * e).astype(np.float32), t0)
pad_dark = np.stack([lp(pad, 650, 2), lp(padR, 650, 2)])
pad_bright = np.stack([lp(pad, 2400, 2), lp(padR, 2400, 2)])
bright = env_points([(0, 0.0), (5, 0.08), (17.8, 0.2), (18.0, 0.0), (21.2, 0.4), (24, 0.3), (50, 0.35), (120, 0.55), (164, 0.65), (222, 0.6), (250, 0.8), (288, 0.7), (299, 0.3)])
pad_mix = pad_dark * (1 - bright) + pad_bright * bright
pad_lvl = env_points([(0, 0), (1.2, 0.6), (5, 0.5), (17.6, 0.7), (18.0, 0.15), (21.0, 0.15), (21.3, 0.8), (24, 0.55), (288, 0.6), (296, 0.45), (299, 0)])
pad_mix *= pad_lvl * 0.075

# ---------------------------------------------------------------- bass (eighths on the root)
bass = np.zeros(N, np.float32)
eighth = BEAT / 2
for b in range(nbars):
    root = hz(chord_at(b)[0] - 12)
    for k in range(8):
        t0 = b * BAR + k * eighth
        L = eighth * 0.95
        tt = np.arange(int(L * SR)) / SR
        e = np.minimum(1, tt / 0.006) * (0.55 + 0.45 * np.exp(-tt / 0.08)) * np.minimum(1, (L - tt) / 0.02)
        x = np.sin(2 * np.pi * root * tt) + 0.5 * np.sin(4 * np.pi * root * tt)
        place(bass, (np.tanh(1.6 * x) * e).astype(np.float32), t0, 1.0 if k % 2 == 0 else 0.75)
bass_lvl = env_points([(0, 0), (5, 0), (6, 0.4), (17.6, 0.6), (17.9, 0), (21.2, 0), (24, 0.5), (50, 0.55), (120, 0.8), (200, 0.55), (222, 0.8), (288, 0.4), (291, 0), (299, 0)])
bass = lp(bass, 900) * bass_lvl * 0.12

# ---------------------------------------------------------------- pluck arpeggio (16ths) with ping-pong delay
def pluck(f, L=0.7):
    tt = np.arange(int(L * SR)) / SR
    e = np.exp(-tt / 0.17) * np.minimum(1, tt / 0.003)
    return ((np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt / 0.05) + 0.12 * np.sin(6 * np.pi * f * tt) * np.exp(-tt / 0.03)) * e).astype(np.float32)


arp = np.zeros(N, np.float32)
six = BEAT / 4
PAT = [0, 1, 2, 3, 2, 1, 2, 3, 0, 2, 1, 3, 2, 3, 1, 2]
cache = {}
for b in range(nbars):
    notes = [m + 12 for m in chord_at(b)[1]]
    for k in range(16):
        m = notes[PAT[k]]
        if m not in cache:
            cache[m] = pluck(hz(m))
        place(arp, cache[m], b * BAR + k * six, 1.0 if k % 4 == 0 else 0.62)
arp_lvl = env_points([(0, 0), (22, 0), (24.5, 0.45), (92, 0.6), (120, 0.75), (200, 0.55), (222, 0.8), (288, 0.5), (292, 0), (299, 0)])
arp = lp(arp, 5200) * arp_lvl * 0.06
d = int(BEAT * 0.75 * SR)
arpL = arp.copy()
arpR = np.zeros_like(arp)
fb = 0.38
src = arp.copy()
for rep in range(5):
    src = np.concatenate([np.zeros(d, np.float32), src[:-d]]) * fb
    if rep % 2 == 0:
        arpR += src
    else:
        arpL += src
arp_st = np.stack([arpL, arpR])

# ---------------------------------------------------------------- drums
def kick_t():
    L = 0.42
    tt = np.arange(int(L * SR)) / SR
    f = 46 + 90 * np.exp(-tt * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-tt * 7.5) + 0.25 * np.exp(-tt * 300) * rng.standard_normal(len(tt))).astype(np.float32)


KICK = kick_t()
HAT = (hp(rng.standard_normal(int(0.06 * SR)), 7500, 4) * np.exp(-np.arange(int(0.06 * SR)) / SR / 0.014)).astype(np.float32)
_c = bp(rng.standard_normal(int(0.25 * SR)), 900, 3200, 2)
_tt = np.arange(len(_c)) / SR
CLAP = (_c * (np.exp(-_tt / 0.05) + 0.6 * np.exp(-np.maximum(0, _tt - 0.012) / 0.05) * (_tt > 0.012))).astype(np.float32)

kick = np.zeros(N, np.float32)
hat = np.zeros(N, np.float32)
clap = np.zeros(N, np.float32)
kick_times = []
SECT = [(5, 17.8, 'half'), (50, 120, 'half'), (120, 200, 'full'), (200, 222, 'half'), (222, 288, 'full')]
for b in range(nbars):
    for q in range(4):
        tq = b * BAR + q * BEAT
        mode = next((m for a, z, m in SECT if a <= tq < z), None)
        if not mode:
            continue
        if mode == 'full' or q in (0, 2):
            place(kick, KICK, tq)
            kick_times.append(tq)
        if mode == 'full':
            place(hat, HAT, tq + BEAT / 2, 1.0)
            place(hat, HAT, tq + BEAT / 4 * 3, 0.35)
            if q in (1, 3):
                place(clap, CLAP, tq)
        else:
            place(hat, HAT, tq + BEAT / 2, 0.6)
drum_lvl = env_points([(0, 0), (4.9, 0), (5, 0.55), (17.8, 0.55), (17.9, 0), (49.5, 0), (50, 0.6), (120, 1), (287, 1), (288.5, 0), (299, 0)])
kick *= drum_lvl * 0.42
hat *= drum_lvl * 0.035
clap *= drum_lvl * 0.06

# sidechain duck from the kicks
duck = np.ones(N, np.float32)
for kt in kick_times:
    i = int(kt * SR)
    L = int(0.32 * SR)
    j = min(N, i + L)
    tt = np.arange(j - i) / SR
    duck[i:j] = np.minimum(duck[i:j], 1 - 0.38 * np.exp(-tt / 0.11))
duck = 1 - (1 - duck) * drum_lvl

# ---------------------------------------------------------------- bell motif (impact to close)
def bell(f, L=2.2):
    tt = np.arange(int(L * SR)) / SR
    x = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.9) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt / 0.25) + 0.2 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt / 0.1)
    return (x * np.minimum(1, tt / 0.002)).astype(np.float32)


bellv = np.zeros(N, np.float32)
MOTIF = [(0, 78), (1.5, 81), (2, 83), (3, 86), (4.5, 83), (6, 81), (7, 78)]  # beats, midi: F#5 A5 B5 D6
for start in np.arange(250 - 250 % (2 * BAR) + 2 * BAR, 286, 2 * BAR):
    for bt, m in MOTIF:
        place(bellv, bell(hz(m)), start + bt * BEAT, 0.8)
for bt, m in [(0, 74), (0.5, 78), (1, 81), (1.5, 86)]:
    place(bellv, bell(hz(m), 3.5), 288.8 + bt * BEAT * 0.5, 0.9)
for bt, m in [(0, 78), (1, 81), (2, 83), (3, 86)]:  # title sparkle
    place(bellv, bell(hz(m), 2.5), 21.3 + bt * 0.22, 0.6)
bellv *= 0.05

# ---------------------------------------------------------------- transitions: risers and sub hits
fx = np.zeros(N, np.float32)
def riser(t_hit, L=1.8, g=1.0):
    n = int(L * SR)
    tt = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 1800, 9000, 2) * (tt / L) ** 2.2
    place(fx, x.astype(np.float32), t_hit - L, 0.05 * g)


def hit(t0, g=1.0):
    L = 2.6
    tt = np.arange(int(L * SR)) / SR
    f = 32 + 36 * np.exp(-tt * 5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.6)
    place(fx, x.astype(np.float32), t0, 0.32 * g)


for th in (24, 50, 92, 120, 164, 200, 222, 250):
    riser(th, 1.5, 0.7)
for th in (18.0, 21.2, 288):
    riser(th, 2.2, 1.0)
    hit(th, 0.9)
hit(0.6, 0.7)
# a clock tick on every beat while Aina is circling
for tq in np.arange(5.0, 17.8, BEAT):
    place(fx, (HAT * 9).astype(np.float32), tq, 0.05)

# ---------------------------------------------------------------- mix, reverb, master
dry = pad_mix * duck + np.stack([bass * duck, bass * duck]) + arp_st + np.stack([kick, kick]) + np.stack([hat * 0.8, hat]) + np.stack([clap, clap * 0.9]) + np.stack([bellv * 0.9, bellv]) + np.stack([fx, fx])
send = pad_mix * 0.5 + arp_st * 0.8 + np.stack([bellv, bellv]) * 1.2 + np.stack([clap, clap]) * 0.6
irL = int(2.4 * SR)
tt = np.arange(irL) / SR
ir = np.stack([lp(rng.standard_normal(irL), 5000) * np.exp(-tt / 0.5), lp(rng.standard_normal(irL), 5000) * np.exp(-tt / 0.5)])
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
wet = np.stack([fftconvolve(send[0], ir[0])[:N], fftconvolve(send[1], ir[1])[:N]])
mix = dry + 0.32 * wet
mix = hp(mix, 28)
fade = env_points([(0, 0), (0.6, 1), (DUR - 2.5, 1), (DUR, 0)])
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.89
out = (np.clip(mix.T, -1, 1) * 32767).astype(np.int16)
import wave
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(out.tobytes())
print('wrote', sys.argv[1], round(DUR, 1), 's')
