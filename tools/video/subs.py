"""Build captions from tools/video/script.json.

Usage: python3 tools/video/subs.py OUT_DIR
Writes captions.ass (burned into version A), parkflow-demo.srt and voiceover-script.md.
"""
import sys, json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(sys.argv[1])
S = json.loads((HERE / 'script.json').read_text())
MAXL = 50


def wrap(text, width=MAXL):
    words, lines, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = (cur + ' ' + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def balanced(text):
    """Two lines of similar length when the cue needs two."""
    if len(text) <= MAXL:
        return [text]
    words = text.split()
    best = None
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        if len(a) <= MAXL + 4 and len(b) <= MAXL + 4:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else wrap(text)


def cues():
    for t0, t1, text in S['vo']:
        if len(text) <= 2 * MAXL:
            yield t0, t1, balanced(text)
            continue
        # split into k chunks near equal length, preferring clause boundaries
        import math
        words = text.split()
        k = math.ceil(len(text) / (2 * MAXL))
        pos, acc = [], 0
        for i, w in enumerate(words[:-1]):
            acc += len(w) + 1
            pos.append((acc, i + 1, w[-1] in ',:;.'))
        cuts, used = [], 0
        for j in range(1, k):
            target = len(text) * j / k
            cand = sorted(pos, key=lambda p: abs(p[0] - target) - (14 if p[2] else 0))
            cuts.append(cand[0][1])
        cuts = sorted(set(cuts))
        chunks, prev = [], 0
        for cidx in cuts + [len(words)]:
            chunks.append(' '.join(words[prev:cidx]))
            prev = cidx
        total = sum(len(c) for c in chunks)
        t = t0
        for c in chunks:
            d = (t1 - t0) * len(c) / total
            yield t, t + d - 0.04, balanced(c)
            t += d


def ts_srt(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def ts_ass(t):
    cs = int(round(t * 100))
    return f'{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}'


C = list(cues())
srt = []
for i, (a, b, lines) in enumerate(C, 1):
    srt.append(f'{i}\n{ts_srt(a)} --> {ts_srt(b)}\n' + '\n'.join(lines) + '\n')
(out / 'parkflow-demo.srt').write_text('\n'.join(srt), encoding='utf-8')

ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080', 'WrapStyle: 2', 'ScaledBorderAndShadow: yes', '',
       '[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
       'Style: Cap,Inter,38,&H00FFFFFF,&H00FFFFFF,&H38160D08,&H38160D08,0,0,0,0,100,100,0,0,4,16,0,2,200,200,66,1',
       '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
for a, b, lines in C:
    txt = '\\N'.join(l.replace('{', '(').replace('}', ')') for l in lines)
    ass.append(f'Dialogue: 0,{ts_ass(a)},{ts_ass(b)},Cap,,0,0,0,,{{\\fad(160,160)\\b600}}{txt}')
(out / 'captions.ass').write_text('\n'.join(ass) + '\n', encoding='utf-8')

md = ['# ParkFlow demo video: voiceover script', '',
      'Read at a calm, confident pace (about 150 words a minute). Each line starts at the time shown; the video already leaves room for it.', '']
chap = {c['t0']: c for c in S['chapters']}
cur = None
for t0, t1, text in S['vo']:
    c = max([c for c in S['chapters'] if c['t0'] <= t0 + 0.01], key=lambda c: c['t0'], default=None)
    name = c['name'] if c and t0 < c['t1'] else ('Opening' if t0 < 14 else 'Close')
    if name != cur:
        md += ['', f'## {name}', '']
        cur = name
    m, s = divmod(t0, 60)
    md.append(f'- **{int(m)}:{s:04.1f}** {text}')
words = sum(len(v[2].split()) for v in S['vo'])
md += ['', f'{words} words in total.']
(out / 'voiceover-script.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
print(len(C), 'cues,', words, 'words')
