from __future__ import annotations
import json, platform, shutil, subprocess
from pathlib import Path
from typing import Any
from .audio import render_audio
from .canonical import canonical_json,digest,file_digest
from .render import render_project
from .captions import export_vtt
from .media import ffmpeg_version


def render_with_receipt(project:dict[str,Any],output_dir:Path,machine_root:Path,*,assemble:bool=True,profile:str='h264')->dict[str,Any]:
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fm=render_project(project,out,machine_root);am=render_audio(project,out/'audio.wav',machine_root,out);subs=export_vtt(project,out/'captions.vtt')
    ver=ffmpeg_version();video=None;assembly={'attempted':False,'succeeded':False,'external_boundary':'ffmpeg','version':ver,'bit_exact_claim':False,'profile':profile}
    if assemble and ver:
        assembly['attempted']=True;fps=project['canvas']['fps'];vp=out/'video.mp4';exe=shutil.which('ffmpeg') or 'ffmpeg'
        if profile=='fast': vcodec=['-c:v','libx264','-preset','veryfast','-crf','24']
        elif profile=='quality': vcodec=['-c:v','libx264','-preset','slow','-crf','17']
        else: vcodec=['-c:v','libx264','-preset','medium','-crf','20']
        cmd=[exe,'-y','-loglevel','error','-framerate',str(fps),'-i',str(out/'frames'/'frame-%06d.ppm'),'-i',str(out/'audio.wav'),*vcodec,'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(vp)]
        p=subprocess.run(cmd,capture_output=True,text=True,check=False);assembly.update(returncode=p.returncode,stderr=p.stderr[-4000:])
        if p.returncode==0 and vp.is_file(): video={'path':str(vp),'digest':file_digest(vp)};assembly['succeeded']=True
    rec={'schema':'axm.framestate.render-receipt/v0.6','project_id':project['id'],'project_digest':digest(project),'media_manifest_digest':fm['media_manifest_digest'],'frame_manifest_digest':fm['manifest_digest'],'audio_manifest':am,'subtitle_export':subs,'video':video,'assembly':assembly,'environment':{'python':platform.python_version(),'platform':platform.platform()},'truth_boundary':{'canonical_project':'normalized and digest-bound','frame_state':'integer/fixed-point native state plus exact PPM bytes','media':'input bytes digest-bound; Pillow/FFmpeg/font runtimes remain named boundaries','audio':'exact mixed PCM/WAV current-runtime truth; imported/speech boundaries receipted','container_video':'external FFmpeg encoding boundary; no universal MP4 bit-identity claim'}}
    stable=json.loads(json.dumps(rec))
    if isinstance(stable.get('subtitle_export'),dict): stable['subtitle_export'].pop('path',None)
    if isinstance(stable.get('video'),dict): stable['video'].pop('path',None)
    rec['receipt_digest']=digest(stable);(out/'render-receipt.json').write_bytes(canonical_json(rec)+b'\n');return rec

def verify_repeat(project:dict[str,Any],base_dir:Path,machine_root:Path)->dict[str,Any]:
    a=render_with_receipt(project,Path(base_dir)/'repeat-a',machine_root,assemble=False);b=render_with_receipt(project,Path(base_dir)/'repeat-b',machine_root,assemble=False)
    am=json.loads((Path(base_dir)/'repeat-a'/'frame-manifest.json').read_text());bm=json.loads((Path(base_dir)/'repeat-b'/'frame-manifest.json').read_text());ame=json.loads((Path(base_dir)/'repeat-a'/'media-manifest.json').read_text());bme=json.loads((Path(base_dir)/'repeat-b'/'media-manifest.json').read_text())
    checks={'project_digest_equal':a['project_digest']==b['project_digest'],'media_manifest_equal':ame==bme,'frame_manifest_equal':am==bm,'audio_pcm_equal':a['audio_manifest']['pcm_digest']==b['audio_manifest']['pcm_digest'],'audio_wav_equal':a['audio_manifest']['wav_digest']==b['audio_manifest']['wav_digest']}
    result={'schema':'axm.framestate.repeat-verification/v0.4','passed':all(checks.values()),'checks':checks,'project_digest':a['project_digest'],'media_manifest_digest':ame['manifest_digest'],'frame_manifest_digest':am['manifest_digest'],'audio_pcm_digest':a['audio_manifest']['pcm_digest'],'claim':'repeat proof covers normalized project, conformed media in this runtime, frame state/PPM and mixed PCM/WAV; external codec/font/speech implementations are versioned boundaries'};result['verification_digest']=digest(result);return result
