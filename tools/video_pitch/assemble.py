"""Join the rendered halves, encode the picture once, and mux both soundtracks.
Usage: python assemble.py WORK OUTDIR
WORK holds raw0.mp4, raw1.mp4 (render_pitch.py) and mix_narrated.wav, mix_music.wav (audio.py)."""
import pathlib, subprocess, sys, imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
w, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
def run(c): subprocess.run([str(x) for x in c], check=True, cwd=w)
(w / 'parts.txt').write_text("file 'raw0.mp4'\nfile 'raw1.mp4'\n")
run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'parts.txt', '-c', 'copy', 'raw.mp4'])
# about 4.5 Mbit/s: sharp text on the slides, small enough for GitHub (< 100 MB per file)
run([FF, '-y', '-loglevel', 'error', '-i', 'raw.mp4', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-maxrate', '6M', '-bufsize', '12M',
     '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', '-an', 'picture.mp4'])
meta = ['-metadata', 'title=ParkFlow: how the Priority Zone works', '-metadata', 'comment=Team Hexa, Universiti Malaya. Concept simulation; layout reconstructed from site footage.']
for name, mix in (('ParkFlow-Pitch-2min.mp4', 'mix_narrated.wav'), ('ParkFlow-Pitch-2min-music-only.mp4', 'mix_music.wav')):
    run([FF, '-y', '-loglevel', 'error', '-i', 'picture.mp4', '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
         '-shortest', '-movflags', '+faststart', *meta, out / name])
    print('wrote', out / name)
