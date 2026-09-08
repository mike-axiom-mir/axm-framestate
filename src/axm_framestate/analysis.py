from __future__ import annotations
from pathlib import Path
from .canonical import digest
from .media import read_ppm

def analyze_render(render_dir:Path,threshold_milli:int=300)->dict:
    frames=sorted((Path(render_dir)/'frames').glob('frame-*.ppm'));rows=[];prev=None;cuts=[]
    for i,p in enumerate(frames):
        w,h,b=read_ppm(p);n=max(1,w*h);avg=[sum(b[c::3])//n for c in range(3)];delta=0
        if prev is not None:
            delta=sum(abs(a-bb) for a,bb in zip(b,prev))*1000//max(1,len(b)*255)
            if delta>=threshold_milli: cuts.append({'frame':i,'delta_milli':delta,'proposal_only':True})
        rows.append({'frame':i,'average_rgb':avg,'delta_milli':delta});prev=b
    out={'schema':'axm.framestate.frame-analysis/v0.1','frame_count':len(rows),'frames':rows,'proposed_cuts':cuts,'mutated_project':False,'truth_boundary':'cut detections are evidence/proposals only; analysis never edits canonical state'};out['digest']=digest(out);return out
