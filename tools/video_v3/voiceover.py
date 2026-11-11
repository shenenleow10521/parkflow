"""Narrate the 60-second film and mix the voice over the music bed.

Usage: python voiceover.py WORK RAW_VIDEO OUT.mp4 [VOICE]
WORK holds music.wav (tools/video/music.py WORK/music.wav 60). Each line is synthesised with edge-tts
(a neural voice, online), sped up only if it would overrun its scene slot, then placed at its start time.
"""
import asyncio, json, pathlib, subprocess, sys
import edge_tts, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = pathlib.Path(__file__).resolve().parent
work, raw, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), pathlib.Path(sys.argv[3]).resolve()
voice = sys.argv[4] if len(sys.argv) > 4 else 'en-US-AndrewNeural'
lines = json.loads((HERE / 'narration.json').read_text(encoding='utf-8'))
vo = work / 'vo'; vo.mkdir(exist_ok=True)


def dur(p):
    r = subprocess.run([FF, '-i', str(p)], capture_output=True, text=True).stderr
    h, m, s = r.split('Duration: ')[1].split(',')[0].split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


async def synth(text, path, rate):
    for attempt in range(4):  # the service occasionally returns no audio; retry
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, voice, rate=f'{rate:+d}%').save(str(path)), timeout=25); return
        except (edge_tts.exceptions.NoAudioReceived, asyncio.TimeoutError):
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'no audio for: {text}')

placed = []
for i, (t0, t1, text) in enumerate(lines):
    p, rate = vo / f'l{i:02d}.mp3', -4
    for _ in range(6):
        asyncio.run(synth(text, p, rate))
        d = dur(p)
        if d <= (t1 - t0) or rate >= 18:
            break
        rate += max(3, int(((d / (t1 - t0)) - 1) * 100) + 2)
    print(f'{t0:5.1f}-{t1:5.1f}  {d:4.2f}s  rate {rate:+d}%  {text}')
    placed.append((t0, p))

# voice track: each line delayed to its start, then summed
inputs, chains = [], []
for i, (t0, p) in enumerate(placed):
    inputs += ['-i', str(p)]
    ms = int(t0 * 1000)
    chains.append(f'[{i}:a]aresample=48000,adelay={ms}|{ms},apad=whole_dur=60[v{i}]')
mixv = ''.join(f'[v{i}]' for i in range(len(placed)))
fc = ';'.join(chains) + f';{mixv}amix=inputs={len(placed)}:normalize=0,atrim=0:60,loudnorm=I=-16:TP=-1.5:LRA=7[voice]'
subprocess.run([FF, '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc, '-map', '[voice]', '-ac', '2', str(work / 'voice.wav')], check=True)

# music ducked under the voice, then both muxed with the picture
fc = ('[1:a]aresample=48000,loudnorm=I=-22:TP=-3:LRA=11,afade=t=in:st=0:d=0.6,afade=t=out:st=57.5:d=2.5[m];'
      '[2:a]asplit=2[vk][vm];[m][vk]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[md];'
      '[md][vm]amix=inputs=2:normalize=0,alimiter=limit=0.89[a]')
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', str(raw), '-i', str(work / 'music.wav'), '-i', str(work / 'voice.wav'),
                '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                '-movflags', '+faststart', '-metadata', 'title=ParkFlow: Same Bays. Greater Value. (narrated)', str(out)], check=True)
print('wrote', out)
