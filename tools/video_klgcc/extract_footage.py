"""Extract the footage frames the composition needs: one JPEG per composition frame inside each footage window.
Usage: python extract_footage.py VIDEO.MOV WORK"""
import sys, json, pathlib, cv2
here = pathlib.Path(__file__).resolve().parent
tl = json.loads((here / 'timeline.json').read_text())
src, work = sys.argv[1], pathlib.Path(sys.argv[2]); out = work / 'foot'; out.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(src); sfps = cap.get(cv2.CAP_PROP_FPS); fps = tl['fps']
want = {}
for seg in tl['footage']:
    for k in range(round(seg['t0'] * fps), round(seg['t1'] * fps)):
        u = (k / fps - seg['t0']) / (seg['t1'] - seg['t0'])
        want.setdefault(min(int((seg['s0'] + u * (seg['s1'] - seg['s0'])) * sfps), int(cap.get(7)) - 1), []).append(k)
i, n = 0, 0
last = max(want)
while i <= last:
    ok, f = cap.read()
    if not ok: break
    if i in want:
        f = cv2.resize(f, (540, 960), interpolation=cv2.INTER_AREA)
        for k in want[i]:
            cv2.imwrite(str(out / f'{k:05d}.jpg'), f, [cv2.IMWRITE_JPEG_QUALITY, 88]); n += 1
    i += 1
print('wrote', n, 'frames to', out)
