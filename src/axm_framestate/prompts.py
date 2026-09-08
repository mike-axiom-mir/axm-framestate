from __future__ import annotations
import copy,re
from pathlib import Path
from typing import Any
from .canonical import canonical_json,digest,load_project,normalize_project
from .rehearsal import rehearse_project

PROMPT_SCHEMA='axm.framestate.prompt/v0.1';PROMPT_PLAN_SCHEMA='axm.framestate.prompt-plan/v0.1';PROMPT_RECEIPT_SCHEMA='axm.framestate.prompt-receipt/v0.1'
STYLE_BUNDLES={
'cinematic':{'ref':'builtin:prompt-style.cinematic@1','meaning':'smooth camera easing + bounded visual fades + restrained non-speech audio; not an artistic-quality claim','operations':[{'op':'camera-smoothstep'},{'op':'visual-fades','frames':3},{'op':'scale-non-speech-audio','factor_milli':900}]},
'cleaner':{'ref':'builtin:prompt-style.cleaner@1','meaning':'reduce particle density and non-speech audio without deleting textual/narrative content','operations':[{'op':'scale-particles','factor_milli':700},{'op':'scale-non-speech-audio','factor_milli':900}]},
'documentary':{'ref':'builtin:prompt-style.documentary@1','meaning':'restrained camera easing + modest fades + lower non-speech audio','operations':[{'op':'camera-smoothstep'},{'op':'visual-fades','frames':2},{'op':'scale-non-speech-audio','factor_milli':850}]},
'warmer':{'ref':'builtin:prompt-style.warmer@1','meaning':'fixed integer shift toward red/yellow for non-text scene colors','operations':[{'op':'color-temperature','red_delta':12,'green_delta':4,'blue_delta':-10}]},
'cooler-color':{'ref':'builtin:prompt-style.cooler-color@1','meaning':'fixed integer shift toward blue for non-text scene colors','operations':[{'op':'color-temperature','red_delta':-10,'green_delta':2,'blue_delta':12}]},
}
TOKEN_SPECS=[
('cooler-color','style',['cooler colors','cooler colours','cooler color','cooler colour']),('bigger-title','direct',['bigger title','make the title bigger','larger title']),('lower-music','direct',['lower the music','quieter music','music quieter','turn the music down']),('longer-captions','direct',['longer captions','hold captions longer','keep captions longer']),('slower-footage','direct',['slower footage','slow the footage','slow down the footage']),('faster-footage','direct',['faster footage','speed up the footage','speed the footage up']),('more-readable','direct',['more readable','easier to read','improve readability']),('cinematic','style',['cinematic']),('documentary','style',['documentary']),('cleaner','style',['cleaner','less busy']),('warmer','style',['warmer colors','warmer colours','warmer'])]
AMBIGUOUS={
'cooler':{'phrase':'cooler','reason':'could mean lower color temperature, more stylish, calmer, or generally better','candidates':['cooler-color','cleaner','external-semantic-interpretation']},
'dramatic':{'phrase':'dramatic','reason':'could refer to pacing, contrast, framing, sound, story, or performance','candidates':['external-semantic-interpretation']},
'epic':{'phrase':'epic','reason':'subjective semantic direction has no single native state mapping in v0.7','candidates':['external-semantic-interpretation']},
'intense':{'phrase':'intense','reason':'subjective semantic direction has no single native state mapping in v0.7','candidates':['external-semantic-interpretation']},
'lonely':{'phrase':'lonely','reason':'emotional meaning is an interpretation surface rather than deterministic project truth','candidates':['external-semantic-interpretation']},
'hopeful':{'phrase':'hopeful','reason':'emotional meaning is an interpretation surface rather than deterministic project truth','candidates':['external-semantic-interpretation']},
}
STOP={'a','an','and','be','but','can','could','film','for','i','it','keep','look','make','me','movie','of','please','slightly','somewhat','the','this','to','video','with','feel','feels','like','more','less','overall','just','little','bit','very','really','also','while'}

def _clean(s:str)->str:return ' '.join(s.lower().strip().split())
def _has(s,p):return re.search(r'(?<![a-z0-9])'+re.escape(p)+r'(?![a-z0-9])',s) is not None

def normalize_prompt(raw):
    if not isinstance(raw,dict):raise ValueError('prompt must be an object')
    allowed={'schema','id','text','allow_classes','ambiguity_policy','scope','metadata'};extra=set(raw)-allowed
    if extra:raise ValueError(f'prompt has unknown fields: {sorted(extra)}')
    if raw.get('schema')!=PROMPT_SCHEMA:raise ValueError(f'schema must be {PROMPT_SCHEMA}')
    pid,text=raw.get('id'),raw.get('text')
    if not isinstance(pid,str) or not pid.strip():raise ValueError('prompt id must be non-empty text')
    if not isinstance(text,str) or not text.strip() or len(text)>4000:raise ValueError('prompt text must be 1..4000 characters')
    allow=raw.get('allow_classes',['direct','style','semantic'])
    if not isinstance(allow,list) or not allow or any(x not in {'direct','style','semantic'} for x in allow):raise ValueError('allow_classes must contain direct/style/semantic')
    amb=raw.get('ambiguity_policy','hold');scope=raw.get('scope','all');meta=raw.get('metadata',{}) or {}
    if amb not in {'hold','error'}:raise ValueError('ambiguity_policy must be hold or error')
    if scope!='all':raise ValueError("v0.7 supports only scope='all'")
    if not isinstance(meta,dict):raise ValueError('metadata must be an object')
    return {'schema':PROMPT_SCHEMA,'id':pid.strip(),'text':text.strip(),'allow_classes':sorted(set(allow)),'ambiguity_policy':amb,'scope':'all','metadata':meta}

def _ops(token,p):
    fps=int(p['canvas']['fps'])
    if token in STYLE_BUNDLES:
        b=STYLE_BUNDLES[token];return copy.deepcopy(b['operations']),[],b['ref']
    m={'lower-music':([{'op':'scale-non-speech-audio','factor_milli':750}],[]),'bigger-title':([{'op':'scale-title','factor_milli':1250}],['TEXT_FIT']),'longer-captions':([{'op':'extend-captions','frames':max(1,fps//2)}],['CAPTION_READABILITY','TEXT_FIT']),'slower-footage':([{'op':'scale-video-playback','factor_milli':800}],[]),'faster-footage':([{'op':'scale-video-playback','factor_milli':1250}],[]),'more-readable':([],['CAPTION_READABILITY','TEXT_FIT','AUDIO_HEADROOM'])}
    if token not in m:raise ValueError(f'unknown prompt token: {token}')
    return m[token][0],m[token][1],None

def interpret_prompt(project,raw_prompt):
    p=normalize_project(project);pr=normalize_prompt(raw_prompt);txt=_clean(pr['text']);cons=[];rec=[];specs=[]
    for token,cls,phrases in TOKEN_SPECS:
        for phrase in phrases:specs.append((len(phrase),token,cls,phrase))
    for _,token,cls,phrase in sorted(specs,key=lambda x:(-x[0],x[3])):
        for m in re.finditer(r'(?<![a-z0-9])'+re.escape(phrase)+r'(?![a-z0-9])',txt):
            if any(not(m.end()<=a or m.start()>=b) for a,b in cons):continue
            cons.append((m.start(),m.end()));allowed=cls in pr['allow_classes'];operations,hints,bref=_ops(token,p)
            rec.append({'token':token,'class':cls,'matched_phrase':phrase,'allowed':allowed,'bundle_ref':bref,'operations':operations if allowed else [],'rehearsal_hints':hints if allowed else [],'hold_reason':None if allowed else f'prompt class {cls} is disabled by allow_classes'})
    amb=[]
    for key,item in sorted(AMBIGUOUS.items()):
        if _has(txt,item['phrase']) and not(key=='cooler' and any(r['token']=='cooler-color' for r in rec)):amb.append({'term':key,**item})
    if amb and pr['ambiguity_policy']=='error':raise ValueError('ambiguous prompt terms: '+', '.join(x['term'] for x in amb))
    chars=list(txt)
    for a,b in cons:
        for i in range(a,b):chars[i]=' '
    left=''.join(chars)
    for x in amb:left=re.sub(r'(?<![a-z0-9])'+re.escape(x['phrase'])+r'(?![a-z0-9])',' ',left)
    unresolved=sorted(set(w for w in re.findall(r"[a-z0-9][a-z0-9'-]*",left) if w not in STOP and len(w)>1))
    operations=[];hints=set()
    for r in rec:
        if r['allowed']:operations+=copy.deepcopy(r['operations']);hints.update(r['rehearsal_hints'])
    dedup={canonical_json(o):o for o in operations};operations=[dedup[k] for k in sorted(dedup)]
    plan={'schema':PROMPT_PLAN_SCHEMA,'prompt':pr,'prompt_text_digest':digest(pr['text']),'normalized_text':txt,'input_project_digest':digest(p),'recognized':sorted(rec,key=lambda r:(r['class'],r['token'],r['matched_phrase'])),'ambiguous':amb,'unresolved_fragments':unresolved,'operations':operations,'rehearsal_hints':sorted(hints),'status':'ACTIONABLE' if operations or hints else ('HELD_AMBIGUOUS' if amb else 'NO_NATIVE_INTERPRETATION'),'truth_boundary':'prompt text is direction, not project truth; only explicit plan operations may change native state'};plan['plan_digest']=digest(plan);return plan

def explain_prompt_token(token):
    key=_clean(token)
    if key in STYLE_BUNDLES:return {'token':key,'class':'style',**copy.deepcopy(STYLE_BUNDLES[key]),'truth_boundary':'versioned native vocabulary, not an artistic-quality claim'}
    direct=next((x for x in TOKEN_SPECS if x[0]==key and x[1]=='direct'),None)
    if direct:
        ops,hints,_=_ops(key,{'canvas':{'fps':12}});return {'token':key,'class':'direct','phrases':direct[2],'operations_at_12fps':ops,'rehearsal_hints':hints}
    if key in AMBIGUOUS:return {'token':key,'class':'semantic-ambiguity',**AMBIGUOUS[key],'native_action':'hold'}
    return {'token':key,'class':'unknown','native_action':'none'}

def _scale(v,f,lo=None,hi=None):
    one=lambda x:max(lo if lo is not None else -10**9,min(hi if hi is not None else 10**9,int(x)*f//1000))
    if isinstance(v,int):return one(v)
    if isinstance(v,dict) and 'keyframes' in v:return {'keyframes':[{**r,'value':one(r['value'])} for r in v['keyframes']]}
    return {**v,'from':one(v.get('from',v.get('value',0))),'to':one(v.get('to',v.get('from',v.get('value',0))))}
def _smooth(v):
    if isinstance(v,int):return v
    if 'keyframes' in v:return {'keyframes':[{**r,'easing':'hold' if i==len(v['keyframes'])-1 else 'smoothstep'} for i,r in enumerate(v['keyframes'])]}
    return {**v,'easing':'smoothstep'}
def _color(c,r,g,b):return [max(0,min(255,c[0]+r)),max(0,min(255,c[1]+g)),max(0,min(255,c[2]+b))]

def apply_prompt_plan(project,plan):
    p=copy.deepcopy(normalize_project(project))
    if plan.get('schema')!=PROMPT_PLAN_SCHEMA:raise ValueError('unsupported prompt plan schema')
    if plan.get('input_project_digest')!=digest(p):raise ValueError('prompt plan input project digest does not match current project')
    applied=[]
    for op in plan.get('operations',[]):
        before=digest(p);kind=op['op']
        if kind=='camera-smoothstep':
            for k in ('x','y','zoom_milli'):p['camera'][k]=_smooth(p['camera'][k])
        elif kind=='visual-fades':
            for l in p['layers']:
                active=l['end_frame']-l['start_frame'];n=min(int(op['frames']),active//2) if active>=4 else 0;l['fade_in_frames']=max(l.get('fade_in_frames',0),n);l['fade_out_frames']=max(l.get('fade_out_frames',0),n)
        elif kind=='scale-non-speech-audio':
            for e in p['audio']:
                if e['kind']!='speech':e['gain_milli']=_scale(e.get('gain_milli',1000),int(op['factor_milli']),0,10000)
        elif kind=='scale-particles':
            for l in p['layers']:
                if l['kind']=='particles':l['count']=max(1,min(10000,l['count']*int(op['factor_milli'])//1000))
        elif kind=='color-temperature':
            p['background']=_color(p['background'],op['red_delta'],op['green_delta'],op['blue_delta'])
            for l in p['layers']:
                if 'color' in l and l['kind']!='text':l['color']=_color(l['color'],op['red_delta'],op['green_delta'],op['blue_delta'])
                if l.get('background_color') is not None:l['background_color']=_color(l['background_color'],op['red_delta'],op['green_delta'],op['blue_delta'])
        elif kind=='scale-title':
            texts=[l for l in p['layers'] if l['kind']=='text'];targets=[l for l in texts if 'title' in l['id'].lower()] or texts[:1]
            for l in targets:old=l.get('scale',1);l['scale']=max(1,min(32,max(old+1,(old*int(op['factor_milli'])+999)//1000)))
        elif kind=='extend-captions':
            rows=sorted(p['captions'],key=lambda c:(c['start_frame'],c['end_frame'],c['id']))
            for i,c in enumerate(rows):c['end_frame']=min(rows[i+1]['start_frame'] if i+1<len(rows) else p['duration_frames'],c['end_frame']+int(op['frames']))
        elif kind=='scale-video-playback':
            for l in p['layers']:
                if l['kind']=='video':l['playback_milli']=_scale(l.get('playback_milli',1000),int(op['factor_milli']),-10000,10000)
        else:raise ValueError(f'unsupported prompt operation: {kind}')
        p=normalize_project(p);applied.append({'operation':op,'changed':digest(p)!=before,'project_digest_after':digest(p)})
    meta=copy.deepcopy(p.get('metadata',{}));history=list(meta.get('prompt_history',[])) if isinstance(meta.get('prompt_history',[]),list) else [];history.append({'prompt_id':plan['prompt']['id'],'prompt_text_digest':plan['prompt_text_digest'],'prompt_plan_digest':plan['plan_digest'],'recognized_tokens':[r['token'] for r in plan['recognized'] if r['allowed']],'ambiguous_terms':[r['term'] for r in plan['ambiguous']]});meta['prompt_history']=history[-32:];p['metadata']=meta
    return {'project':normalize_project(p),'applied_operations':applied}

def prompt_project(project,raw_prompt,output_dir:Path,machine_root:Path,*,rehearse=True,rehearsal_policy=None,profile='h264',verify_final=False):
    src=normalize_project(project);plan=interpret_prompt(src,raw_prompt);applied=apply_prompt_plan(src,plan);cand=applied['project'];out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);(out/'prompt-plan.json').write_bytes(canonical_json(plan)+b'\n');(out/'prompt-candidate-project.json').write_bytes(canonical_json(cand)+b'\n')
    rr=None;final=cand;video=None;repeat=None
    if rehearse:
        rr=rehearse_project(cand,out/'rehearsal',machine_root,policy=rehearsal_policy,assemble_final=True,profile=profile,verify_final=verify_final);final=load_project(out/'rehearsal'/'final-project.json');video=rr.get('final_video');repeat=rr.get('final_repeat_verification')
    else:
        from .receipts import render_with_receipt,verify_repeat
        r=render_with_receipt(cand,out/'final-render',machine_root,assemble=True,profile=profile);video=r.get('video');repeat=verify_repeat(cand,out/'final-repeat',machine_root) if verify_final else None
    receipt={'schema':PROMPT_RECEIPT_SCHEMA,'input_project_digest':digest(src),'prompt_plan_digest':plan['plan_digest'],'candidate_project_digest':digest(cand),'final_project_digest':digest(final),'interpretation_status':plan['status'],'recognized_tokens':[r['token'] for r in plan['recognized'] if r['allowed']],'held_terms':[r['term'] for r in plan['ambiguous']]+list(plan['unresolved_fragments']),'applied_operations':applied['applied_operations'],'rehearsed':bool(rehearse),'rehearsal_receipt_digest':rr.get('rehearsal_receipt_digest') if rr else None,'final_video':video,'final_repeat_verification':repeat,'truth_boundary':'prompt influence became explicit native state operations before rendering; ambiguous/unresolved language gained no hidden mutation authority'};receipt['prompt_receipt_digest']=digest(receipt);(out/'prompt-receipt.json').write_bytes(canonical_json(receipt)+b'\n');return receipt
