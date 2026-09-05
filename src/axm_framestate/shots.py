from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .canonical import digest, canonical_json, file_digest
from .media import read_ppm, scale_nearest
from .render import render_project
from .text import raster


def derive_shots(project:dict[str,Any])->list[dict[str,Any]]:
    duration=project["duration_frames"]
    cuts={0,duration}
    labels={0:"START"}
    for marker in project.get("markers",[]):
        if marker.get("kind") in {"cut","scene","shot"}:
            cuts.add(marker["frame"]); labels[marker["frame"]]=marker["label"]
    pts=sorted(cuts); out=[]
    for i,(a,b) in enumerate(zip(pts,pts[1:])):
        if b<=a: continue
        out.append({"id":f"shot-{i+1:03d}","start_frame":a,"end_frame":b,"duration_frames":b-a,"label":labels.get(a,f"SHOT {i+1}"),"representative_frame":a+(b-a-1)//2})
    return out


def _ppm_bytes(w:int,h:int,pixels:list[tuple[int,int,int]])->bytes:
    body=bytearray()
    for p in pixels: body.extend(p)
    return f"P6\n{w} {h}\n255\n".encode()+bytes(body)


def build_storyboard(project:dict[str,Any],output_dir:Path,machine_root:Path,thumb_width:int=160)->dict[str,Any]:
    output_dir=Path(output_dir); render_dir=output_dir/"source-render"; manifest=render_project(project,render_dir,machine_root); shots=derive_shots(project)
    srcw=project["canvas"]["width"]; srch=project["canvas"]["height"]; tw=min(thumb_width,srcw); th=max(1,srch*tw//srcw); label_h=12
    cols=min(3,max(1,len(shots))); rows=(len(shots)+cols-1)//cols; sheet_w=cols*tw; sheet_h=rows*(th+label_h); sheet=[(12,12,16)]*(sheet_w*sheet_h)
    cells=[]
    for i,shot in enumerate(shots):
        f=shot["representative_frame"]; p=render_dir/"frames"/f"frame-{f:06d}.ppm"; w,h,px=read_ppm(p); scaled=scale_nearest(px,w,h,tw,th); col=i%cols; row=i//cols; ox=col*tw; oy=row*(th+label_h)
        for y in range(th): sheet[(oy+y)*sheet_w+ox:(oy+y)*sheet_w+ox+tw]=scaled[y*tw:(y+1)*tw]
        text=f"{shot['id']} F{f}"; fw,fh,bm=raster(text,1,[255,255,255])
        tx=ox+2; ty=oy+th+2
        for y in range(min(fh,label_h-2)):
            for x in range(min(fw,tw-4)):
                v=bm[y*fw+x]
                if v is not None: sheet[(ty+y)*sheet_w+tx+x]=v
        cells.append({**shot,"source_frame_digest":manifest["files"][f]["digest"]})
    out=output_dir/"storyboard.ppm"; out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(_ppm_bytes(sheet_w,sheet_h,sheet))
    result={"schema":"axm.framestate.storyboard/v0.2","project_digest":manifest["project_digest"],"shots":cells,"storyboard":{"path":str(out),"digest":file_digest(out),"width":sheet_w,"height":sheet_h}}; result["storyboard_digest"]=digest(result); (output_dir/"storyboard.json").write_bytes(canonical_json(result)+b'\n'); return result
