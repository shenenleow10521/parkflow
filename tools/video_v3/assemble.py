"""Join the rendered halves and add the music bed.
Usage: python assemble.py WORK OUT.mp4   (WORK holds part0.mp4, part1.mp4 and music.wav from tools/video/music.py)"""
import sys, pathlib, subprocess, imageio_ffmpeg
ff = imageio_ffmpeg.get_ffmpeg_exe()
w, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
def run(c): print(' '.join(map(str, c))[:160], flush=True); subprocess.run([str(x) for x in c], check=True, cwd=w)
parts = sorted(w.glob('part*.mp4'))
(w / 'parts.txt').write_text(''.join(f"file '{p.name}'\n" for p in parts))
run([ff, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'parts.txt', '-c', 'copy', 'raw.mp4'])
run([ff, '-y', '-loglevel', 'error', '-i', 'raw.mp4', '-i', 'music.wav', '-filter_complex',
     '[1:a]loudnorm=I=-17:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.6,afade=t=out:st=57.5:d=2.5[a]', '-map', '0:v', '-map', '[a]', '-shortest',
     '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
     '-c:a', 'aac', '-b:a', '192k', '-metadata', 'title=ParkFlow: Same Bays. Greater Value.', '-metadata', 'comment=Team Hexa, Universiti Malaya. Concept simulation.', out])
print('done', out)
