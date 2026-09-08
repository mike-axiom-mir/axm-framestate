from __future__ import annotations
from pathlib import Path
from typing import Any
from .canonical import canonical_json,digest,file_digest
from .media import read_ppm
from .receipts import render_with_receipt

SHOT_KINDS={'scene','shot','cut'}

def derive_shots(project:dict[str,Any])->dict[str,Any]:
    marks=[m for m in project.get('markers',[]) if m.get('kind') in SHOT_KINDS]
    if not marks or marks[0]['frame']!=0: marks=[{'frame':0,'label':'START','kind':'scene'},*marks]
    uniq=[]; seen=set()
    for m in sorted(marks,key=lambda x:(x['frame'],x['label'])):
        if m['frame'] in seen: continue
        seen.add(m['frame']);uniq.append(m)
    rows=[]
    for i,m in enumerate(uniq):
        end=uniq[i+1]['frame'] if i+1<len(uniq) else project['duration_frames']
        if end>m['frame']: rows.append({'index':i,'id':f"shot-{i:03d}",'label':m['label'],'start_frame':m['frame'],'end_frame':end,'representative_frame':m['frame']+(end-m['frame']-1)//2})
    out={'schema':'axm.framestate.shots/v0.1','project_digest':digest(project),'shots':rows};out['digest']=digest(out);return out

def storyboard(project:dict[str,Any],output_dir:Path,machine_root:Path)->dict[str,Any]:
    out=Path(output_dir);render_dir=out/'render';rec=render_with_receipt(project,render_dir,machine_root,assemble=False);shots=derive_shots(project);panels=[]
    frames=[]
    for row in shots['shots']:
        p=render_dir/'frames'/f"frame-{row['representative_frame']:06d}.ppm"; w,h,b=read_ppm(p);frames.append((w,h,b,row));panels.append({**row,'frame_digest':file_digest(p)})
    if frames:
        fw,fh=frames[0][0],frames[0][1]; gap=4; sw=fw*len(frames)+gap*(len(frames)-1);sh=fh;body=bytearray([20,20,24])*(sw*sh)
        for j,(w,h,b,row) in enumerate(frames):
            ox=j*(fw+gap)
            for y in range(min(h,sh)):
                src=y*w*3;dst=(y*sw+ox)*3;body[dst:dst+w*3]=b[src:src+w*3]
        sp=out/'storyboard.ppm';sp.parent.mkdir(parents=True,exist_ok=True);sp.write_bytes(f'P6\n{sw} {sh}\n255\n'.encode()+body)
    else: sp=out/'storyboard.ppm';sp.write_bytes(b'P6\n1 1\n255\n\x00\x00\x00')
    result={'schema':'axm.framestate.storyboard/v0.1','project_digest':rec['project_digest'],'frame_manifest_digest':rec['frame_manifest_digest'],'shot_digest':shots['digest'],'panels':panels,'storyboard_digest':file_digest(sp),'path':str(sp)};result['digest']=digest(result);(out/'storyboard.json').write_bytes(canonical_json(result)+b'\n');return result
