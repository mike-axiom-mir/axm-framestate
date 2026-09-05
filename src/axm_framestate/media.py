from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .canonical import file_digest, digest
from .three_d import load_obj


class MediaError(RuntimeError):
    pass


def ffmpeg_version() -> str | None:
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    p = subprocess.run([exe, "-version"], capture_output=True, text=True, check=False)
    return p.stdout.splitlines()[0] if p.stdout else "ffmpeg-present-version-unknown"


def resolve_source(machine_root: Path, raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path(machine_root) / p
    return p.resolve()


def read_ppm(path: Path) -> tuple[int, int, list[tuple[int,int,int]]]:
    data = Path(path).read_bytes()
    if not data.startswith(b"P6"):
        raise MediaError(f"unsupported conformed PPM: {path}")
    i = 2
    tokens=[]
    n=len(data)
    while len(tokens) < 3:
        while i<n and chr(data[i]).isspace(): i+=1
        if i<n and data[i]==35:
            while i<n and data[i]!=10: i+=1
            continue
        j=i
        while j<n and not chr(data[j]).isspace(): j+=1
        tokens.append(data[i:j].decode('ascii'))
        i=j
    while i<n and chr(data[i]).isspace(): i+=1
    w,h,maxv=map(int,tokens)
    if maxv!=255: raise MediaError("PPM max value must be 255")
    body=data[i:]
    if len(body)!=w*h*3: raise MediaError("PPM payload size mismatch")
    px=[(body[k],body[k+1],body[k+2]) for k in range(0,len(body),3)]
    return w,h,px


def _run(cmd: list[str]) -> None:
    p=subprocess.run(cmd,capture_output=True,text=True,check=False)
    if p.returncode!=0:
        raise MediaError((p.stderr or "ffmpeg failed")[-4000:])


def prepare_media(project: dict[str,Any], cache_dir: Path, machine_root: Path) -> tuple[dict[str,dict[str,Any]], dict[str,Any]]:
    cache_dir=Path(cache_dir); cache_dir.mkdir(parents=True,exist_ok=True)
    exe=shutil.which("ffmpeg")
    assets: dict[str,dict[str,Any]]={}
    rows=[]
    for item in project.get("media",[]):
        src=resolve_source(machine_root,item["path"])
        if not src.is_file(): raise MediaError(f"media source missing: {src}")
        target=cache_dir/item["id"]; target.mkdir(parents=True,exist_ok=True)
        if item["kind"]=="mesh":
            mesh=load_obj(src); assets[item["id"]]={"kind":"mesh","mesh":mesh,"source":src}; rows.append({"id":item["id"],"kind":"mesh","declared_path":item["path"],"source_digest":file_digest(src),"vertex_count":len(mesh["vertices"]),"triangle_count":len(mesh["triangles"])}); continue
        if item["kind"]=="image":
            out=target/"frame-000000.ppm"
            if not exe: raise MediaError("ffmpeg required to conform image media")
            _run([exe,"-y","-loglevel","error","-i",str(src),"-frames:v","1","-pix_fmt","rgb24",str(out)])
            frame_files=[out]
        elif item["kind"]=="video":
            if not exe: raise MediaError("ffmpeg required to conform video media")
            pattern=target/"frame-%06d.ppm"
            _run([exe,"-y","-loglevel","error","-i",str(src),"-vf",f"fps={project['canvas']['fps']}","-pix_fmt","rgb24",str(pattern)])
            frame_files=sorted(target.glob("frame-*.ppm"))
            if not frame_files: raise MediaError(f"video decoded zero frames: {src}")
        else:
            continue
        parsed=[read_ppm(p) for p in frame_files]
        frames=[{"path":p,"width":v[0],"height":v[1],"pixels":v[2]} for p,v in zip(frame_files,parsed)]
        assets[item["id"]]={"kind":item["kind"],"frames":frames,"source":src}
        rows.append({
            "id":item["id"],"kind":item["kind"],"declared_path":item["path"],
            "source_digest":file_digest(src),"frame_count":len(frame_files),
            "conformed_frame_digests":[file_digest(p) for p in frame_files],
        })
    manifest={"schema":"axm.framestate.media-conform/v0.2","ffmpeg":ffmpeg_version(),"assets":rows}
    manifest["manifest_digest"]=digest(manifest)
    return assets,manifest


def scale_nearest(src: list[tuple[int,int,int]], sw:int, sh:int, dw:int, dh:int) -> list[tuple[int,int,int]]:
    if dw<=0 or dh<=0: return []
    out=[]
    for y in range(dh):
        sy=min(sh-1,(y*sh)//dh)
        base=sy*sw
        for x in range(dw):
            sx=min(sw-1,(x*sw)//dw)
            out.append(src[base+sx])
    return out
