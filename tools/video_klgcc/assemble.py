"""Concatenate rendered parts, burn captions (version A) and add music.
Usage: python assemble.py WORK OUTDIR   (WORK holds part*.mp4 and music.wav)"""
import sys, json, pathlib, subprocess, imageio_ffmpeg
ff = imageio_ffmpeg.get_ffmpeg_exe()
here = pathlib.Path(__file__).resolve().parent
w, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
def run(c): print(' '.join(map(str, c))[:200], flush=True); subprocess.run([str(x) for x in c], check=True, cwd=w)
parts = sorted(w.glob('part*.mp4'))
(w / 'parts.txt').write_text(''.join(f"file '{p.name}'\n" for p in parts))
run([ff, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'parts.txt', '-c', 'copy', 'raw.mp4'])
def ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
caps = json.loads((here / 'captions.json').read_text(encoding='utf-8'))
ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 0", "",
       "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Cap,Barlow Medium,40,&H00F6F0EB,&H00FFFFFF,&H001C110A,&H9A1C110A,0,0,0,0,100,100,0,0,4,14,0,2,260,260,36,1", "",
       "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
ass += [f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\fad(150,150)}}{t}" for a, b, t in caps]
(w / 'captions.ass').write_text('\n'.join(ass) + '\n', encoding='utf-8')
x264 = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
aac = ['-c:a', 'aac', '-b:a', '192k']
run([ff, '-y', '-loglevel', 'error', '-i', 'raw.mp4', '-i', 'music.wav', '-filter_complex',
     "[0:v]ass=captions.ass:fontsdir=fonts[v];[1:a]loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=out:st=172:d=3[a]", '-map', '[v]', '-map', '[a]', '-shortest', *x264, *aac, out / 'ParkFlow-KLGCC-demo.mp4'])
run([ff, '-y', '-loglevel', 'error', '-i', 'raw.mp4', '-i', 'music.wav', '-filter_complex',
     '[1:a]loudnorm=I=-27:TP=-8:LRA=11,afade=t=out:st=172:d=3[a]', '-map', '0:v', '-map', '[a]', '-shortest', *x264, *aac, out / 'ParkFlow-KLGCC-demo-no-captions.mp4'])
print('done', out)
