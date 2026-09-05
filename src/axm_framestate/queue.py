from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .canonical import digest, canonical_json, load_project
from .receipts import render_with_receipt


def run_queue(queue_file:Path,machine_root:Path)->dict[str,Any]:
    raw=json.loads(Path(queue_file).read_text(encoding='utf-8'))
    if not isinstance(raw,dict) or set(raw)!={"jobs"} or not isinstance(raw["jobs"],list): raise ValueError("queue must be {jobs:[...]}")
    rows=[]
    for i,job in enumerate(raw["jobs"]):
        if not isinstance(job,dict) or set(job)-{"id","project","output","assemble"}: raise ValueError(f"jobs[{i}] unsupported fields")
        jid=str(job.get("id",f"job-{i}")); project_path=Path(job["project"]); output=Path(job["output"]); assemble=bool(job.get("assemble",True))
        project=load_project(project_path); receipt=render_with_receipt(project,output,machine_root,assemble=assemble)
        rows.append({"id":jid,"project":str(project_path),"output":str(output),"receipt_digest":receipt["receipt_digest"],"video":receipt["video"],"passed":True})
    result={"schema":"axm.framestate.render-queue-receipt/v0.2","jobs":rows,"passed":all(r["passed"] for r in rows)}; result["queue_digest"]=digest(result)
    Path(queue_file).with_suffix('.receipt.json').write_bytes(canonical_json(result)+b'\n')
    return result
