from __future__ import annotations
import copy,json
from pathlib import Path
from typing import Any
from .canonical import PROJECT_SCHEMA,canonical_json,normalize_project,digest
from .timeline import shift_track

BRIEF_SCHEMA = 'axm.framestate.creative-brief/v0.1'


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
    for key in camera:
        by={int(r['frame']):r for r in camera[key]['keyframes']};camera[key]['keyframes']=[by[f] for f in sorted(by)]
    project={'schema':PROJECT_SCHEMA,'id':raw.get('id','compiled-film'),'title':raw.get('title',raw.get('id','Compiled Film')),'canvas':raw['canvas'],'duration_frames':offset,'background':raw.get('background',[0,0,0]),'camera':camera,'media':raw.get('media',[]),'layers':layers,'captions':captions,'audio':audio,'effects':raw.get('effects',[]),'markers':markers,'metadata':{**raw.get('metadata',{}),'compiled_from':'shot-plan','shot_count':len(shots)}}
    return normalize_project(project)


def _duration_partition(total:int,weights:list[int])->list[int]:
    if total < len(weights)*2: raise ValueError('creative brief duration too short for beat count')
    sw=sum(weights);out=[];used=0
    for i,w in enumerate(weights):
        if i==len(weights)-1: dur=total-used
        else:
            dur=max(2,total*w//sw);used+=dur
        out.append(dur)
    while sum(out)>total:
        i=max(range(len(out)),key=lambda j:out[j]);out[i]-=1
    while sum(out)<total:
        out[-1]+=1
    return out


def _palette(style:str)->dict[str,list[int]]:
    palettes={
        'cinematic':{'bg':[6,8,15],'primary':[86,170,255],'accent':[255,115,80],'text':[245,248,255]},
        'clean':{'bg':[236,240,246],'primary':[42,78,120],'accent':[24,150,140],'text':[18,24,34]},
        'energetic':{'bg':[12,5,18],'primary':[255,65,145],'accent':[80,225,255],'text':[255,250,245]},
        'minimal':{'bg':[12,12,12],'primary':[220,220,220],'accent':[120,120,120],'text':[250,250,250]},
        'documentary':{'bg':[18,20,19],'primary':[196,174,126],'accent':[136,166,148],'text':[242,238,226]},
    }
    return palettes.get(style,palettes['cinematic'])


def _builtin_shot(kind:str,beat:dict[str,Any],duration:int,index:int,pal:dict[str,list[int]],media_by_id:dict[str,dict[str,Any]],fps:int,width:int,height:int)->dict[str,Any]:
    text=str(beat.get('text','')).strip() or f'BEAT {index+1}'
    sid=f"beat-{index+1}-{kind}";cx=width//2;cy=height//2
    common={'id':sid,'label':text[:80],'duration_frames':duration,'camera':{},'layers':[],'captions':[],'audio':[]}
    if kind=='title':
        common['camera']={'zoom_milli':{'from':920,'to':1080,'easing':'smoothstep'}}
        common['layers']=[
            {'id':'particles','kind':'particles','z':0,'x':cx,'y':height-30,'count':70,'seed':index+17,'spread_x':max(40,width//2),'spread_y':max(20,height//4),'speed':2,'size':2,'color':pal['primary']},
            {'id':'title','kind':'text','z':5,'text':text,'scale':2,'x':{'from':max(10,cx-80),'to':cx,'easing':'smoothstep'},'y':cy,'color':pal['text'],'background_color':pal['bg'],'padding':3,'fade_in_frames':max(1,fps//3),'fade_out_frames':max(1,fps//4)},
        ]
    elif kind in {'media','footage'} and beat.get('media_id') in media_by_id:
        mid=str(beat['media_id']);mk=media_by_id[mid]['kind'];layer_kind='video' if mk=='video' else 'image'
        common['camera']={'zoom_milli':{'from':1000,'to':1120,'easing':'smoothstep'}}
        common['layers']=[
            {'id':'media','kind':layer_kind,'media_id':mid,'z':1,'x':cx,'y':cy,'w':{'from':max(64,width*3//4),'to':max(72,width*9//10),'easing':'smoothstep'},'h':{'from':max(48,height*3//4),'to':max(54,height*9//10),'easing':'smoothstep'},'loop':True if layer_kind=='video' else False,'fade_in_frames':max(1,fps//4),'fade_out_frames':max(1,fps//4)},
            {'id':'caption-card','kind':'text','z':6,'text':text,'scale':1,'x':cx,'y':max(14,height//7),'color':pal['text'],'background_color':pal['bg'],'padding':2},
        ]
    elif kind in {'reveal','3d'}:
        mesh_id=beat.get('media_id') if beat.get('media_id') in media_by_id and media_by_id[str(beat.get('media_id'))]['kind']=='mesh' else None
        if mesh_id:
            obj={'id':'hero','kind':'mesh3d','media_id':mesh_id,'z':2,'x':0,'y':0,'depth':{'from':280,'to':220,'easing':'smoothstep'},'size':72,'rot_x_mdeg':{'from':-10000,'to':25000},'rot_y_mdeg':{'from':0,'to':220000},'rot_z_mdeg':0,'color':pal['primary'],'shadow':True}
        else:
            obj={'id':'hero','kind':'cube3d','z':2,'x':0,'y':0,'depth':{'from':260,'to':205,'easing':'smoothstep'},'size':72,'rot_x_mdeg':{'from':-15000,'to':30000},'rot_y_mdeg':{'from':0,'to':240000},'rot_z_mdeg':{'from':0,'to':25000},'color':pal['primary'],'shadow':True}
        common['layers']=[obj,{'id':'label','kind':'text','z':6,'text':text,'scale':1,'x':cx,'y':max(14,height//7),'color':pal['text'],'background_color':pal['bg'],'padding':2}]
    elif kind=='closing':
        common['camera']={'zoom_milli':{'from':1120,'to':900,'easing':'smoothstep'}}
        common['layers']=[
            {'id':'orb','kind':'circle','z':1,'x':cx,'y':cy,'radius':{'from':10,'to':max(30,min(width,height)//3),'easing':'smoothstep'},'color':pal['accent'],'fade_in_frames':2},
            {'id':'closing','kind':'text','z':5,'text':text,'scale':2,'x':cx,'y':cy,'color':pal['text'],'background_color':pal['bg'],'padding':3},
        ]
    else:
        common['layers']=[
            {'id':'bar','kind':'rect','z':1,'x':{'from':max(20,cx-100),'to':cx,'easing':'smoothstep'},'y':cy,'w':{'from':50,'to':max(120,width*3//5),'easing':'smoothstep'},'h':max(36,height//4),'color':pal['primary'],'fade_in_frames':2,'fade_out_frames':2},
            {'id':'message','kind':'text','z':5,'text':text,'scale':1,'x':cx,'y':cy,'color':pal['text'],'background_color':pal['bg'],'padding':3},
        ]
    if beat.get('caption'):
        common['captions'].append({'id':'caption','start_frame':0,'end_frame':duration,'text':str(beat['caption']),'position':'bottom','scale':1})
    narration=beat.get('narration')
    if narration:
        common['audio'].append({'id':'voice','kind':'speech','start_frame':0,'end_frame':duration,'text':str(narration),'voice':str(beat.get('voice','en')),'rate_wpm':int(beat.get('rate_wpm',165)),'gain_milli':800,'pan_milli':0})
    return common


def compile_brief(raw:dict[str,Any],machine_root:Path|None=None)->dict[str,Any]:
    if raw.get('schema')!=BRIEF_SCHEMA: raise ValueError('unsupported creative-brief schema')
    allowed={'schema','id','title','canvas','duration_frames','background','style','format','media','beats','effects','metadata','bed_tone'}
    if set(raw)-allowed: raise ValueError(f"creative brief has unknown fields: {sorted(set(raw)-allowed)}")
    canvas=raw.get('canvas',{})
    width=int(canvas.get('width',320));height=int(canvas.get('height',180));fps=int(canvas.get('fps',12));total=int(raw['duration_frames']);style=str(raw.get('style','cinematic'));pal=_palette(style)
    media=copy.deepcopy(raw.get('media',[]));media_by_id={str(m['id']):m for m in media}
    beats=raw.get('beats',[]) or []
    if not beats: raise ValueError('creative brief requires at least one beat')
    weights=[max(1,int(b.get('weight',1))) for b in beats];durations=_duration_partition(total,weights)
    installed={}
    if machine_root is not None:
        from .recipes import load_recipe_library
        installed=load_recipe_library(machine_root)
    shots=[]
    for i,(beat,dur) in enumerate(zip(beats,durations)):
        recipe_ref=beat.get('recipe_ref')
        if recipe_ref:
            if recipe_ref not in installed: raise ValueError(f'recipe not installed: {recipe_ref}')
            from .recipes import instantiate_recipe
            values=copy.deepcopy(beat.get('values',{}));values.setdefault('duration_frames',dur);values.setdefault('text',str(beat.get('text','')))
            shot=instantiate_recipe(installed[recipe_ref],values);shot['duration_frames']=dur;shot['id']=f"beat-{i+1}-{installed[recipe_ref]['id']}"
        else:
            shot=_builtin_shot(str(beat.get('kind','message')),beat,dur,i,pal,media_by_id,fps,width,height)
        shots.append(shot)
    bed=raw.get('bed_tone')
    if bed:
        freq=int(bed.get('frequency_hz',82));gain=int(bed.get('gain_milli',30))
        for shot in shots:
            shot.setdefault('audio',[]).insert(0,{'id':'bed','kind':'tone','start_frame':0,'end_frame':shot['duration_frames'],'frequency_hz':freq,'gain_milli':gain,'pan_milli':0})
    plan={'schema':'axm.framestate.shot-plan/v0.2','id':raw.get('id','brief-film'),'title':raw.get('title',raw.get('id','Brief Film')),'canvas':{'width':int(canvas.get('width',320)),'height':int(canvas.get('height',180)),'fps':fps},'background':raw.get('background',pal['bg']),'media':media,'effects':raw.get('effects',[]),'shots':shots,'metadata':{**raw.get('metadata',{}),'compiled_from':'creative-brief','style':style,'format':raw.get('format','general'),'beat_count':len(beats)}}
    return compile_plan(plan)


def compile_plan_file(source:Path,target:Path)->dict[str,Any]:
    raw=json.loads(Path(source).read_text(encoding='utf-8'));project=compile_plan(raw);p=Path(target);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical_json(project)+b'\n');return {'path':str(p),'project_digest':digest(project),'duration_frames':project['duration_frames'],'shot_count':len(raw.get('shots',[]))}


def compile_brief_file(source:Path,target:Path,machine_root:Path|None=None)->dict[str,Any]:
    raw=json.loads(Path(source).read_text(encoding='utf-8'));project=compile_brief(raw,machine_root);p=Path(target);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical_json(project)+b'\n');return {'path':str(p),'project_digest':digest(project),'duration_frames':project['duration_frames'],'beat_count':len(raw.get('beats',[]))}
