from __future__ import annotations
import math, shutil, struct, subprocess, wave
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MEDIA=ROOT/'media'

def main()->int:
    MEDIA.mkdir(parents=True,exist_ok=True)
    w,h=32,24
    body=bytearray()
    for y in range(h):
        for x in range(w): body += bytes(((x*8)%256,(y*11)%256,((x+y)*5)%256))
    (MEDIA/'still.ppm').write_bytes(f'P6\n{w} {h}\n255\n'.encode()+body)
    sr=48000; n=int(sr*0.8)
    with wave.open(str(MEDIA/'pulse.wav'),'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(b''.join(struct.pack('<h',int(math.sin(2*math.pi*220*i/sr)*8000*(1 if (i//2400)%2==0 else 0))) for i in range(n)))
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        print('FFmpeg absent: still.ppm and pulse.wav generated; clip.mp4 not generated')
        return 0
    seq=MEDIA/'clipframes'; seq.mkdir(exist_ok=True)
    for f in range(24):
        b=bytearray()
        for y in range(h):
            for x in range(w): b += bytes(((x*5+f*10)%256,(y*7+f*3)%256,((x-y)*4+128+f*6)%256))
        (seq/f'frame-{f:06d}.ppm').write_bytes(f'P6\n{w} {h}\n255\n'.encode()+b)
    subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','12','-i',str(seq/'frame-%06d.ppm'),'-c:v','libx264','-pix_fmt','yuv420p',str(MEDIA/'clip.mp4')],check=True)
    shutil.rmtree(seq)
    print('demo media generated')
    return 0

if __name__=='__main__': raise SystemExit(main())
