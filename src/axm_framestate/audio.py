from __future__ import annotations

import hashlib
import math
import shutil
import struct
import subprocess
import wave
import io
from pathlib import Path
from typing import Any

from .canonical import digest, file_digest
from .media import resolve_source, ffmpeg_version

SAMPLE_RATE=48000


def _decode_audio(path:Path)->bytes:
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required for imported audio")
    p=subprocess.run([exe,"-v","error","-i",str(path),"-ac","1","-ar",str(SAMPLE_RATE),"-f","s16le","-acodec","pcm_s16le","-"],capture_output=True,check=False)
    if p.returncode!=0: raise RuntimeError(p.stderr.decode("utf-8","replace")[-4000:])
    return p.stdout


def _decode_audio_bytes(data:bytes)->bytes:
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("ffmpeg required for speech audio conform")
    p=subprocess.run([exe,"-v","error","-i","pipe:0","-ac","1","-ar",str(SAMPLE_RATE),"-f","s16le","-acodec","pcm_s16le","-"],input=data,capture_output=True,check=False)
    if p.returncode!=0: raise RuntimeError(p.stderr.decode("utf-8","replace")[-4000:])
    return p.stdout

def _speech(text:str,voice:str,rate:int)->tuple[bytes,dict[str,Any]]:
    exe=shutil.which("espeak") or shutil.which("espeak-ng")
    if not exe: raise RuntimeError("espeak/espeak-ng not available for speech event")
    version=subprocess.run([exe,"--version"],capture_output=True,text=True,check=False).stdout.splitlines()[:1]
    p=subprocess.run([exe,"--stdout","-s",str(rate),"-v",voice,text],capture_output=True,check=False)
    if p.returncode!=0: raise RuntimeError(p.stderr.decode("utf-8","replace")[-4000:])
    raw=_decode_audio_bytes(p.stdout)
    return raw,{"synthesizer":version[0] if version else Path(exe).name,"voice":voice,"rate_wpm":rate,"synthesized_wav_digest":"sha256:"+hashlib.sha256(p.stdout).hexdigest(),"decoded_pcm_digest":"sha256:"+hashlib.sha256(raw).hexdigest()}

def render_audio(project:dict[str,Any],path:Path,machine_root:Path|None=None)->dict[str,Any]:
    fps=project["canvas"]["fps"]; total_samples=project["duration_frames"]*SAMPLE_RATE//fps; samples=[0]*total_samples; evidence=[]
    root=Path(machine_root or Path.cwd())
    for event in project["audio"]:
        start=event["start_frame"]*SAMPLE_RATE//fps; end=event["end_frame"]*SAMPLE_RATE//fps; gain=event["gain_milli"]
        if event["kind"]=="tone":
            freq=event["frequency_hz"]; amp=32767*gain//1000
            for i in range(max(0,start),min(total_samples,end)):
                phase=2.0*math.pi*freq*(i-start)/SAMPLE_RATE; value=int(math.sin(phase)*amp); samples[i]=max(-32768,min(32767,samples[i]+value))
            evidence.append({"id":event["id"],"kind":"tone","frequency_hz":freq})
        elif event["kind"]=="file":
            src=resolve_source(root,event["path"])
            if not src.is_file(): raise RuntimeError(f"audio source missing: {src}")
            raw=_decode_audio(src); vals=[v[0] for v in struct.iter_unpack("<h",raw)]; offset=event["source_start_frame"]*SAMPLE_RATE//fps
            usable=vals[offset:] if offset<len(vals) else []
            for i in range(max(0,start),min(total_samples,end)):
                j=i-start
                if not usable: break
                if event.get("loop"): j%=len(usable)
                elif j>=len(usable): break
                value=usable[j]*gain//1000; samples[i]=max(-32768,min(32767,samples[i]+value))
            evidence.append({"id":event["id"],"kind":"file","declared_path":event["path"],"source_digest":file_digest(src),"decoded_pcm_digest":"sha256:"+hashlib.sha256(raw).hexdigest(),"decoder":ffmpeg_version()})
        else:
            raw,ev=_speech(event["text"],event["voice"],event["rate_wpm"]); vals=[v[0] for v in struct.iter_unpack("<h",raw)]
            for i in range(max(0,start),min(total_samples,end)):
                j=i-start
                if j>=len(vals): break
                value=vals[j]*gain//1000; samples[i]=max(-32768,min(32767,samples[i]+value))
            evidence.append({"id":event["id"],"kind":"speech","text_digest":digest(event["text"]),**ev})
    path.parent.mkdir(parents=True,exist_ok=True); raw_pcm=b"".join(struct.pack("<h",s) for s in samples)
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE); wf.writeframes(raw_pcm)
    result={"schema":"axm.framestate.audio-manifest/v0.2","sample_rate":SAMPLE_RATE,"samples":total_samples,"pcm_digest":"sha256:"+hashlib.sha256(raw_pcm).hexdigest(),"wav_digest":file_digest(path),"events_digest":digest(project["audio"]),"source_evidence":evidence}; result["manifest_digest"]=digest(result); return result
