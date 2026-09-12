from __future__ import annotations
import hashlib, math, shutil, struct, subprocess, wave
from pathlib import Path
from typing import Any
from .canonical import digest,file_digest
from .media import resolve_source, ffmpeg_version
from .native_audio import NativeAudioError, decode_wav_bytes
from .timeline import sample
from .speech import synthesize_native

SAMPLE_RATE=48000

class AudioError(RuntimeError): pass

def _looks_like_wav(data:bytes)->bool:
    return len(data)>=12 and data[:4]==b'RIFF' and data[8:12]==b'WAVE'

def _decode_audio_with_evidence(path:Path,channels:int=1)->tuple[bytes,dict[str,Any]]:
    path=Path(path); data=path.read_bytes()
    if _looks_like_wav(data):
        try:return decode_wav_bytes(data,SAMPLE_RATE,channels)
        except NativeAudioError as exc: raise AudioError(str(exc)) from exc
    exe=shutil.which('ffmpeg')
    if not exe: raise AudioError('ffmpeg required for imported audio formats other than native PCM WAV')
    p=subprocess.run([exe,'-v','error','-i',str(path),'-ac',str(channels),'-ar',str(SAMPLE_RATE),'-f','s16le','-acodec','pcm_s16le','-'],capture_output=True,check=False)
    if p.returncode!=0: raise AudioError(p.stderr.decode('utf-8','replace')[-4000:])
    return p.stdout,{'boundary':'ffmpeg-audio-decode','decoder':ffmpeg_version(),'target_rate':SAMPLE_RATE,'target_channels':channels}

def _decode_audio(path:Path,channels:int=1)->bytes:
    return _decode_audio_with_evidence(path,channels)[0]

def _decode_audio_bytes_with_evidence(data:bytes,channels:int=1)->tuple[bytes,dict[str,Any]]:
    if _looks_like_wav(data):
        try:return decode_wav_bytes(data,SAMPLE_RATE,channels)
        except NativeAudioError as exc: raise AudioError(str(exc)) from exc
    exe=shutil.which('ffmpeg')
    if not exe: raise AudioError('ffmpeg required for non-WAV speech/audio conform')
    p=subprocess.run([exe,'-v','error','-i','pipe:0','-ac',str(channels),'-ar',str(SAMPLE_RATE),'-f','s16le','-acodec','pcm_s16le','-'],input=data,capture_output=True,check=False)
    if p.returncode!=0: raise AudioError(p.stderr.decode('utf-8','replace')[-4000:])
    return p.stdout,{'boundary':'ffmpeg-audio-bytes-decode','decoder':ffmpeg_version(),'target_rate':SAMPLE_RATE,'target_channels':channels}

def _decode_audio_bytes(data:bytes,channels:int=1)->bytes:
    return _decode_audio_bytes_with_evidence(data,channels)[0]

def _speech_espeak(text:str,voice:str,rate:int)->tuple[bytes,dict[str,Any]]:
    exe=shutil.which('espeak') or shutil.which('espeak-ng')
    if not exe: raise AudioError('espeak/espeak-ng not available')
    v=subprocess.run([exe,'--version'],capture_output=True,text=True,check=False).stdout.splitlines()[:1]
    p=subprocess.run([exe,'--stdout','-s',str(rate),'-v',voice,text],capture_output=True,check=False)
    if p.returncode!=0: raise AudioError(p.stderr.decode('utf-8','replace')[-4000:])
    raw,conform=_decode_audio_bytes_with_evidence(p.stdout,1)
    ev={'synthesizer':v[0] if v else Path(exe).name,'voice':voice,'rate_wpm':rate,'synthesized_wav_digest':'sha256:'+hashlib.sha256(p.stdout).hexdigest(),'decoded_pcm_digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'speech_audio_conform':conform}
    return raw,ev

def _add(samples:list[list[int]],i:int,value:int,gain:int,pan:int,channels:int):
    value=value*gain//1000
    if channels==1:
        samples[0][i]+=value;return
    lg=1000-max(0,pan); rg=1000+min(0,pan)
    samples[0][i]+=value*lg//1000;samples[1][i]+=value*rg//1000

def render_audio(project:dict[str,Any],path:Path,machine_root:Path|None=None,output_dir:Path|None=None)->dict[str,Any]:
    fps=project['canvas']['fps']; total=project['duration_frames']*SAMPLE_RATE//fps
    stereo=any((isinstance(e.get('pan_milli'),int) and e.get('pan_milli')!=0) or isinstance(e.get('pan_milli'),dict) for e in project.get('audio',[]))
    channels=2 if stereo else 1; samples=[[0]*total for _ in range(channels)]; evidence=[];root=Path(machine_root or Path.cwd())
    for event in project.get('audio',[]):
        start=event['start_frame']*SAMPLE_RATE//fps; end=event['end_frame']*SAMPLE_RATE//fps; kind=event['kind']
        vals=[]; ev={'id':event['id'],'kind':kind}
        if kind=='tone':
            freq=event['frequency_hz']; n=max(0,end-start); vals=[int(math.sin(2*math.pi*freq*j/SAMPLE_RATE)*32767) for j in range(n)];ev['frequency_hz']=freq
        elif kind=='file':
            src=resolve_source(root,event['path']); raw,decode_ev=_decode_audio_with_evidence(src,1); vals=[x[0] for x in struct.iter_unpack('<h',raw)]; off=event.get('source_start_frame',0)*SAMPLE_RATE//fps;vals=vals[off:] if off<len(vals) else []
            ev.update(declared_path=event['path'],source_digest=file_digest(src),decoded_pcm_digest='sha256:'+hashlib.sha256(raw).hexdigest(),decoder=decode_ev)
        elif kind=='speech':
            if event.get('engine','native')=='native': raw,sev=synthesize_native(event['text'],event['voice'],event['rate_wpm'])
            else: raw,sev=_speech_espeak(event['text'],event['voice'],event['rate_wpm'])
            vals=[x[0] for x in struct.iter_unpack('<h',raw)];ev.update(sev);ev['engine']=event.get('engine','native');ev.setdefault('text_digest',digest(event['text']))
        elif kind=='child':
            from .media import MediaCache
            cache=MediaCache(project,Path(output_dir or path.parent),root); child=cache.child(event['media_id']); wav=child['output']/'audio.wav';raw,decode_ev=_decode_audio_with_evidence(wav,1);vals=[x[0] for x in struct.iter_unpack('<h',raw)];ev.update(child_project_digest=child['receipt']['project_digest'],child_audio_manifest_digest=child['receipt']['audio_manifest']['manifest_digest'],decoder=decode_ev)
        else: raise AudioError(f'unsupported audio kind {kind}')
        if not vals: evidence.append(ev);continue
        for i in range(max(0,start),min(total,end)):
            local=i-start; j=local%len(vals) if event.get('loop') else local
            if j>=len(vals): break
            frame=event['start_frame']+local*fps//SAMPLE_RATE;gain=max(0,min(4000,sample(event.get('gain_milli',1000),frame,event['start_frame'],event['end_frame'])));pan=max(-1000,min(1000,sample(event.get('pan_milli',0),frame,event['start_frame'],event['end_frame'])));_add(samples,i,vals[j],gain,pan,channels)
        evidence.append(ev)
    preclip_peak=max((abs(v) for channel in samples for v in channel),default=0)
    clipped_values=sum(1 for channel in samples for v in channel if v < -32768 or v > 32767)
    inter=bytearray()
    for i in range(total):
        for c in range(channels):
            v=max(-32768,min(32767,samples[c][i]));inter.extend(struct.pack('<h',v))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as wf: wf.setnchannels(channels);wf.setsampwidth(2);wf.setframerate(SAMPLE_RATE);wf.writeframes(bytes(inter))
    result={'schema':'axm.framestate.audio-manifest/v0.9','sample_rate':SAMPLE_RATE,'channels':channels,'samples_per_channel':total,'pcm_digest':'sha256:'+hashlib.sha256(inter).hexdigest(),'wav_digest':file_digest(path),'events_digest':digest(project.get('audio',[])),'preclip_peak_abs':preclip_peak,'clipped_sample_values':clipped_values,'source_evidence':evidence};result['manifest_digest']=digest(result);return result
