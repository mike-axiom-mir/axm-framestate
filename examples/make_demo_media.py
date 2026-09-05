from __future__ import annotations
import math, shutil, struct, subprocess, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent; M=ROOT/'media'

def ppm(path,w,h,fn):
    b=bytearray()
    for y in range(h):
        for x in range(w): b.extend(fn(x,y))
    path.write_bytes(f'P6\n{w} {h}\n255\n'.encode()+b)

def main():
    M.mkdir(parents=True,exist_ok=True);w,h=64,40
    ppm(M/'still.ppm',w,h,lambda x,y:((20+x*3)%256,(30+y*5)%256,(120+x+y*2)%256))
    ppm(M/'texture.ppm',32,32,lambda x,y:((230 if (x//4+y//4)%2==0 else 40),(80+x*4)%256,(220-y*5)%256))
    ppm(M/'mask.ppm',w,h,lambda x,y:((255 if ((x-w//2)**2+(y-h//2)**2)<(min(w,h)//2)**2 else 0,)*3))
    ppm(M/'green_card.ppm',w,h,lambda x,y:((20,230,30) if x<10 or x>w-11 or y<7 or y>h-8 else (255,120+(x*2)%100,40+(y*3)%120)))
    sr=48000;n=sr*2
    with wave.open(str(M/'pulse.wav'),'wb') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(sr);wf.writeframes(b''.join(struct.pack('<h',int(math.sin(2*math.pi*(180+(i//6000)*20)*i/sr)*7000*(1 if (i//2400)%2==0 else .35))) for i in range(n)))
    obj='''# textured pyramid\nv -1 -1 -1\nv 1 -1 -1\nv 1 -1 1\nv -1 -1 1\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nvt 0.5 0.5\nf 1/1 4/4 3/3\nf 1/1 3/3 2/2\nf 1/1 2/2 5/5\nf 2/2 3/3 5/5\nf 3/3 4/4 5/5\nf 4/4 1/1 5/5\n''';(M/'pyramid.obj').write_text(obj)
    seq=M/'clipframes';seq.mkdir(exist_ok=True)
    for f in range(36): ppm(seq/f'frame-{f:06d}.ppm',w,h,lambda x,y,f=f:((x*4+f*8)%256,(y*5+f*3)%256,((x-y)*3+128+f*4)%256))
    ff=shutil.which('ffmpeg')
    if ff:
        subprocess.run([ff,'-y','-loglevel','error','-framerate','12','-i',str(seq/'frame-%06d.ppm'),'-c:v','libx264','-pix_fmt','yuv420p',str(M/'clip.mp4')],check=True)
    shutil.rmtree(seq)
    print('demo media ready')
if __name__=='__main__':main()
