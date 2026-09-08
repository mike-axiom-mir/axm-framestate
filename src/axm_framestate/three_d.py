from __future__ import annotations
from pathlib import Path
from typing import Any

CORDIC_SCALE=1_000_000
ATAN_MDEG=[45000,26565,14036,7125,3576,1790,895,448,224,112,56,28,14,7,3,2]
K_INV=607253

def sincos_mdeg(angle:int)->tuple[int,int]:
    # normalize to [-180,180], fold to [-90,90]
    a=((int(angle)+180000)%360000)-180000; sign_s=1; sign_c=1
    if a>90000: a=180000-a; sign_c=-1
    elif a<-90000: a=-180000-a; sign_c=-1; sign_s=-1
    x=K_INV; y=0; z=a
    for i,atan in enumerate(ATAN_MDEG):
        di=1 if z>=0 else -1; xn=x-di*(y>>i); yn=y+di*(x>>i); z-=di*atan; x,y=xn,yn
    return sign_s*y,sign_c*x

def rotate_xyz(v:tuple[int,int,int],rx:int,ry:int,rz:int)->tuple[int,int,int]:
    x,y,z=v; sx,cx=sincos_mdeg(rx); sy,cy=sincos_mdeg(ry); sz,cz=sincos_mdeg(rz)
    y,z=(y*cx-z*sx)//CORDIC_SCALE,(y*sx+z*cx)//CORDIC_SCALE
    x,z=(x*cy+z*sy)//CORDIC_SCALE,(-x*sy+z*cy)//CORDIC_SCALE
    x,y=(x*cz-y*sz)//CORDIC_SCALE,(x*sz+y*cz)//CORDIC_SCALE
    return x,y,z

def parse_obj(path:Path)->dict[str,Any]:
    verts=[]; uvs=[]; faces=[]
    for line in Path(path).read_text(encoding='utf-8',errors='replace').splitlines():
        s=line.strip()
        if not s or s.startswith('#'): continue
        p=s.split()
        if p[0]=='v' and len(p)>=4: verts.append(tuple(int(round(float(c)*1000)) for c in p[1:4]))
        elif p[0]=='vt' and len(p)>=3: uvs.append((int(round(float(p[1])*1_000_000)),int(round(float(p[2])*1_000_000))))
        elif p[0]=='f' and len(p)>=4:
            refs=[]
            for tok in p[1:]:
                c=tok.split('/'); vi=int(c[0]); vi=vi-1 if vi>0 else len(verts)+vi; ti=None
                if len(c)>1 and c[1]: ti=int(c[1]); ti=ti-1 if ti>0 else len(uvs)+ti
                refs.append((vi,ti))
            for j in range(1,len(refs)-1): faces.append((refs[0],refs[j],refs[j+1]))
    if not verts or not faces: raise ValueError(f'OBJ has no renderable geometry: {path}')
    return {'vertices':verts,'uvs':uvs,'faces':faces}

def cube_mesh()->dict[str,Any]:
    v=[(-1000,-1000,-1000),(1000,-1000,-1000),(1000,1000,-1000),(-1000,1000,-1000),(-1000,-1000,1000),(1000,-1000,1000),(1000,1000,1000),(-1000,1000,1000)]
    fs=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(3,2,6),(3,6,7),(1,5,6),(1,6,2),(0,3,7),(0,7,4)]
    return {'vertices':v,'uvs':[],'faces':[tuple((i,None) for i in f) for f in fs]}

def project_vertex(v:tuple[int,int,int],cx:int,cy:int,depth:int,size:int,canvas_w:int,canvas_h:int)->tuple[int,int,int]:
    x,y,z=v; zz=max(80,depth+z*size//1000); focal=min(canvas_w,canvas_h)*2
    sx=canvas_w//2+cx+(x*size//1000)*focal//zz; sy=canvas_h//2+cy-(y*size//1000)*focal//zz
    return sx,sy,zz
