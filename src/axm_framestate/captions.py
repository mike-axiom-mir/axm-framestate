from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import file_digest, digest


def _ts(frame:int,fps:int)->str:
    ms=frame*1000//fps; h=ms//3_600_000; ms%=3_600_000; m=ms//60_000; ms%=60_000; s=ms//1000; ms%=1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_webvtt(project:dict[str,Any],path:Path)->dict[str,Any]:
    fps=project["canvas"]["fps"]; lines=["WEBVTT",""]
    for cap in project.get("captions",[]):
        lines += [cap["id"],f"{_ts(cap['start_frame'],fps)} --> {_ts(cap['end_frame'],fps)}",cap["text"],""]
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text("\n".join(lines),encoding="utf-8",newline="\n")
    result={"schema":"axm.framestate.caption-manifest/v0.2","cue_count":len(project.get("captions",[])),"captions_digest":digest(project.get("captions",[])),"webvtt_digest":file_digest(path)}; result["manifest_digest"]=digest(result); return result
