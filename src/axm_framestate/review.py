from __future__ import annotations
from typing import Any
from .effects import load_effect_library
from .timeline import sample

def review_project(project:dict[str,Any],machine_root)->dict[str,Any]:
    w,h=project['canvas']['width'],project['canvas']['height'];dur=project['duration_frames'];findings=[];lib=load_effect_library(machine_root)
    for ref in project['effects']:
        if ref not in lib: findings.append({'severity':'block','code':'MISSING_EFFECT','subject':ref,'evidence':'effect ref absent from live library'})
    for l in project['layers']:
        fs=sorted(set([l['start_frame'],(l['start_frame']+l['end_frame']-1)//2,l['end_frame']-1]));obs=[];near=0;transparent=0
        for f in fs:
            x=sample(l['x'],f,l['start_frame'],l['end_frame']);y=sample(l['y'],f,l['start_frame'],l['end_frame']);op=sample(l['opacity_milli'],f,l['start_frame'],l['end_frame']);v=(-w<=x<=2*w and -h<=y<=2*h);near+=v;transparent+=op<50;obs.append({'frame':f,'x':x,'y':y,'opacity_milli':op,'coarsely_near_canvas':v})
        if near==0: findings.append({'severity':'warn','code':'LAYER_COARSELY_OFFSCREEN','subject':l['id'],'evidence':obs})
        if transparent==len(fs): findings.append({'severity':'warn','code':'LAYER_EFFECTIVELY_TRANSPARENT','subject':l['id'],'evidence':obs})
    # declared gain overlap only, not loudness
    points=sorted({0,dur-1,*[a['start_frame'] for a in project['audio']],*[max(0,a['end_frame']-1) for a in project['audio']]})
    peak=0;pf=0
    for f in points:
        g=sum(sample(a.get('gain_milli',1000),f,a['start_frame'],a['end_frame']) for a in project['audio'] if a['start_frame']<=f<a['end_frame'])
        if g>peak:peak,pf=g,f
    if peak>2000: findings.append({'severity':'warn','code':'DECLARED_AUDIO_GAIN_OVERLAP','subject':'audio','evidence':{'frame':pf,'summed_gain_milli':peak},'note':'declared-gain evidence only, not measured loudness'})
    zvals=[sample(project['camera']['zoom_milli'],f,0,dur) for f in (0,max(0,dur//2),dur-1)]
    if max(zvals)>4000 or min(zvals)<200: findings.append({'severity':'note','code':'EXTREME_CAMERA_ZOOM','subject':'camera','evidence':zvals})
    return {'schema':'axm.framestate.mechanical-review/v0.4','finding_count':len(findings),'blocks':sum(x['severity']=='block' for x in findings),'warnings':sum(x['severity']=='warn' for x in findings),'findings':findings,'truth_boundary':'bounded mechanical evidence only; this does not score story, beauty, originality or emotional truth'}
