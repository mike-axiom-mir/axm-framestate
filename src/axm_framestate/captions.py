from __future__ import annotations
from pathlib import Path
from .canonical import file_digest,digest

def _ts(ms:int)->str:
    h=ms//3600000;ms%=3600000;m=ms//60000;ms%=60000;s=ms//1000;ms%=1000;return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'

def export_vtt(project,path:Path):
    fps=project['canvas']['fps'];lines=['WEBVTT','']
    for c in project.get('captions',[]):
        lines += [c['id'],f"{_ts(c['start_frame']*1000//fps)} --> {_ts(c['end_frame']*1000//fps)}",c['text'],'']
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(lines),encoding='utf-8')
    return {'schema':'axm.framestate.subtitle-export/v0.1','cue_count':len(project.get('captions',[])),'path':str(p),'digest':file_digest(p),'cues_digest':digest(project.get('captions',[]))}
