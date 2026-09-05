from __future__ import annotations
import copy,math
from pathlib import Path
from .analysis import analyze_render
from .canonical import canonical_json,digest,normalize_project
from .receipts import render_with_receipt,verify_repeat
from .review import review_project
from .rehearsal_metrics import normalize_policy,declared_audio,caption_metrics,fade_violations,text_metrics,wrap_text

def simulate_project(project,output_dir,machine_root,policy=None):
    p=normalize_project(project);pol=normalize_policy(policy);out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);(out/'candidate-project.json').write_bytes(canonical_json(p)+b'\n')
    r=render_with_receipt(p,out,machine_root,assemble=False);review=review_project(p,machine_root);ana=analyze_render(out,300);caps,cv=caption_metrics(p,pol['max_caption_words_per_second_milli']);texts,tv=text_metrics(p,machine_root);dec=declared_audio(p);pcm={'preclip_peak_abs':int(r['audio_manifest'].get('preclip_peak_abs',0)),'clipped_sample_values':int(r['audio_manifest'].get('clipped_sample_values',0))};bad=[]
    if dec['peak_milli']>pol['target_declared_audio_gain_milli'] or pcm['preclip_peak_abs']>pol['target_pcm_peak_abs'] or pcm['clipped_sample_values']:bad.append({'code':'AUDIO_HEADROOM','subject':'audio-mix','evidence':{'declared':dec,'pcm':pcm}})
    bad+=cv+fade_violations(p)+tv
    stable={'schema':'axm.framestate.rehearsal-simulation/v0.1','project_digest':digest(p),'render_receipt_digest':r['receipt_digest'],'review':{'blocks':int(review['blocks']),'warnings':int(review['warnings'])},'metrics':{'declared_audio':dec,'pcm':pcm,'captions':caps,'text_fit':texts,'frame_motion_average_delta_milli':sum(int(x.get('delta_milli',0)) for x in ana.get('frames',[]))//max(1,len(ana.get('frames',[])) )},'violations':sorted(bad,key=lambda v:(v['code'],v['subject']))};stable['violation_count']=len(stable['violations']);stable['simulation_digest']=digest(stable);(out/'simulation.json').write_bytes(canonical_json(stable)+b'\n');return stable

def propose_deltas(p,sim,root,pol):
    out=[];dec=sim['metrics']['declared_audio']['peak_milli'];pre=sim['metrics']['pcm']['preclip_peak_abs']
    if p['audio'] and (dec>pol['target_declared_audio_gain_milli'] or pre>pol['target_pcm_peak_abs'] or sim['metrics']['pcm']['clipped_sample_values']):
        factors=[1000]
        if dec>pol['target_declared_audio_gain_milli']:factors.append(pol['target_declared_audio_gain_milli']*1000//max(1,dec))
        if pre>pol['target_pcm_peak_abs']:factors.append(pol['target_pcm_peak_abs']*1000//max(1,pre))
        ids=[e['id'] for e in p['audio'] if e['kind']!='speech'] or [e['id'] for e in p['audio']];out.append({'code':'AUDIO_HEADROOM','subjects':ids,'factor_milli':max(1,min(factors)),'auto_eligible':'AUDIO_HEADROOM' in pol['auto_accept_codes']})
    text_changes=[]
    for v in sim['violations']:
        code=v['code']
        if code=='CAPTION_READABILITY':
            c=next(c for c in p['captions'] if c['id']==v['subject']);row=v['evidence'];need=math.ceil(row['words']*p['canvas']['fps']*1000/pol['max_caption_words_per_second_milli']);end=min(row['next_caption_start'],c['start_frame']+need)
            if end>c['end_frame']:out.append({'code':code,'subjects':[c['id']],'new_end_frame':end,'auto_eligible':code in pol['auto_accept_codes']})
        elif code=='FADE_BUDGET':
            l=next(l for l in p['layers'] if l['id']==v['subject']);active=l['end_frame']-l['start_frame'];fi,fo=int(l.get('fade_in_frames',0)),int(l.get('fade_out_frames',0));total=max(1,fi+fo);nfi=active*fi//total;out.append({'code':code,'subjects':[l['id']],'fade_in_frames':nfi,'fade_out_frames':active-nfi,'auto_eligible':code in pol['auto_accept_codes']})
        elif code=='TEXT_FIT':
            kind,sid=v['subject'].split(':',1)
            if kind=='layer':spec=next(l for l in p['layers'] if l['id']==sid)
            else:
                c=next(c for c in p['captions'] if c['id']==sid);spec={'text':c['text'],'scale':c.get('scale',1),'font_media_id':c.get('font_media_id'),'font_size':c.get('font_size',14),'padding':2}
            wrapped=wrap_text(p,spec,v['evidence']['available_width'],root)
            if wrapped!=spec['text']:text_changes.append({'subject':v['subject'],'text':wrapped})
    if text_changes:out.append({'code':'TEXT_FIT','subjects':[x['subject'] for x in text_changes],'changes':text_changes,'auto_eligible':'TEXT_FIT' in pol['auto_accept_codes']})
    order={'AUDIO_HEADROOM':0,'CAPTION_READABILITY':1,'FADE_BUDGET':2,'TEXT_FIT':3};return sorted(out,key=lambda x:(order.get(x['code'],99),x['subjects']))

def _scale(t,f):
    if isinstance(t,int):return max(0,t*f//1000)
    if isinstance(t,dict) and 'keyframes' in t:return {'keyframes':[{**k,'value':max(0,int(k['value'])*f//1000)} for k in t['keyframes']]}
    if isinstance(t,dict):return {**t,'from':max(0,int(t['from'])*f//1000),'to':max(0,int(t['to'])*f//1000)}
    return t

def apply_delta(project,q):
    p=copy.deepcopy(normalize_project(project));code=q['code'];subs=set(q.get('subjects',[]))
    if code=='AUDIO_HEADROOM':
        for e in p['audio']:
            if e['id'] in subs:e['gain_milli']=_scale(e.get('gain_milli',1000),int(q['factor_milli']))
    elif code=='CAPTION_READABILITY':
        for c in p['captions']:
            if c['id'] in subs:c['end_frame']=int(q['new_end_frame'])
    elif code=='FADE_BUDGET':
        for l in p['layers']:
            if l['id'] in subs:l['fade_in_frames']=int(q['fade_in_frames']);l['fade_out_frames']=int(q['fade_out_frames'])
    elif code=='TEXT_FIT':
        for ch in q.get('changes',[]):
            kind,sid=ch['subject'].split(':',1);rows=p['layers'] if kind=='layer' else p['captions']
            for row in rows:
                if row['id']==sid:row['text']=ch['text']
    else:raise ValueError(f'unsupported rehearsal delta code: {code}')
    return normalize_project(p)

def _metric(s,code,subs):
    if code=='AUDIO_HEADROOM':return (int(s['metrics']['declared_audio']['peak_milli']),int(s['metrics']['pcm']['preclip_peak_abs']),int(s['metrics']['pcm']['clipped_sample_values']))
    if code=='CAPTION_READABILITY':
        rows={r['id']:r for r in s['metrics']['captions']};v=[int(rows[x]['words_per_second_milli']) for x in subs if x in rows];return (max(v) if v else 0,)
    if code=='FADE_BUDGET':
        rows=[v for v in s['violations'] if v['code']==code and v['subject'] in subs];return (len(rows),sum(max(0,int(v['fade_frames'])-int(v['active_frames'])) for v in rows))
    if code=='TEXT_FIT':
        rows={f"{r['subject_type']}:{r['id']}":r for r in s['metrics']['text_fit']};v=[rows[x] for x in subs if x in rows];return (sum(int(r['overflow_x']) for r in v),sum(int(r['overflow_y']) for r in v))
    return (int(s['violation_count']),)

def compare_simulations(a,b,q):
    before,after=_metric(a,q['code'],q.get('subjects',[])),_metric(b,q['code'],q.get('subjects',[]));improved=all(x<=y for x,y in zip(after,before)) and any(x<y for x,y in zip(after,before));ok=bool(improved and b['review']['blocks']<=a['review']['blocks'] and b['violation_count']<=a['violation_count']);return {'accepted':ok,'code':q['code'],'subjects':q.get('subjects',[]),'target_metric_before':list(before),'target_metric_after':list(after),'blocks_before':a['review']['blocks'],'blocks_after':b['review']['blocks'],'violation_count_before':a['violation_count'],'violation_count_after':b['violation_count'],'acceptance_rule':'target metric must improve; review blocks and total mechanical violations may not increase'}

def rehearse_project(project,output_dir,machine_root,*,policy=None,assemble_final=True,profile='h264',verify_final=False):
    pol=normalize_policy(policy);root=Path(output_dir);root.mkdir(parents=True,exist_ok=True);cur=normalize_project(project);initial=digest(cur);sim=simulate_project(cur,root/'pass-00-initial',machine_root,pol);initial_sim=sim['simulation_digest'];iterations=[];stop='MAX_PASSES_REACHED'
    for n in range(1,pol['max_passes']+1):
        qs=[q for q in propose_deltas(cur,sim,machine_root,pol) if q['auto_eligible']]
        if not qs:stop='NO_JUSTIFIED_AUTO_DELTA';break
        attempts=[];accepted=False;start=digest(cur)
        for i,q in enumerate(qs,1):
            cand=apply_delta(cur,q);cs=simulate_project(cand,root/f'pass-{n:02d}-attempt-{i:02d}',machine_root,pol);cmp=compare_simulations(sim,cs,q);attempts.append({'proposal':q,'candidate_project_digest':digest(cand),'candidate_simulation_digest':cs['simulation_digest'],'comparison':cmp})
            if cmp['accepted']:cur,sim,accepted=cand,cs,True;break
        iterations.append({'pass':n,'starting_project_digest':start,'attempts':attempts,'accepted':accepted})
        if not accepted:stop='NO_EVIDENCE_IMPROVING_DELTA';break
    final=normalize_project(cur);(root/'final-project.json').write_bytes(canonical_json(final)+b'\n');render=render_with_receipt(final,root/'final-render',machine_root,assemble=assemble_final,profile=profile);repeat=verify_repeat(final,root/'final-repeat',machine_root) if verify_final else None;remaining=propose_deltas(final,sim,machine_root,pol)
    if stop=='MAX_PASSES_REACHED' and not remaining:stop='NO_JUSTIFIED_AUTO_DELTA'
    truth={'schema':'axm.framestate.rehearsal-receipt/v0.1','policy':pol,'initial_project_digest':initial,'initial_simulation_digest':initial_sim,'final_project_digest':digest(final),'final_simulation_digest':sim['simulation_digest'],'iterations':iterations,'accepted_delta_count':sum(1 for x in iterations if x['accepted']),'rejected_attempt_count':sum(1 for x in iterations for a in x['attempts'] if not a['comparison']['accepted']),'stop_reason':stop,'remaining_proposals':remaining,'final_render_receipt_digest':render['receipt_digest'],'final_video':render.get('video'),'final_repeat_verification':repeat,'quality_claim':'bounded mechanical rehearsal improved only evidence-backed targets; this does not prove artistic quality or general taste','authority_boundary':'rehearsal may apply only policy-listed bounded deltas whose targeted evidence improves; it cannot change roots, invent intent, merge, canonize or grant permissions'};truth['rehearsal_receipt_digest']=digest(truth);(root/'rehearsal-receipt.json').write_bytes(canonical_json(truth)+b'\n');return truth
