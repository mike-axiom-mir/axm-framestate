from __future__ import annotations
import copy,json
from pathlib import Path
from typing import Any
from .canonical import PROJECT_SCHEMA,canonical_json,normalize_project,digest
from .timeline import shift_track


def _shift_layer(layer:dict[str,Any],offset:int,duration:int)->dict[str,Any]:
    x=copy.deepcopy(layer);x['start_frame']=int(x.get('start_frame',0))+offset;x['end_frame']=int(x.get('end_frame',duration))+offset
    for k,v in list(x.items()):
        if isinstance(v,dict) and 'keyframes' in v: x[k]=shift_track(v,offset)
    return x

def compile_plan(raw:dict[str,Any])->dict[str,Any]:
    if raw.get('schema') not in {'axm.framestate.shot-plan/v0.1','axm.framestate.shot-plan/v0.2'}: raise ValueError('unsupported shot-plan schema')
    shots=raw.get('shots',[]);offset=0;layers=[];captions=[];audio=[];markers=[]
    camera={'x':{'keyframes':[]},'y':{'keyframes':[]},'zoom_milli':{'keyframes':[]}}
    for si,shot in enumerate(shots):
        dur=int(shot['duration_frames']); markers.append({'frame':offset,'label':shot.get('label',shot.get('id',f'SHOT {si+1}')),'kind':'shot'})
        sc=shot.get('camera',{}) or {}
        for key,default in [('x',0),('y',0),('zoom_milli',1000)]:
            val=sc.get(key,default)
            if isinstance(val,int): camera[key]['keyframes'].append({'frame':offset,'value':val,'easing':'hold'})
            elif isinstance(val,dict) and 'keyframes' in val:
                camera[key]['keyframes'].extend({**r,'frame':int(r['frame'])+offset} for r in val['keyframes'])
            else:
                camera[key]['keyframes'].append({'frame':offset,'value':int(val.get('from',default)),'easing':val.get('easing','linear')});camera[key]['keyframes'].append({'frame':offset+dur-1,'value':int(val.get('to',val.get('from',default))),'easing':'hold'})
        for l in shot.get('layers',[]):
            row=_shift_layer(l,offset,dur)
            row['id']=f"{shot.get('id',si)}::{row.get('id','layer')}"
            layers.append(row)
        for c in shot.get('captions',[]): captions.append({**c,'start_frame':int(c.get('start_frame',0))+offset,'end_frame':int(c.get('end_frame',dur))+offset,'id':f"{shot.get('id',si)}::{c.get('id','caption')}"})
        for a in shot.get('audio',[]): audio.append({**a,'start_frame':int(a.get('start_frame',0))+offset,'end_frame':int(a.get('end_frame',dur))+offset,'id':f"{shot.get('id',si)}::{a.get('id','audio')}"})
        offset+=dur
    # dedupe camera keyframe collisions, later shot wins
    for key in camera:
        by={int(r['frame']):r for r in camera[key]['keyframes']};camera[key]['keyframes']=[by[f] for f in sorted(by)]
    project={'schema':PROJECT_SCHEMA,'id':raw.get('id','compiled-film'),'title':raw.get('title',raw.get('id','Compiled Film')),'canvas':raw['canvas'],'duration_frames':offset,'background':raw.get('background',[0,0,0]),'camera':camera,'media':raw.get('media',[]),'layers':layers,'captions':captions,'audio':audio,'effects':raw.get('effects',[]),'markers':markers,'metadata':{**raw.get('metadata',{}),'compiled_from':'shot-plan','shot_count':len(shots)}}
    return normalize_project(project)

def compile_plan_file(source:Path,target:Path)->dict[str,Any]:
    raw=json.loads(Path(source).read_text(encoding='utf-8'));project=compile_plan(raw);p=Path(target);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical_json(project)+b'\n');return {'path':str(p),'project_digest':digest(project),'duration_frames':project['duration_frames'],'shot_count':len(raw.get('shots',[]))}
