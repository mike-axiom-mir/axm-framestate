from __future__ import annotations
import hashlib, json, random
from pathlib import Path
from typing import Any
from .canonical import canonical_json,digest,file_digest
from .effects import EffectOrgan,load_effect_library
from .timeline import sample
from .media import MediaCache, read_ppm
from .text import bitmap_text, shaped_text
from .three_d import CORDIC_SCALE, cube_mesh, project_vertex, rotate_xyz, sincos_mdeg

class RenderError(RuntimeError): pass

def clamp(v:int)->int: return 0 if v<0 else 255 if v>255 else v

def _mode(dst:tuple[int,int,int],src:tuple[int,int,int],mode:str)->tuple[int,int,int]:
    if mode=='add': return tuple(clamp(dst[i]+src[i]) for i in range(3))
    if mode=='multiply': return tuple(dst[i]*src[i]//255 for i in range(3))
    if mode=='screen': return tuple(255-((255-dst[i])*(255-src[i])//255) for i in range(3))
    return src

def blend(dst:tuple[int,int,int],src:tuple[int,int,int],alpha:int,mode:str='normal')->tuple[int,int,int]:
    a=max(0,min(1000,int(alpha))); s=_mode(dst,src,mode); inv=1000-a
    return tuple(clamp((dst[i]*inv+s[i]*a)//1000) for i in range(3))

def _camera(value:int,offset:int,zoom:int,center:int)->int: return center+(value-offset-center)*zoom//1000

def _fade(layer:dict[str,Any],frame:int,alpha:int)->int:
    s,e=layer['start_frame'],layer['end_frame']; fi=layer.get('fade_in_frames',0); fo=layer.get('fade_out_frames',0)
    if fi and frame<s+fi: alpha=alpha*max(0,frame-s)*1000//max(1,fi)//1000
    if fo and frame>=e-fo: alpha=alpha*max(0,e-1-frame)*1000//max(1,fo)//1000
    return max(0,min(1000,alpha))

def _draw_rect(pix,w,h,cx,cy,rw,rh,color,alpha,mode):
    x0=cx-rw//2; y0=cy-rh//2
    for y in range(max(0,y0),min(h,y0+rh)):
        base=y*w
        for x in range(max(0,x0),min(w,x0+rw)):
            i=base+x; pix[i]=blend(pix[i],tuple(color),alpha,mode)

def _draw_circle(pix,w,h,cx,cy,r,color,alpha,mode):
    rr=r*r
    for y in range(max(0,cy-r),min(h,cy+r+1)):
        dy=y-cy; base=y*w
        for x in range(max(0,cx-r),min(w,cx+r+1)):
            dx=x-cx
            if dx*dx+dy*dy<=rr:
                i=base+x; pix[i]=blend(pix[i],tuple(color),alpha,mode)

def _rgba_from_rgb(sw:int,sh:int,body:bytes)->bytes:
    out=bytearray(sw*sh*4)
    j=0
    for i in range(sw*sh): out[j:j+4]=body[i*3:i*3+3]+b'\xff'; j+=4
    return bytes(out)

def _composite_rgba(pix,w,h,rgba:bytes,sw:int,sh:int,cx:int,cy:int,dw:int,dh:int,angle:int,alpha:int,mode:str,wipe:int=1000,chroma=None,tolerance:int=0,mask:tuple[int,int,bytes]|None=None):
    if dw<=0 or dh<=0: return
    s,c=sincos_mdeg(angle); halfw=dw//2; halfh=dh//2
    # conservative rotated bounding box
    bound=max(dw,dh)+2; x0=max(0,cx-bound//2); x1=min(w,cx+bound//2+1); y0=max(0,cy-bound//2); y1=min(h,cy+bound//2+1)
    for y in range(y0,y1):
        for x in range(x0,x1):
            dx=x-cx; dy=y-cy
            # inverse rotate
            rx=(dx*c+dy*s)//CORDIC_SCALE; ry=(-dx*s+dy*c)//CORDIC_SCALE
            if rx<-halfw or rx>=dw-halfw or ry<-halfh or ry>=dh-halfh: continue
            if wipe<1000 and (rx+halfw)*1000//max(1,dw)>=wipe: continue
            u=(rx+halfw)*sw//max(1,dw); v=(ry+halfh)*sh//max(1,dh)
            if not (0<=u<sw and 0<=v<sh): continue
            si=(v*sw+u)*4; sr,sg,sb,sa=rgba[si:si+4]
            if chroma is not None and max(abs(sr-chroma[0]),abs(sg-chroma[1]),abs(sb-chroma[2]))<=tolerance: continue
            ma=1000
            if mask is not None:
                mw,mh,mb=mask; mu=u*mw//sw; mv=v*mh//sh; mi=(mv*mw+mu)*3; ma=sum(mb[mi:mi+3])*1000//(255*3)
            a=alpha*sa//255*ma//1000
            di=y*w+x; pix[di]=blend(pix[di],(sr,sg,sb),a,mode)

def _text_rgba(layer:dict[str,Any],cache:MediaCache):
    bg=layer.get('background_color')
    if layer.get('font_media_id'):
        return shaped_text(layer.get('text',''),cache.font_path(layer['font_media_id']),layer.get('font_size',16),tuple(layer.get('color',[255,255,255])),tuple(bg) if bg else None,layer.get('padding',0))
    return bitmap_text(layer.get('text',''),layer.get('scale',1),tuple(layer.get('color',[255,255,255])),tuple(bg) if bg else None,layer.get('padding',0))

def _source_index(layer:dict[str,Any],frame:int,count:int)->int:
    if count<=1: return 0
    if layer.get('freeze_frame') is not None: return max(0,min(count-1,int(layer['freeze_frame'])))
    local=frame-layer['start_frame']; speed=sample(layer.get('playback_milli',1000),frame,layer['start_frame'],layer['end_frame'])
    idx=layer.get('source_start_frame',0)+(local*speed//1000)
    if layer.get('loop'): return idx%count
    return max(0,min(count-1,idx))

def _draw_particles(pix,w,h,layer,frame,cx,cy,alpha,mode):
    count=layer['count']; seed=layer['seed']; age=max(0,frame-layer['start_frame']); color=layer['color']; size=layer['size']
    for i in range(count):
        # stable per-particle pseudo-random values
        hsh=hashlib.sha256(f'{seed}:{i}'.encode()).digest(); rx=int.from_bytes(hsh[:4],'big'); ry=int.from_bytes(hsh[4:8],'big')
        px=cx+(rx%(layer['spread_x']*2+1)-layer['spread_x']); py=cy+(ry%(layer['spread_y']*2+1)-layer['spread_y'])-age*layer['speed']
        _draw_rect(pix,w,h,px,py,size,size,color,alpha,mode)

def _triangle(pix,zbuf,w,h,pts,cols,alpha,mode,texture=None,uvs=None):
    (x0,y0,z0),(x1,y1,z1),(x2,y2,z2)=pts
    minx=max(0,min(x0,x1,x2)); maxx=min(w-1,max(x0,x1,x2)); miny=max(0,min(y0,y1,y2)); maxy=min(h-1,max(y0,y1,y2))
    den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if den==0:return 0
    drawn=0
    for y in range(miny,maxy+1):
        for x in range(minx,maxx+1):
            a_num=(y1-y2)*(x-x2)+(x2-x1)*(y-y2); b_num=(y2-y0)*(x-x2)+(x0-x2)*(y-y2); c_num=den-a_num-b_num
            if den>0:
                if a_num<0 or b_num<0 or c_num<0: continue
            else:
                if a_num>0 or b_num>0 or c_num>0: continue
            z=(z0*a_num+z1*b_num+z2*c_num)//den; idx=y*w+x
            if z>=zbuf[idx]: continue
            zbuf[idx]=z
            if texture and uvs:
                tw,th,tb=texture; u=(uvs[0][0]*a_num+uvs[1][0]*b_num+uvs[2][0]*c_num)//den; v=(uvs[0][1]*a_num+uvs[1][1]*b_num+uvs[2][1]*c_num)//den
                tx=max(0,min(tw-1,u*tw//1_000_000)); ty=max(0,min(th-1,(1_000_000-v)*th//1_000_000)); ti=(ty*tw+tx)*3; src=tuple(tb[ti:ti+3])
            else: src=cols
            pix[idx]=blend(pix[idx],src,alpha,mode); drawn+=1
    return drawn

def _render_mesh(pix,w,h,layer,frame,cx,cy,zoom,cache,mesh):
    s=layer['start_frame'];e=layer['end_frame']; depth=sample(layer['depth'],frame,s,e); size=sample(layer['size'],frame,s,e)*zoom//1000; rx=sample(layer['rot_x_mdeg'],frame,s,e);ry=sample(layer['rot_y_mdeg'],frame,s,e);rz=sample(layer['rot_z_mdeg'],frame,s,e)
    lx=sample(layer['x'],frame,s,e);ly=sample(layer['y'],frame,s,e); sx=_camera(lx,cx,zoom,w//2)-w//2; sy=_camera(ly,cy,zoom,h//2)-h//2
    verts=mesh['vertices']
    if layer.get('morph_media_id'):
        other=cache.mesh(layer['morph_media_id']); mm=max(0,min(1000,sample(layer.get('morph_milli',0),frame,s,e)))
        if len(other['vertices'])==len(verts): verts=[tuple(a[k]+(b[k]-a[k])*mm//1000 for k in range(3)) for a,b in zip(verts,other['vertices'])]
    proj=[project_vertex(rotate_xyz(v,rx,ry,rz),sx,sy,depth,size,w,h) for v in verts]
    tex=None
    if layer.get('texture_media_id'):
        tw,th,tb=cache.image_frame(layer['texture_media_id'],0); tex=(tw,th,tb)
    zbuf=[10**12]*(w*h); triangles=0
    for face in mesh['faces']:
        ids=[r[0] for r in face]; pts=[proj[i] for i in ids]
        # backface/lighting in screen space
        cross=(pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])
        if cross==0: continue
        shade=650+min(350,abs(cross)//20); col=tuple(clamp(c*shade//1000) for c in layer['color'])
        uv=None
        if tex and all(r[1] is not None for r in face): uv=[mesh['uvs'][r[1]] for r in face]
        triangles+=_triangle(pix,zbuf,w,h,pts,col,_fade(layer,frame,sample(layer['opacity_milli'],frame,s,e)),layer['blend_mode'],tex,uv)>0
    # simple screen-space cast shadow projection
    shadow_tris=0
    if layer.get('shadow'):
        sp=[(x+30,y+20,z+1000) for x,y,z in proj]; zb=[10**12]*(w*h)
        for face in mesh['faces']:
            pts=[sp[r[0]] for r in face]; shadow_tris+=_triangle(pix,zb,w,h,pts,(8,8,12),250,'multiply')>0
    return {'triangles':triangles,'shadow_triangles':shadow_tris,'depth':depth,'size':size,'rotation_mdeg':[rx,ry,rz]}

def _bone_pose(layer,frame):
    rig=layer.get('rig',{}); bones=rig.get('bones',[]); clip=layer.get('clip',{}).get('bones',{}) if isinstance(layer.get('clip'),dict) else {}; poses={}
    for b in bones:
        bid=b['id']; parent=b.get('parent'); angle=int(b.get('angle_mdeg',0)); angle+=sample(clip.get(bid,0),frame,layer['start_frame'],layer['end_frame']) if bid in clip else 0
        length=int(b.get('length',20)); base_x=int(b.get('x',0)); base_y=int(b.get('y',0))
        if parent and parent in poses: bx,by,pa=poses[parent]['end_x'],poses[parent]['end_y'],poses[parent]['angle']; angle+=pa
        else: bx,by=base_x,base_y
        ss,cc=sincos_mdeg(angle); ex=bx+length*cc//CORDIC_SCALE; ey=by+length*ss//CORDIC_SCALE; poses[bid]={'x':bx,'y':by,'end_x':ex,'end_y':ey,'angle':angle}
    return poses

def render_frame(project:dict[str,Any],frame:int,library:dict[str,EffectOrgan],cache:MediaCache)->tuple[bytes,dict[str,Any]]:
    w=project['canvas']['width']; h=project['canvas']['height']; bg=tuple(project['background']); pix=[bg]*(w*h)
    cam=project['camera']; cx=sample(cam['x'],frame,0,project['duration_frames']);cy=sample(cam['y'],frame,0,project['duration_frames']);zoom=sample(cam['zoom_milli'],frame,0,project['duration_frames'])
    visible=[]
    for layer in project['layers']:
        if not(layer['start_frame']<=frame<layer['end_frame']): continue
        s,e=layer['start_frame'],layer['end_frame']; alpha=_fade(layer,frame,sample(layer['opacity_milli'],frame,s,e)); x=sample(layer['x'],frame,s,e);y=sample(layer['y'],frame,s,e);sx=_camera(x,cx,zoom,w//2);sy=_camera(y,cy,zoom,h//2);mode=layer['blend_mode']; kind=layer['kind']; rec={'id':layer['id'],'kind':kind,'x':sx,'y':sy,'opacity_milli':alpha,'z':layer['z']}
        if kind=='rect': rw=max(1,sample(layer['w'],frame,s,e)*zoom//1000);rh=max(1,sample(layer['h'],frame,s,e)*zoom//1000);_draw_rect(pix,w,h,sx,sy,rw,rh,layer['color'],alpha,mode);rec.update(w=rw,h=rh)
        elif kind=='circle': r=max(1,sample(layer['radius'],frame,s,e)*zoom//1000);_draw_circle(pix,w,h,sx,sy,r,layer['color'],alpha,mode);rec['radius']=r
        elif kind=='text':
            tw,th,rgba,ev=_text_rgba(layer,cache); _composite_rgba(pix,w,h,rgba,tw,th,sx,sy,tw,th,sample(layer['rotation_mdeg'],frame,s,e),alpha,mode);rec.update(text_digest=digest(layer['text']),text_boundary=ev)
        elif kind in {'image','video','child'}:
            if kind=='child':
                child=cache.child(layer['media_id']); count=child['project']['duration_frames']; idx=_source_index(layer,frame,count); fp=child['output']/'frames'/f'frame-{idx:06d}.ppm'; sw,sh,body=read_ppm(fp); rec['child_project_digest']=child['receipt']['project_digest'];rec['child_frame_manifest_digest']=child['receipt']['frame_manifest_digest']
            else:
                count=cache.frame_count(layer['media_id']);idx=_source_index(layer,frame,count);sw,sh,body=cache.image_frame(layer['media_id'],idx)
            rgba=_rgba_from_rgb(sw,sh,body); dw=max(1,sample(layer['w'],frame,s,e)*zoom//1000);dh=max(1,sample(layer['h'],frame,s,e)*zoom//1000);mask=None
            if layer.get('mask_media_id'): mask=cache.image_frame(layer['mask_media_id'],0)
            _composite_rgba(pix,w,h,rgba,sw,sh,sx,sy,dw,dh,sample(layer['rotation_mdeg'],frame,s,e),alpha,mode,sample(layer.get('wipe_milli',1000),frame,s,e),layer.get('chroma_key'),layer.get('chroma_tolerance',0),mask);rec.update(source_frame=idx,w=dw,h=dh,mask_media_id=layer.get('mask_media_id'),chroma_key=layer.get('chroma_key'))
        elif kind=='particles': _draw_particles(pix,w,h,layer,frame,sx,sy,alpha,mode);rec['particle_count']=layer['count']
        elif kind in {'cube3d','mesh3d','skinned_mesh3d'}:
            mesh=cube_mesh() if kind=='cube3d' else cache.mesh(layer['media_id']); rec.update(_render_mesh(pix,w,h,layer,frame,cx,cy,zoom,cache,mesh))
        elif kind=='rig2d':
            poses=_bone_pose(layer,frame)
            for p in poses.values():
                steps=max(abs(p['end_x']-p['x']),abs(p['end_y']-p['y']),1)
                for k in range(steps+1):
                    bx=sx+p['x']+(p['end_x']-p['x'])*k//steps;by=sy+p['y']+(p['end_y']-p['y'])*k//steps;_draw_circle(pix,w,h,bx,by,layer['bone_width'],layer['color'],alpha,mode)
            rec['bone_count']=len(poses)
        visible.append(rec)
    # captions are canonical overlay state
    for cap in project.get('captions',[]):
        if cap['start_frame']<=frame<cap['end_frame']:
            lay={'text':cap['text'],'scale':cap['scale'],'color':[255,255,255],'padding':2,'background_color':[0,0,0],'font_media_id':cap.get('font_media_id'),'font_size':cap.get('font_size',14)}
            tw,th,rgba,ev=_text_rgba(lay,cache); cypos=h-th//2-3 if cap['position']=='bottom' else th//2+3;_composite_rgba(pix,w,h,rgba,tw,th,w//2,cypos,tw,th,0,900,'normal');visible.append({'id':cap['id'],'kind':'caption','text_digest':digest(cap['text']),'text_boundary':ev})
    refs=[]
    for ref in project['effects']:
        if ref not in library: raise RenderError(f'missing effect organ: {ref}')
        organ=library[ref];pix=[organ.apply(r,g,b,i%w,i//w) for i,(r,g,b) in enumerate(pix)];refs.append(ref)
    body=bytearray()
    for r,g,b in pix: body.extend((r,g,b))
    ppm=f'P6\n{w} {h}\n255\n'.encode()+bytes(body); pd='sha256:'+hashlib.sha256(body).hexdigest();state={'frame':frame,'camera':{'x':cx,'y':cy,'zoom_milli':zoom},'visible_layers':visible,'effects':refs,'pixel_digest':pd};state['state_digest']=digest(state);return ppm,state

def render_project(project:dict[str,Any],output_dir:Path,machine_root:Path)->dict[str,Any]:
    output_dir=Path(output_dir);fd=output_dir/'frames';fd.mkdir(parents=True,exist_ok=True);lib=load_effect_library(machine_root);cache=MediaCache(project,output_dir,machine_root);states=[];files=[]
    for f in range(project['duration_frames']):
        ppm,state=render_frame(project,f,lib,cache);p=fd/f'frame-{f:06d}.ppm';p.write_bytes(ppm);states.append(state);files.append({'path':p.name,'digest':file_digest(p)})
    m={'schema':'axm.framestate.frame-manifest/v0.4','project_digest':digest(project),'media_manifest_digest':cache.manifest['manifest_digest'],'frame_count':len(states),'states':states,'files':files};m['manifest_digest']=digest(m);(output_dir/'frame-manifest.json').write_bytes(canonical_json(m)+b'\n');return m
