from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, file_digest
from .effects import EffectOrgan, load_effect_library
from .media import prepare_media, scale_nearest
from .text import raster, measure
from .timeline import sample
from .three_d import cube_geometry, draw_cube, mesh_geometry, draw_mesh


class RenderError(RuntimeError):
    pass


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _blend_mode(dst: tuple[int,int,int], src: tuple[int,int,int] | list[int], alpha_milli:int, mode:str="normal") -> tuple[int,int,int]:
    a=max(0,min(1000,alpha_milli)); inv=1000-a
    if mode=="add": mixed=tuple(_clamp(dst[i]+src[i]) for i in range(3))
    elif mode=="multiply": mixed=tuple((dst[i]*src[i])//255 for i in range(3))
    elif mode=="screen": mixed=tuple(255-((255-dst[i])*(255-src[i])//255) for i in range(3))
    else: mixed=tuple(int(src[i]) for i in range(3))
    return tuple(_clamp((dst[i]*inv+mixed[i]*a)//1000) for i in range(3))


def _camera_project(value:int,camera_offset:int,zoom_milli:int,center:int)->int:
    return center+((value-camera_offset-center)*zoom_milli//1000)


def _fade_alpha(layer:dict[str,Any],frame:int,alpha:int)->int:
    start,end=layer["start_frame"],layer["end_frame"]
    fi=layer.get("fade_in_frames",0); fo=layer.get("fade_out_frames",0)
    mul=1000
    if fi and frame<start+fi: mul=min(mul,max(0,(frame-start)*1000//max(1,fi)))
    if fo and frame>=end-fo: mul=min(mul,max(0,(end-frame-1)*1000//max(1,fo)))
    return alpha*mul//1000


def _draw_bitmap(pixels:list[tuple[int,int,int]],width:int,height:int,bitmap:list[tuple[int,int,int]|None],bw:int,bh:int,x0:int,y0:int,alpha:int,mode:str="normal",tint:list[int]|None=None)->None:
    for y in range(bh):
        py=y0+y
        if py<0 or py>=height: continue
        for x in range(bw):
            px=x0+x
            if px<0 or px>=width: continue
            src=bitmap[y*bw+x]
            if src is None: continue
            if tint is not None: src=tuple(src[i]*tint[i]//255 for i in range(3))
            idx=py*width+px
            pixels[idx]=_blend_mode(pixels[idx],src,alpha,mode)


def _draw_text(pixels:list[tuple[int,int,int]],width:int,height:int,text:str,scale:int,color:list[int],bg:list[int],padding:int,x:int,y:int,align:str,alpha:int)->dict[str,Any]:
    tw,th,bm=raster(text,scale,color); bw=tw+2*padding; bh=th+2*padding
    if align=="center": x0=x-bw//2
    elif align=="right": x0=x-bw
    else: x0=x
    y0=y-bh//2
    for py in range(max(0,y0),min(height,y0+bh)):
        row=py*width
        for px in range(max(0,x0),min(width,x0+bw)):
            idx=row+px; pixels[idx]=_blend_mode(pixels[idx],bg,alpha,"normal")
    _draw_bitmap(pixels,width,height,bm,tw,th,x0+padding,y0+padding,alpha)
    return {"x":x0,"y":y0,"w":bw,"h":bh}


def render_frame(project:dict[str,Any],frame:int,library:dict[str,EffectOrgan],media_assets:dict[str,dict[str,Any]]|None=None)->tuple[bytes,dict[str,Any]]:
    width=project["canvas"]["width"]; height=project["canvas"]["height"]
    if frame<0 or frame>=project["duration_frames"]: raise RenderError("frame out of range")
    pixels=[tuple(project["background"]) for _ in range(width*height)]
    camera=project["camera"]; cx=sample(camera["x"],frame,0,project["duration_frames"]); cy=sample(camera["y"],frame,0,project["duration_frames"]); zoom=sample(camera["zoom_milli"],frame,0,project["duration_frames"])
    visible=[]
    media_assets=media_assets or {}
    for layer in project["layers"]:
        if not (layer["start_frame"]<=frame<layer["end_frame"]): continue
        start,end=layer["start_frame"],layer["end_frame"]
        x=sample(layer["x"],frame,start,end); y=sample(layer["y"],frame,start,end); alpha=_fade_alpha(layer,frame,sample(layer["opacity_milli"],frame,start,end))
        sx=_camera_project(x,cx,zoom,width//2); sy=_camera_project(y,cy,zoom,height//2); mode=layer.get("blend_mode","normal")
        rec={"id":layer["id"],"kind":layer["kind"],"x":sx,"y":sy,"opacity_milli":alpha,"z":layer["z"],"blend_mode":mode}
        kind=layer["kind"]
        if kind=="rect":
            w=max(1,sample(layer["w"],frame,start,end)*zoom//1000); h=max(1,sample(layer["h"],frame,start,end)*zoom//1000); rec.update({"w":w,"h":h}); x0=sx-w//2; y0=sy-h//2
            for py in range(max(0,y0),min(height,y0+h)):
                for px in range(max(0,x0),min(width,x0+w)):
                    idx=py*width+px; pixels[idx]=_blend_mode(pixels[idx],layer["color"],alpha,mode)
        elif kind=="circle":
            radius=max(1,sample(layer["radius"],frame,start,end)*zoom//1000); rec["radius"]=radius; rr=radius*radius
            for py in range(max(0,sy-radius),min(height,sy+radius+1)):
                dy=py-sy
                for px in range(max(0,sx-radius),min(width,sx+radius+1)):
                    dx=px-sx
                    if dx*dx+dy*dy<=rr:
                        idx=py*width+px; pixels[idx]=_blend_mode(pixels[idx],layer["color"],alpha,mode)
        elif kind in {"image","video"}:
            asset=media_assets.get(layer["media_id"])
            if not asset: raise RenderError(f"media asset not prepared: {layer['media_id']}")
            count=len(asset["frames"]); local=max(0,frame-start); source=layer["source_start_frame"]+(local*layer["playback_milli"]//1000)
            if layer.get("loop") and count: source%=count
            else: source=max(0,min(count-1,source))
            mf=asset["frames"][source]; w=max(1,sample(layer["w"],frame,start,end)*zoom//1000); h=max(1,sample(layer["h"],frame,start,end)*zoom//1000)
            scaled=scale_nearest(mf["pixels"],mf["width"],mf["height"],w,h); x0=sx-w//2; y0=sy-h//2
            _draw_bitmap(pixels,width,height,scaled,w,h,x0,y0,alpha,mode,layer["color"])
            rec.update({"w":w,"h":h,"media_id":layer["media_id"],"source_frame":source})
        elif kind=="text":
            rec.update(_draw_text(pixels,width,height,layer["text"],layer["scale"],layer["color"],layer["background_color"],layer["padding"],sx,sy,layer["align"],alpha)); rec["text"]=layer["text"]
        elif kind=="cube3d":
            depth=sample(layer["depth"],frame,start,end); size=max(1,sample(layer["size"],frame,start,end)); rx=sample(layer["rot_x_mdeg"],frame,start,end); ry=sample(layer["rot_y_mdeg"],frame,start,end); rz=sample(layer["rot_z_mdeg"],frame,start,end)
            # 2D camera x/y are applied as world offsets; zoom scales primitive size.
            world_x=(x-cx); world_y=(y-cy); size=max(1,size*zoom//1000)
            geom=cube_geometry(world_x,world_y,depth,size,rx,ry,rz,width,height); draw_cube(pixels,width,height,geom,layer["color"],_blend_mode,alpha,mode)
            rec.update({"depth":depth,"size":size,"rot_x_mdeg":rx,"rot_y_mdeg":ry,"rot_z_mdeg":rz,"visible_faces":[g["face"] for g in geom]})
        elif kind=="mesh3d":
            depth=sample(layer["depth"],frame,start,end); size=max(1,sample(layer["size"],frame,start,end)); rx=sample(layer["rot_x_mdeg"],frame,start,end); ry=sample(layer["rot_y_mdeg"],frame,start,end); rz=sample(layer["rot_z_mdeg"],frame,start,end); world_x=x-cx; world_y=y-cy; size=max(1,size*zoom//1000)
            asset=media_assets.get(layer["media_id"]);
            if not asset or asset.get("kind")!="mesh": raise RenderError(f"mesh asset not prepared: {layer['media_id']}")
            geom=mesh_geometry(asset["mesh"],world_x,world_y,depth,size,rx,ry,rz,width,height); draw_mesh(pixels,width,height,geom,layer["color"],_blend_mode,alpha,mode)
            rec.update({"media_id":layer["media_id"],"depth":depth,"size":size,"rot_x_mdeg":rx,"rot_y_mdeg":ry,"rot_z_mdeg":rz,"visible_triangles":len(geom)})
        visible.append(rec)

    caption_rows=[]
    for cap in project.get("captions",[]):
        if cap["start_frame"]<=frame<cap["end_frame"]:
            tw,th=measure(cap["text"],cap["scale"]); margin=max(4,cap["padding"]+2)
            cypos=margin+(th//2+cap["padding"]) if cap["position"]=="top" else height//2 if cap["position"]=="middle" else height-margin-(th//2+cap["padding"])
            box=_draw_text(pixels,width,height,cap["text"],cap["scale"],cap["color"],cap["background_color"],cap["padding"],width//2,cypos,"center",1000)
            caption_rows.append({"id":cap["id"],"text":cap["text"],**box})

    refs=[]
    for ref in project["effects"]:
        if ref not in library: raise RenderError(f"missing effect organ: {ref}")
        organ=library[ref]; pixels=[organ.apply(r,g,b,i%width,i//width) for i,(r,g,b) in enumerate(pixels)]; refs.append(ref)
    header=f"P6\n{width} {height}\n255\n".encode("ascii"); body=bytearray()
    for r,g,b in pixels: body.extend((r,g,b))
    ppm=header+bytes(body); pixel_digest="sha256:"+hashlib.sha256(bytes(body)).hexdigest()
    state={"frame":frame,"camera":{"x":cx,"y":cy,"zoom_milli":zoom},"visible_layers":visible,"captions":caption_rows,"effects":refs,"pixel_digest":pixel_digest}; state["state_digest"]=digest(state)
    return ppm,state


def render_project(project:dict[str,Any],output_dir:Path,machine_root:Path)->dict[str,Any]:
    output_dir=Path(output_dir); frames_dir=output_dir/"frames"; frames_dir.mkdir(parents=True,exist_ok=True)
    library=load_effect_library(machine_root); media_assets,media_manifest=prepare_media(project,output_dir/"media-cache",machine_root)
    states=[]; files=[]
    for frame in range(project["duration_frames"]):
        ppm,state=render_frame(project,frame,library,media_assets); p=frames_dir/f"frame-{frame:06d}.ppm"; p.write_bytes(ppm); states.append(state); files.append({"path":p.name,"digest":file_digest(p)})
    manifest={"schema":"axm.framestate.frame-manifest/v0.2","project_digest":digest(project),"frame_count":len(states),"states":states,"files":files,"media_conform":media_manifest}; manifest["manifest_digest"]=digest(manifest)
    (output_dir/"frame-manifest.json").write_bytes(canonical_json(manifest)+b"\n")
    return manifest
