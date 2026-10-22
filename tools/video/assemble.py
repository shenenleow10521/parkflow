"""Mux the rendered picture with music and captions into the deliverables.

Usage: python3 tools/video/assemble.py WORK
Expects WORK/video_raw.mp4 (from render.py parts + concat), WORK/music.wav and WORK/captions.ass.
Writes:
  ParkFlow-demo.mp4                 version A: music + burned-in captions, ready to submit
  ParkFlow-demo-for-voiceover.mp4   version B: no captions, music lowered as a bed for a recorded voice
"""
import sys, subprocess, pathlib

w = pathlib.Path(sys.argv[1]).resolve()
raw, music, ass = w / 'video_raw.mp4', w / 'music.wav', w / 'captions.ass'


def run(cmd):
    print(' '.join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


x264 = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1',
        '-x264-params', 'keyint=60:aq-mode=3', '-movflags', '+faststart']
aac = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
meta = ['-metadata', 'title=ParkFlow: reserve capacity, not parking bays', '-metadata', 'comment=Sime Darby Property University Hackathon 2026 demo']

# A: captions burned in (libass), music at about -16 LUFS
run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-i', music, '-filter_complex',
     f"[0:v]ass='{ass}'[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]", '-map', '[v]', '-map', '[a]', '-shortest', *x264, *aac, *meta, w / 'ParkFlow-demo.mp4'])
# B: clean picture, music as a quiet bed (about -27 LUFS) under a voice that will sit near -16 LUFS
run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-i', music, '-filter_complex',
     '[1:a]loudnorm=I=-27:TP=-8:LRA=11[a]', '-map', '0:v', '-map', '[a]', '-shortest', *x264, *aac, *meta, w / 'ParkFlow-demo-for-voiceover.mp4'])
print('done')
