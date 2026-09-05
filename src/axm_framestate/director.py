from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .canonical import normalize_project, canonical_json, digest

PLAN_SCHEMA='axm.framestate.shot-plan/v0.1'


def _camera_track(raw:Any,default:int,label:str)->dict[str,Any]:
    if raw is None: return {'from':default,'to':default,'easing':'hold'}
    if isinstance(raw,int): return {'from':raw,'to':raw,'easing':'hold'}
    if not isinstance(raw,dict) or set(raw)-{'from','to','easing'}: raise ValueError(f'{label} must be integer or from/to track')
    a=raw.get('from'); b=raw.get('to',a); easing=raw.get('easing','linear')
    if not isinstance(a,int) or not isinstance(b,int) or easing not in {'linear','hold','smoothstep'}: raise ValueError(f'{label} invalid track')
    return {'from':a,'to':b,'easing':easing}


def _shift(row:dict[str,Any],offset:int,duration:int,kind:str)->dict[str,Any]:
    out=dict(row); start=out.get('start_frame',0); end=out.get('end_frame',duration)
    if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start or end>duration: raise ValueError(f'{kind} relative timing invalid')
    out['start_frame']=offset+start; out['end_frame']=offset+end; return out


def compile_plan(raw:dict[str,Any])->dict[str,Any]:
    if not isinstance(raw,dict) or raw.get('schema')!=PLAN_SCHEMA: raise ValueError(f'plan schema must be {PLAN_SCHEMA}')
    allowed={'schema','id','title','canvas','background','media','effects','metadata','shots'}
    if set(raw)-allowed: raise ValueError(f'plan unknown fields: {sorted(set(raw)-allowed)}')
    shots=raw.get('shots')
    if not isinstance(shots,list) or not shots: raise ValueError('shots must be a non-empty array')
    layers=[]; captions=[]; audio=[]; markers=[]; offset=0; kx=[]; ky=[]; kz=[]
    seen=set()
    for i,shot in enumerate(shots):
        if not isinstance(shot,dict) or set(shot)-{'id','duration_frames','camera','layers','captions','audio','label'}: raise ValueError(f'shots[{i}] unsupported fields')
        sid=str(shot.get('id',f'shot-{i+1}'))
        if not sid or sid in seen: raise ValueError('shot ids must be unique');
        seen.add(sid); dur=shot.get('duration_frames')
        if not isinstance(dur,int) or dur<1: raise ValueError(f'{sid} duration_frames must be positive integer')
        cam=shot.get('camera',{})
        if not isinstance(cam,dict) or set(cam)-{'x','y','zoom_milli'}: raise ValueError(f'{sid} camera unsupported fields')
        tx=_camera_track(cam.get('x'),0,f'{sid}.camera.x'); ty=_camera_track(cam.get('y'),0,f'{sid}.camera.y'); tz=_camera_track(cam.get('zoom_milli'),1000,f'{sid}.camera.zoom_milli')
        for dest,t in ((kx,tx),(ky,ty),(kz,tz)):
            dest.append({'frame':offset,'value':t['from'],'easing':t['easing']})
            if dur>1: dest.append({'frame':offset+dur-1,'value':t['to'],'easing':'hold'})
        markers.append({'frame':offset,'label':str(shot.get('label',sid)),'kind':'shot'})
        for j,row in enumerate(shot.get('layers',[])):
            if not isinstance(row,dict): raise ValueError(f'{sid}.layers[{j}] must be object')
            shifted=_shift(row,offset,dur,'layer'); shifted['id']=f'{sid}/{shifted.get("id",f"layer-{j}")}'; layers.append(shifted)
        for j,row in enumerate(shot.get('captions',[])):
            if not isinstance(row,dict): raise ValueError(f'{sid}.captions[{j}] must be object')
            shifted=_shift(row,offset,dur,'caption'); shifted['id']=f'{sid}/{shifted.get("id",f"caption-{j}")}'; captions.append(shifted)
        for j,row in enumerate(shot.get('audio',[])):
            if not isinstance(row,dict): raise ValueError(f'{sid}.audio[{j}] must be object')
            shifted=_shift(row,offset,dur,'audio'); shifted['id']=f'{sid}/{shifted.get("id",f"audio-{j}")}'; audio.append(shifted)
        offset+=dur
    project={'schema':'axm.framestate.project/v0.2','id':raw.get('id','compiled-plan'),'title':raw.get('title',raw.get('id','compiled-plan')),'canvas':raw['canvas'],'duration_frames':offset,'background':raw.get('background',[0,0,0]),'camera':{'x':{'keyframes':kx},'y':{'keyframes':ky},'zoom_milli':{'keyframes':kz}},'media':raw.get('media',[]),'layers':layers,'captions':captions,'audio':audio,'effects':raw.get('effects',[]),'markers':markers,'metadata':{**raw.get('metadata',{}),'compiled_from':PLAN_SCHEMA}}
    normalized=normalize_project(project); return normalized


def compile_plan_file(plan_path:Path,output_path:Path)->dict[str,Any]:
    raw=json.loads(Path(plan_path).read_text(encoding='utf-8')); project=compile_plan(raw); Path(output_path).parent.mkdir(parents=True,exist_ok=True); Path(output_path).write_bytes(canonical_json(project)+b'\n'); return {'schema':'axm.framestate.plan-compile-receipt/v0.1','plan':str(plan_path),'output':str(output_path),'project_digest':digest(project),'duration_frames':project['duration_frames'],'shot_count':len(raw['shots'])}
