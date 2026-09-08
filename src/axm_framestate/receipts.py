from __future__ import annotations
import json, platform, shutil, subprocess
from pathlib import Path
from typing import Any
from .audio import render_audio
from .canonical import canonical_json,digest,file_digest
from .render import render_project
from .captions import export_vtt
from .media import ffmpeg_version
from .realization import (
    normalize_machine_capabilities,
    normalize_realization_policy,
    plan_realization,
    verify_contract,
    write_realization_inputs,
)


def _assemble_video(project:dict[str,Any],out:Path,profile:str,assemble:bool,ffmpeg_allowed:bool=True)->tuple[dict[str,Any],dict[str,Any]|None]:
    ver=ffmpeg_version() if ffmpeg_allowed else None;video=None
    assembly={'requested':bool(assemble),'attempted':False,'succeeded':False,'external_boundary':'ffmpeg','version':ver,'bit_exact_claim':False,'profile':profile}
    if assemble and not ffmpeg_allowed: assembly['skipped_reason']='declared machine capability says FFmpeg unavailable'
    if assemble and ffmpeg_allowed and ver:
        assembly['attempted']=True;fps=project['canvas']['fps'];vp=out/'video.mp4';exe=shutil.which('ffmpeg') or 'ffmpeg'
        if profile=='fast': vcodec=['-c:v','libx264','-preset','veryfast','-crf','24']
        elif profile=='quality': vcodec=['-c:v','libx264','-preset','slow','-crf','17']
        else: vcodec=['-c:v','libx264','-preset','medium','-crf','20']
        cmd=[exe,'-y','-loglevel','error','-framerate',str(fps),'-i',str(out/'frames'/'frame-%06d.ppm'),'-i',str(out/'audio.wav'),*vcodec,'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(vp)]
        p=subprocess.run(cmd,capture_output=True,text=True,check=False);assembly.update(returncode=p.returncode,stderr=p.stderr[-4000:])
        if p.returncode==0 and vp.is_file(): video={'path':str(vp),'digest':file_digest(vp)};assembly['succeeded']=True
    return assembly,video


def _stable_receipt_digest(rec:dict[str,Any])->str:
    stable=json.loads(json.dumps(rec))
    if isinstance(stable.get('subtitle_export'),dict): stable['subtitle_export'].pop('path',None)
    if isinstance(stable.get('video'),dict): stable['video'].pop('path',None)
    return digest(stable)


def render_with_receipt(project:dict[str,Any],output_dir:Path,machine_root:Path,*,assemble:bool=True,profile:str='h264')->dict[str,Any]:
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    fm=render_project(project,out,machine_root);am=render_audio(project,out/'audio.wav',machine_root,out);subs=export_vtt(project,out/'captions.vtt')
    assembly,video=_assemble_video(project,out,profile,assemble)
    rec={'schema':'axm.framestate.render-receipt/v0.8','project_id':project['id'],'project_digest':digest(project),'media_manifest_digest':fm['media_manifest_digest'],'frame_manifest_digest':fm['manifest_digest'],'audio_manifest':am,'subtitle_export':subs,'video':video,'assembly':assembly,'environment':{'python':platform.python_version(),'platform':platform.platform()},'truth_boundary':{'canonical_project':'normalized and digest-bound','frame_state':'integer/fixed-point native state plus exact PPM bytes','media':'input bytes digest-bound; Pillow/FFmpeg/font runtimes remain named boundaries','audio':'exact mixed PCM/WAV; native speech is internal deterministic state while imported/explicit external speech paths remain receipted boundaries','container_video':'external FFmpeg encoding boundary; no universal MP4 bit-identity claim'}}
    rec['receipt_digest']=_stable_receipt_digest(rec);(out/'render-receipt.json').write_bytes(canonical_json(rec)+b'\n');return rec


def render_realized_with_receipt(project:dict[str,Any],output_dir:Path,machine_root:Path,machine:dict[str,Any],policy:dict[str,Any]|None=None,*,assemble:bool=True)->dict[str,Any]:
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    machine=normalize_machine_capabilities({k:v for k,v in machine.items() if k not in {'capability_digest','probe_scope'}})
    policy=normalize_realization_policy({k:v for k,v in (policy or {}).items() if k!='policy_digest'})
    contract=plan_realization(project,machine,policy)
    invariant_before=verify_contract(project,contract)
    if not invariant_before['passed']:
        raise ValueError('realization contract does not match canonical project')
    write_realization_inputs(out,machine,policy,contract)
    fm=render_project(project,out,machine_root,realization=contract)
    # v0.9 does not degrade canonical audio/caption state. Those paths are rendered exactly as before.
    am=render_audio(project,out/'audio.wav',machine_root,out);subs=export_vtt(project,out/'captions.vtt')
    assembly,video=_assemble_video(project,out,contract['render']['export_profile'],assemble,machine['ffmpeg_available'])
    invariant_after=verify_contract(project,contract)
    rec={
        'schema':'axm.framestate.render-receipt/v0.9',
        'project_id':project['id'],
        'project_digest':digest(project),
        'media_manifest_digest':fm['media_manifest_digest'],
        'frame_manifest_digest':fm['manifest_digest'],
        'audio_manifest':am,
        'subtitle_export':subs,
        'video':video,
        'assembly':assembly,
        'realization':{
            'machine_capability_digest':machine['capability_digest'],
            'policy_digest':policy['policy_digest'],
            'contract_digest':contract['contract_digest'],
            'tier':contract['tier'],
            'backend':contract['backend'],
            'render':contract['render'],
            'expression_deltas':contract['expression_deltas'],
            'invariants_before':invariant_before,
            'invariants_after':invariant_after,
        },
        'environment':{'python':platform.python_version(),'platform':platform.platform()},
        'truth_boundary':{
            'canonical_project':'unchanged normalized project, digest-bound before and after realization',
            'adaptive_expression':'bounded render work only; every reduction is explicit in the realization contract and receipt',
            'frame_state':'exact PPM bytes for this selected realization; different valid tiers are not claimed pixel-identical',
            'audio':'canonical audio event state and exact native PCM/WAV remain unchanged by v0.9 realization',
            'container_video':'external FFmpeg encoding boundary; export profile may adapt when compatibility assembly is requested',
        },
    }
    rec['receipt_digest']=_stable_receipt_digest(rec);(out/'render-receipt.json').write_bytes(canonical_json(rec)+b'\n');return rec


def verify_repeat(project:dict[str,Any],base_dir:Path,machine_root:Path)->dict[str,Any]:
    a=render_with_receipt(project,Path(base_dir)/'repeat-a',machine_root,assemble=False);b=render_with_receipt(project,Path(base_dir)/'repeat-b',machine_root,assemble=False)
    am=json.loads((Path(base_dir)/'repeat-a'/'frame-manifest.json').read_text());bm=json.loads((Path(base_dir)/'repeat-b'/'frame-manifest.json').read_text());ame=json.loads((Path(base_dir)/'repeat-a'/'media-manifest.json').read_text());bme=json.loads((Path(base_dir)/'repeat-b'/'media-manifest.json').read_text())
    checks={'project_digest_equal':a['project_digest']==b['project_digest'],'media_manifest_equal':ame==bme,'frame_manifest_equal':am==bm,'audio_pcm_equal':a['audio_manifest']['pcm_digest']==b['audio_manifest']['pcm_digest'],'audio_wav_equal':a['audio_manifest']['wav_digest']==b['audio_manifest']['wav_digest']}
    result={'schema':'axm.framestate.repeat-verification/v0.4','passed':all(checks.values()),'checks':checks,'project_digest':a['project_digest'],'media_manifest_digest':ame['manifest_digest'],'frame_manifest_digest':am['manifest_digest'],'audio_pcm_digest':a['audio_manifest']['pcm_digest'],'claim':'repeat proof covers normalized project, conformed media in this runtime, frame state/PPM and mixed PCM/WAV; external codec/font/explicit-speech implementations are versioned boundaries; native speech is covered by PCM equality'};result['verification_digest']=digest(result);return result


def verify_realized_repeat(project:dict[str,Any],base_dir:Path,machine_root:Path,machine:dict[str,Any],policy:dict[str,Any]|None=None)->dict[str,Any]:
    a=render_realized_with_receipt(project,Path(base_dir)/'repeat-a',machine_root,machine,policy,assemble=False)
    b=render_realized_with_receipt(project,Path(base_dir)/'repeat-b',machine_root,machine,policy,assemble=False)
    am=json.loads((Path(base_dir)/'repeat-a'/'frame-manifest.json').read_text());bm=json.loads((Path(base_dir)/'repeat-b'/'frame-manifest.json').read_text())
    checks={
        'canonical_project_equal':a['project_digest']==b['project_digest'],
        'contract_equal':a['realization']['contract_digest']==b['realization']['contract_digest'],
        'frame_manifest_equal':am==bm,
        'audio_pcm_equal':a['audio_manifest']['pcm_digest']==b['audio_manifest']['pcm_digest'],
        'invariants_pass':a['realization']['invariants_after']['passed'] and b['realization']['invariants_after']['passed'],
    }
    result={
        'schema':'axm.framestate.realized-repeat-verification/v0.1',
        'passed':all(checks.values()),
        'checks':checks,
        'project_digest':a['project_digest'],
        'contract_digest':a['realization']['contract_digest'],
        'frame_manifest_digest':am['manifest_digest'],
        'audio_pcm_digest':a['audio_manifest']['pcm_digest'],
        'claim':'same canonical project + same machine capability state + same user policy deterministically reproduces the same realization contract, native frames and PCM in this runtime',
    }
    result['verification_digest']=digest(result);return result
