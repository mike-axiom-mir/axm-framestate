from __future__ import annotations
import math
from pathlib import Path
from .media import resolve_source
from .text import bitmap_text,shaped_text
from .timeline import sample

SCHEMA='axm.framestate.rehearsal-policy/v0.1'
DEFAULT={'schema':SCHEMA,'max_passes':4,'target_declared_audio_gain_milli':1600,'target_pcm_peak_abs':30000,'max_caption_words_per_second_milli':3500,'auto_accept_codes':['AUDIO_HEADROOM','CAPTION_READABILITY','FADE_BUDGET','TEXT_FIT']}

def normalize_policy(raw=None):
    s={**DEFAULT,**(raw or {})};unknown=set(s)-set(DEFAULT)
    if unknown: raise ValueError(f'rehearsal policy has unknown fields: {sorted(unknown)}')
    if s.get('schema')!=SCHEMA: raise ValueError('unsupported rehearsal policy schema')
    o={'schema':SCHEMA,'max_passes':int(s['max_passes']),'target_declared_audio_gain_milli':int(s['target_declared_audio_gain_milli']),'target_pcm_peak_abs':int(s['target_pcm_peak_abs']),'max_caption_words_per_second_milli':int(s['max_caption_words_per_second_milli']),'auto_accept_codes':sorted(set(s['auto_accept_codes']))}
    if not 0<=o['max_passes']<=12: raise ValueError('max_passes must be between 0 and 12')
    if not 100<=o['target_declared_audio_gain_milli']<=10000: raise ValueError('target_declared_audio_gain_milli out of range')
    if not 1000<=o['target_pcm_peak_abs']<=32767: raise ValueError('target_pcm_peak_abs out of range')
    if not 500<=o['max_caption_words_per_second_milli']<=12000: raise ValueError('max_caption_words_per_second_milli out of range')
    if not all(isinstance(x,str) and x for x in o['auto_accept_codes']): raise ValueError('auto_accept_codes must be a string list')
    return o

def declared_audio(p):
    peak,pf,rows=0,0,[]
    for f in range(p['duration_frames']):
        r=[];total=0
        for e in p['audio']:
            if e['start_frame']<=f<e['end_frame']:
                g=max(0,sample(e.get('gain_milli',1000),f,e['start_frame'],e['end_frame']));total+=g;r.append({'id':e['id'],'kind':e['kind'],'gain_milli':g})
        if total>peak: peak,pf,rows=total,f,r
    return {'peak_milli':peak,'frame':pf,'contributors':rows}

def caption_metrics(p,max_wps):
    fps=p['canvas']['fps'];ordered=sorted(p['captions'],key=lambda c:(c['start_frame'],c['end_frame'],c['id']));rows=[];bad=[]
    for i,c in enumerate(ordered):
        words=len(str(c['text']).split());frames=max(1,c['end_frame']-c['start_frame']);rate=words*fps*1000//frames;next_start=ordered[i+1]['start_frame'] if i+1<len(ordered) else p['duration_frames'];row={'id':c['id'],'words':words,'frames':frames,'words_per_second_milli':rate,'next_caption_start':next_start};rows.append(row)
        if words and rate>max_wps: bad.append({'code':'CAPTION_READABILITY','subject':c['id'],'evidence':row})
    return rows,bad

def fade_violations(p):
    out=[]
    for l in p['layers']:
        active=l['end_frame']-l['start_frame'];fade=int(l.get('fade_in_frames',0))+int(l.get('fade_out_frames',0))
        if fade>active: out.append({'code':'FADE_BUDGET','subject':l['id'],'active_frames':active,'fade_frames':fade})
    return out

def raster_size(p,spec,root):
    text=str(spec.get('text',''));pad=int(spec.get('padding',0) or 0);fid=spec.get('font_media_id')
    if fid:
        m=next((m for m in p.get('media',[]) if m['id']==fid and m['kind']=='font'),None)
        if not m:return 0,0
        w,h,_,_=shaped_text(text,resolve_source(root,m['path']),int(spec.get('font_size',16)),(255,255,255),None,pad);return w,h
    w,h,_,_=bitmap_text(text,int(spec.get('scale',1)),(255,255,255),None,pad);return w,h

def wrap_text(p,spec,width,root):
    words=str(spec.get('text','')).replace('\n',' ').split()
    if not words:return ''
    lines=[];cur=''
    for word in words:
        cand=word if not cur else cur+' '+word
        if raster_size(p,{**spec,'text':cand},root)[0]<=width:cur=cand;continue
        if cur:lines.append(cur);cur=''
        if raster_size(p,{**spec,'text':word},root)[0]<=width:cur=word;continue
        chunk=''
        for ch in word:
            cand=chunk+ch
            if chunk and raster_size(p,{**spec,'text':cand},root)[0]>width:lines.append(chunk);chunk=ch
            else:chunk=cand
        cur=chunk
    if cur:lines.append(cur)
    return '\n'.join(lines)

def text_metrics(p,root):
    aw,ah=max(8,p['canvas']['width']-8),max(8,p['canvas']['height']-8);rows=[];bad=[];subjects=[]
    subjects += [('layer',l['id'],l) for l in p['layers'] if l['kind']=='text']
    subjects += [('caption',c['id'],{'text':c['text'],'scale':c.get('scale',1),'font_media_id':c.get('font_media_id'),'font_size':c.get('font_size',14),'padding':2}) for c in p['captions']]
    for kind,sid,spec in subjects:
        w,h=raster_size(p,spec,root);row={'subject_type':kind,'id':sid,'width':w,'height':h,'available_width':aw,'available_height':ah,'overflow_x':max(0,w-aw),'overflow_y':max(0,h-ah)};rows.append(row)
        if row['overflow_x'] or row['overflow_y']:bad.append({'code':'TEXT_FIT','subject':f'{kind}:{sid}','evidence':row})
    return rows,bad
