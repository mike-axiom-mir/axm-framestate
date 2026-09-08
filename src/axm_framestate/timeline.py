from __future__ import annotations
from typing import Any


def _smoothstep_milli(t: int) -> int:
    t=max(0,min(1000,int(t)))
    return (3*t*t//1000) - (2*t*t*t//1_000_000)


def _ease(t:int, name:str)->int:
    if name=='hold': return 0
    if name=='smoothstep': return _smoothstep_milli(t)
    return max(0,min(1000,t))


def sample(track: Any, frame: int, start_frame: int, end_frame: int) -> int:
    """Sample integer/scalar/track state deterministically at one frame."""
    if isinstance(track,bool):
        return int(track)
    if isinstance(track,int):
        return track
    if not isinstance(track,dict):
        raise ValueError('track must be integer or object')
    if 'keyframes' in track:
        rows=track['keyframes']
        if len(rows)==1: return int(rows[0]['value'])
        if frame<=int(rows[0]['frame']): return int(rows[0]['value'])
        if frame>=int(rows[-1]['frame']): return int(rows[-1]['value'])
        for a,b in zip(rows,rows[1:]):
            af,bf=int(a['frame']),int(b['frame'])
            if af<=frame<=bf:
                av,bv=int(a['value']),int(b['value'])
                if bf==af: return bv
                t=(frame-af)*1000//(bf-af)
                t=_ease(t,str(a.get('easing','linear')))
                return av+(bv-av)*t//1000
        return int(rows[-1]['value'])
    a=int(track.get('from',track.get('value',0)))
    b=int(track.get('to',a))
    if end_frame-start_frame<=1: return a
    if frame<=start_frame: t=0
    elif frame>=end_frame-1: t=1000
    else: t=(frame-start_frame)*1000//(end_frame-start_frame-1)
    t=_ease(t,str(track.get('easing','linear')))
    return a+(b-a)*t//1000


def shift_track(track: Any, offset: int) -> Any:
    if not isinstance(track,dict) or 'keyframes' not in track:
        return track
    return {'keyframes':[{**row,'frame':int(row['frame'])+offset} for row in track['keyframes']]}
