from __future__ import annotations
from typing import Any

SCALE=1_000_000
ATAN_MDEG=[45000,26565,14036,7125,3576,1790,895,448,224,112,56,28,14,7,3,2,1]
CORDIC_K=607253


def sincos_mdeg(angle:int)->tuple[int,int]:
    """Deterministic integer CORDIC. Returns (sin, cos) scaled by 1e6."""
    a=((angle+180_000)%360_000)-180_000
    sign=1
    if a>90_000:
        a-=180_000; sign=-1
    elif a<-90_000:
        a+=180_000; sign=-1
    x=CORDIC_K; y=0; z=a
    for i,atan in enumerate(ATAN_MDEG):
        if z>=0:
            x,y,z=x-(y>>i),y+(x>>i),z-atan
        else:
            x,y,z=x+(y>>i),y-(x>>i),z+atan
    return y*sign,x*sign


def _rot_x(v:tuple[int,int,int],a:int)->tuple[int,int,int]:
    s,c=sincos_mdeg(a); x,y,z=v
    return x,(y*c-z*s)//SCALE,(y*s+z*c)//SCALE

def _rot_y(v:tuple[int,int,int],a:int)->tuple[int,int,int]:
    s,c=sincos_mdeg(a); x,y,z=v
    return (x*c+z*s)//SCALE,y,(-x*s+z*c)//SCALE

def _rot_z(v:tuple[int,int,int],a:int)->tuple[int,int,int]:
    s,c=sincos_mdeg(a); x,y,z=v
    return (x*c-y*s)//SCALE,(x*s+y*c)//SCALE,z


def cube_geometry(center_x:int,center_y:int,depth:int,size:int,rx:int,ry:int,rz:int,width:int,height:int)->list[dict[str,Any]]:
    half=max(1,size//2)
    verts=[(-half,-half,-half),(half,-half,-half),(half,half,-half),(-half,half,-half),(-half,-half,half),(half,-half,half),(half,half,half),(-half,half,half)]
    world=[]
    for v in verts:
        q=_rot_z(_rot_y(_rot_x(v,rx),ry),rz)
        world.append((q[0]+center_x,q[1]+center_y,q[2]+depth))
    focal=max(32,min(width,height)*2)
    projected=[]
    for x,y,z in world:
        zz=max(1,z)
        projected.append((width//2 + x*focal//zz,height//2 - y*focal//zz,zz))
    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)]
    shade=[700,1000,780,900,860,740]
    rows=[]
    for i,face in enumerate(faces):
        pts=[projected[j] for j in face]
        # Backface cull in screen space using first triangle orientation.
        ax,ay,_=pts[0]; bx,by,_=pts[1]; cx,cy,_=pts[2]
        cross=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        if cross>=0:  # camera-facing winding for this cube definition
            continue
        rows.append({"face":i,"points":[(p[0],p[1]) for p in pts],"depth":sum(p[2] for p in pts)//4,"shade_milli":shade[i]})
    rows.sort(key=lambda r:r["depth"],reverse=True)
    return rows


def draw_triangle(pixels:list[tuple[int,int,int]],width:int,height:int,p0:tuple[int,int],p1:tuple[int,int],p2:tuple[int,int],color:tuple[int,int,int],blend,alpha:int,mode:str)->None:
    minx=max(0,min(p0[0],p1[0],p2[0])); maxx=min(width-1,max(p0[0],p1[0],p2[0]))
    miny=max(0,min(p0[1],p1[1],p2[1])); maxy=min(height-1,max(p0[1],p1[1],p2[1]))
    def edge(a,b,p): return (p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0])
    area=edge(p0,p1,p2)
    if area==0:return
    positive=area>0
    for y in range(miny,maxy+1):
        for x in range(minx,maxx+1):
            p=(x,y); e0=edge(p0,p1,p); e1=edge(p1,p2,p); e2=edge(p2,p0,p)
            inside=(e0>=0 and e1>=0 and e2>=0) if positive else (e0<=0 and e1<=0 and e2<=0)
            if inside:
                idx=y*width+x; pixels[idx]=blend(pixels[idx],color,alpha,mode)


def draw_cube(pixels:list[tuple[int,int,int]],width:int,height:int,geom:list[dict[str,Any]],base:list[int],blend,alpha:int,mode:str)->None:
    for face in geom:
        c=tuple(max(0,min(255,base[i]*face["shade_milli"]//1000)) for i in range(3))
        p=face["points"]
        draw_triangle(pixels,width,height,p[0],p[1],p[2],c,blend,alpha,mode)
        draw_triangle(pixels,width,height,p[0],p[2],p[3],c,blend,alpha,mode)

from decimal import Decimal, InvalidOperation
from pathlib import Path


def load_obj(path:Path)->dict[str,Any]:
    verts=[]; tris=[]
    for line_no,line in enumerate(Path(path).read_text(encoding='utf-8',errors='strict').splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'): continue
        parts=line.split()
        if parts[0]=='v' and len(parts)>=4:
            try: vals=[int(Decimal(parts[i])*SCALE) for i in (1,2,3)]
            except (InvalidOperation,ValueError) as exc: raise ValueError(f'OBJ invalid vertex line {line_no}') from exc
            verts.append(tuple(vals))
        elif parts[0]=='f' and len(parts)>=4:
            idx=[]
            for token in parts[1:]:
                raw=token.split('/')[0]
                try: n=int(raw)
                except ValueError as exc: raise ValueError(f'OBJ invalid face line {line_no}') from exc
                if n<0: n=len(verts)+n+1
                if n<=0 or n>len(verts): raise ValueError(f'OBJ face index out of range line {line_no}')
                idx.append(n-1)
            for i in range(1,len(idx)-1): tris.append((idx[0],idx[i],idx[i+1]))
    if not verts or not tris: raise ValueError('OBJ must contain vertices and faces')
    max_abs=max(max(abs(c) for c in v) for v in verts) or SCALE
    return {'vertices':verts,'triangles':tris,'max_abs':max_abs}


def mesh_geometry(mesh:dict[str,Any],center_x:int,center_y:int,depth:int,size:int,rx:int,ry:int,rz:int,width:int,height:int)->list[dict[str,Any]]:
    world=[]; max_abs=mesh['max_abs']
    for v in mesh['vertices']:
        local=(v[0]*size//(2*max_abs),v[1]*size//(2*max_abs),v[2]*size//(2*max_abs))
        q=_rot_z(_rot_y(_rot_x(local,rx),ry),rz); world.append((q[0]+center_x,q[1]+center_y,q[2]+depth))
    focal=max(32,min(width,height)*2); projected=[]
    for x,y,z in world:
        zz=max(1,z); projected.append((width//2+x*focal//zz,height//2-y*focal//zz,zz))
    rows=[]
    for i,(a,b,c) in enumerate(mesh['triangles']):
        p0,p1,p2=projected[a],projected[b],projected[c]
        cross=(p1[0]-p0[0])*(p2[1]-p0[1])-(p1[1]-p0[1])*(p2[0]-p0[0])
        if cross>=0: continue
        # Deterministic face illumination from transformed world-space normal.
        wa,wb,wc=world[a],world[b],world[c]
        ux,uy,uz=wb[0]-wa[0],wb[1]-wa[1],wb[2]-wa[2]; vx,vy,vz=wc[0]-wa[0],wc[1]-wa[1],wc[2]-wa[2]
        nx=uy*vz-uz*vy; ny=uz*vx-ux*vz; nz=ux*vy-uy*vx
        denom=max(1,abs(nx)+abs(ny)+abs(nz)); light=max(300,min(1000,600+(-nx-ny-2*nz)*400//(4*denom)))
        rows.append({'triangle':i,'points':[(p0[0],p0[1]),(p1[0],p1[1]),(p2[0],p2[1])],'depth':(p0[2]+p1[2]+p2[2])//3,'shade_milli':light})
    rows.sort(key=lambda r:r['depth'],reverse=True); return rows


def draw_mesh(pixels:list[tuple[int,int,int]],width:int,height:int,geom:list[dict[str,Any]],base:list[int],blend,alpha:int,mode:str)->None:
    for tri in geom:
        c=tuple(max(0,min(255,base[i]*tri['shade_milli']//1000)) for i in range(3)); p=tri['points']; draw_triangle(pixels,width,height,p[0],p[1],p[2],c,blend,alpha,mode)
