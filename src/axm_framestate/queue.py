from __future__ import annotations
import json
from pathlib import Path
from .canonical import digest,load_project,canonical_json
from .receipts import render_with_receipt

def render_queue(path:Path,machine_root:Path)->dict:
    raw=json.loads(Path(path).read_text(encoding='utf-8'));rows=[]
    for job in raw.get('jobs',[]):
        project=load_project(Path(job['project']));rec=render_with_receipt(project,Path(job['output']),machine_root,assemble=bool(job.get('assemble',True)),profile=job.get('profile','h264'));rows.append({'id':job.get('id',project['id']),'project_digest':rec['project_digest'],'receipt_digest':rec['receipt_digest'],'video':rec['video']})
    out={'schema':'axm.framestate.render-queue-receipt/v0.1','jobs':rows};out['digest']=digest(out);return out
