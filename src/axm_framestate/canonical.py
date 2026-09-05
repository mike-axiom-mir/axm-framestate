from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

PROJECT_SCHEMAS={f'axm.framestate.project/v0.{n}' for n in range(1,5)}
PROJECT_SCHEMA='axm.framestate.project/v0.4'

class ProjectError(ValueError): pass

def canonical_json(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def digest(value:Any)->str:
    return 'sha256:'+hashlib.sha256(canonical_json(value)).hexdigest()

def file_digest(path:Path)->str:
    return 'sha256:'+hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _int(v:Any,label:str,lo:int|None=None,hi:int|None=None)->int:
    if isinstance(v,bool) or not isinstance(v,int): raise ProjectError(f'{label} must be integer')
    if lo is not None and v<lo: raise ProjectError(f'{label} must be >= {lo}')
    if hi is not None and v>hi: raise ProjectError(f'{label} must be <= {hi}')
    return v

def _text(v:Any,label:str,maxlen:int=10000)->str:
    if not isinstance(v,str) or not v.strip(): raise ProjectError(f'{label} must be non-empty text')
    if len(v)>maxlen: raise ProjectError(f'{label} too long')
    return v

def _color(v:Any,label:str,alpha:bool=False)->list[int]:
    n=4 if alpha else 3
    if not isinstance(v,list) or len(v)!=n: raise ProjectError(f'{label} must have {n} channels')
    return [_int(x,f'{label}[{i}]',0,255) for i,x in enumerate(v)]

def _track(v:Any,label:str,duration:int,default:int=0)->dict[str,Any]|int:
    if v is None: return default
    if isinstance(v,int) and not isinstance(v,bool): return v
    if not isinstance(v,dict): raise ProjectError(f'{label} must be integer or track')
    if 'keyframes' in v:
        if set(v)-{'keyframes'}: raise ProjectError(f'{label} keyframe track has unknown fields')
        rows=v['keyframes']
        if not isinstance(rows,list) or not rows: raise ProjectError(f'{label}.keyframes must be non-empty')
        out=[]; last=-1
        for i,row in enumerate(rows):
            if not isinstance(row,dict) or set(row)-{'frame','value','easing'}: raise ProjectError(f'{label}.keyframes[{i}] invalid')
            fr=_int(row.get('frame'),f'{label}.keyframes[{i}].frame',0,duration-1)
            if fr<=last: raise ProjectError(f'{label}.keyframes must be ordered')
            last=fr
            ease=row.get('easing','linear')
            if ease not in {'linear','hold','smoothstep'}: raise ProjectError(f'{label} easing unsupported')
            out.append({'frame':fr,'value':_int(row.get('value'),f'{label}.keyframes[{i}].value',-10_000_000,10_000_000),'easing':ease})
        return {'keyframes':out}
    allowed={'from','to','easing','value'}
    if set(v)-allowed: raise ProjectError(f'{label} has unknown fields')
    a=_int(v.get('from',v.get('value',default)),f'{label}.from',-10_000_000,10_000_000)
    b=_int(v.get('to',a),f'{label}.to',-10_000_000,10_000_000)
    ease=v.get('easing','linear')
    if ease not in {'linear','hold','smoothstep'}: raise ProjectError(f'{label} easing unsupported')
    return {'from':a,'to':b,'easing':ease}

def _layer(raw:dict[str,Any],i:int,duration:int)->dict[str,Any]:
    label=f'layers[{i}]'; lid=_text(raw.get('id'),f'{label}.id',200); kind=_text(raw.get('kind'),f'{label}.kind',40)
    supported={'rect','circle','text','image','video','particles','cube3d','mesh3d','rig2d','skinned_mesh3d','child'}
    if kind not in supported: raise ProjectError(f'{label}.kind unsupported: {kind}')
    start=_int(raw.get('start_frame',0),f'{label}.start_frame',0,duration-1); end=_int(raw.get('end_frame',duration),f'{label}.end_frame',start+1,duration)
    out={'id':lid,'kind':kind,'z':_int(raw.get('z',0),f'{label}.z',-100000,100000),'start_frame':start,'end_frame':end,
         'x':_track(raw.get('x',0),f'{label}.x',duration,0),'y':_track(raw.get('y',0),f'{label}.y',duration,0),
         'opacity_milli':_track(raw.get('opacity_milli',1000),f'{label}.opacity_milli',duration,1000),
         'rotation_mdeg':_track(raw.get('rotation_mdeg',0),f'{label}.rotation_mdeg',duration,0),
         'fade_in_frames':_int(raw.get('fade_in_frames',0),f'{label}.fade_in_frames',0,duration),'fade_out_frames':_int(raw.get('fade_out_frames',0),f'{label}.fade_out_frames',0,duration),
         'blend_mode':raw.get('blend_mode','normal')}
    if out['blend_mode'] not in {'normal','add','multiply','screen'}: raise ProjectError(f'{label}.blend_mode unsupported')
    if kind in {'rect','circle','particles','cube3d','mesh3d','rig2d','skinned_mesh3d'}: out['color']=_color(raw.get('color',[255,255,255]),f'{label}.color')
    if kind=='rect': out.update(w=_track(raw.get('w',10),f'{label}.w',duration,10),h=_track(raw.get('h',10),f'{label}.h',duration,10))
    elif kind=='circle': out['radius']=_track(raw.get('radius',5),f'{label}.radius',duration,5)
    elif kind=='text':
        out.update(text=str(raw.get('text','')),scale=_int(raw.get('scale',1),f'{label}.scale',1,32),color=_color(raw.get('color',[255,255,255]),f'{label}.color'),align=raw.get('align','center'),font_media_id=raw.get('font_media_id'),font_size=_int(raw.get('font_size',16),f'{label}.font_size',4,512),background_color=raw.get('background_color'),padding=_int(raw.get('padding',0),f'{label}.padding',0,100))
        if out['background_color'] is not None: out['background_color']=_color(out['background_color'],f'{label}.background_color')
    elif kind in {'image','video','child'}:
        out.update(media_id=_text(raw.get('media_id'),f'{label}.media_id',200),w=_track(raw.get('w',64),f'{label}.w',duration,64),h=_track(raw.get('h',64),f'{label}.h',duration,64),source_start_frame=_int(raw.get('source_start_frame',0),f'{label}.source_start_frame',0,10_000_000),playback_milli=_track(raw.get('playback_milli',1000),f'{label}.playback_milli',duration,1000),loop=bool(raw.get('loop',False)),freeze_frame=raw.get('freeze_frame'),mask_media_id=raw.get('mask_media_id'),chroma_key=raw.get('chroma_key'),chroma_tolerance=_int(raw.get('chroma_tolerance',0),f'{label}.chroma_tolerance',0,255),wipe_milli=_track(raw.get('wipe_milli',1000),f'{label}.wipe_milli',duration,1000))
        if out['chroma_key'] is not None: out['chroma_key']=_color(out['chroma_key'],f'{label}.chroma_key')
    elif kind=='particles':
        out.update(count=_int(raw.get('count',32),f'{label}.count',1,10000),seed=_int(raw.get('seed',1),f'{label}.seed',0,2**31-1),spread_x=_int(raw.get('spread_x',64),f'{label}.spread_x',0,10000),spread_y=_int(raw.get('spread_y',32),f'{label}.spread_y',0,10000),speed=_int(raw.get('speed',3),f'{label}.speed',-1000,1000),size=_int(raw.get('size',2),f'{label}.size',1,100))
    elif kind in {'cube3d','mesh3d','skinned_mesh3d'}:
        out.update(depth=_track(raw.get('depth',180),f'{label}.depth',duration,180),size=_track(raw.get('size',100),f'{label}.size',duration,100),rot_x_mdeg=_track(raw.get('rot_x_mdeg',0),f'{label}.rot_x_mdeg',duration,0),rot_y_mdeg=_track(raw.get('rot_y_mdeg',0),f'{label}.rot_y_mdeg',duration,0),rot_z_mdeg=_track(raw.get('rot_z_mdeg',0),f'{label}.rot_z_mdeg',duration,0),shadow=bool(raw.get('shadow',False)),texture_media_id=raw.get('texture_media_id'),morph_media_id=raw.get('morph_media_id'),morph_milli=_track(raw.get('morph_milli',0),f'{label}.morph_milli',duration,0))
        if kind!='cube3d': out['media_id']=_text(raw.get('media_id'),f'{label}.media_id',200)
        if kind=='skinned_mesh3d': out.update(rig=raw.get('rig',{}),weights=raw.get('weights',[]),clip=raw.get('clip',{}))
    elif kind=='rig2d': out.update(rig=raw.get('rig',{}),clip=raw.get('clip',{}),bone_width=_int(raw.get('bone_width',3),f'{label}.bone_width',1,40))
    return out

def normalize_project(raw:Any)->dict[str,Any]:
    if not isinstance(raw,dict): raise ProjectError('project must be object')
    allowed={'schema','id','title','canvas','duration_frames','background','camera','media','layers','captions','audio','effects','markers','metadata'}
    if set(raw)-allowed: raise ProjectError(f'project has unknown fields: {sorted(set(raw)-allowed)}')
    schema=raw.get('schema','axm.framestate.project/v0.4')
    if schema not in PROJECT_SCHEMAS: raise ProjectError('unsupported project schema')
    pid=_text(raw.get('id'),'id',200); title=str(raw.get('title',pid))
    canvas=raw.get('canvas',{}); width=_int(canvas.get('width'),'canvas.width',16,4096); height=_int(canvas.get('height'),'canvas.height',16,4096); fps=_int(canvas.get('fps'),'canvas.fps',1,120); duration=_int(raw.get('duration_frames'),'duration_frames',1,fps*60*60)
    bg=_color(raw.get('background',[0,0,0]),'background')
    cam=raw.get('camera',{}) or {}; camera={'x':_track(cam.get('x',0),'camera.x',duration,0),'y':_track(cam.get('y',0),'camera.y',duration,0),'zoom_milli':_track(cam.get('zoom_milli',1000),'camera.zoom_milli',duration,1000)}
    media=[]; mids=set()
    for i,m in enumerate(raw.get('media',[]) or []):
        if not isinstance(m,dict): raise ProjectError(f'media[{i}] invalid')
        mid=_text(m.get('id'),f'media[{i}].id',200)
        if mid in mids: raise ProjectError('duplicate media id')
        mids.add(mid)
        kind=_text(m.get('kind'),f'media[{i}].kind',40)
        if kind not in {'image','video','audio','mesh','font','framestate'}: raise ProjectError(f'media[{i}].kind unsupported')
        row={'id':mid,'kind':kind,'path':_text(m.get('path'),f'media[{i}].path',2000)}
        media.append(row)
    layers=[]; lids=set()
    for i,l in enumerate(raw.get('layers',[]) or []):
        row=_layer(l,i,duration)
        if row['id'] in lids: raise ProjectError('duplicate layer id')
        lids.add(row['id'])
        if row.get('media_id') and row['media_id'] not in mids: raise ProjectError(f"layer {row['id']} references missing media")
        layers.append(row)
    captions=[]
    for i,c in enumerate(raw.get('captions',[]) or []):
        if not isinstance(c,dict): raise ProjectError(f'captions[{i}] invalid')
        s=_int(c.get('start_frame'),f'captions[{i}].start_frame',0,duration-1); e=_int(c.get('end_frame'),f'captions[{i}].end_frame',s+1,duration)
        captions.append({'id':str(c.get('id',f'caption-{i}')),'start_frame':s,'end_frame':e,'text':str(c.get('text','')),'position':c.get('position','bottom'),'scale':_int(c.get('scale',1),f'captions[{i}].scale',1,16),'font_media_id':c.get('font_media_id'),'font_size':_int(c.get('font_size',14),f'captions[{i}].font_size',4,512)})
    audio=[]
    for i,a in enumerate(raw.get('audio',[]) or []):
        if not isinstance(a,dict): raise ProjectError(f'audio[{i}] invalid')
        kind=a.get('kind','tone'); s=_int(a.get('start_frame',0),f'audio[{i}].start_frame',0,duration-1); e=_int(a.get('end_frame',duration),f'audio[{i}].end_frame',s+1,duration)
        row={'id':str(a.get('id',f'audio-{i}')),'kind':kind,'start_frame':s,'end_frame':e,'gain_milli':_track(a.get('gain_milli',1000),f'audio[{i}].gain_milli',duration,1000),'pan_milli':_track(a.get('pan_milli',0),f'audio[{i}].pan_milli',duration,0),'loop':bool(a.get('loop',False)),'source_start_frame':_int(a.get('source_start_frame',0),f'audio[{i}].source_start_frame',0,10_000_000)}
        if kind=='tone': row['frequency_hz']=_int(a.get('frequency_hz',440),f'audio[{i}].frequency_hz',20,20000)
        elif kind=='file': row['path']=_text(a.get('path'),f'audio[{i}].path',2000)
        elif kind=='speech': row.update(text=str(a.get('text','')),voice=str(a.get('voice','en')),rate_wpm=_int(a.get('rate_wpm',165),f'audio[{i}].rate_wpm',80,450))
        elif kind=='child': row['media_id']=_text(a.get('media_id'),f'audio[{i}].media_id',200)
        else: raise ProjectError(f'audio[{i}].kind unsupported')
        audio.append(row)
    markers=[]
    for i,m in enumerate(raw.get('markers',[]) or []): markers.append({'frame':_int(m.get('frame'),f'markers[{i}].frame',0,duration-1),'label':str(m.get('label','')),'kind':m.get('kind','marker')})
    effects=raw.get('effects',[]) or []
    if not isinstance(effects,list) or not all(isinstance(x,str) and x for x in effects): raise ProjectError('effects invalid')
    meta=raw.get('metadata',{}) or {}
    if not isinstance(meta,dict): raise ProjectError('metadata invalid')
    return {'schema':PROJECT_SCHEMA,'id':pid,'title':title,'canvas':{'width':width,'height':height,'fps':fps},'duration_frames':duration,'background':bg,'camera':camera,'media':media,'layers':sorted(layers,key=lambda x:(x['z'],x['id'])),'captions':captions,'audio':audio,'effects':effects,'markers':sorted(markers,key=lambda x:(x['frame'],x['label'])),'metadata':meta}

def load_project(path:Path)->dict[str,Any]:
    try: raw=json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e: raise ProjectError(f'could not load project: {e}') from e
    return normalize_project(raw)
