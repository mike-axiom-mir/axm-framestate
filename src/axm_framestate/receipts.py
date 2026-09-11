from __future__ import annotations
import copy, hashlib, json, os, platform, re, shutil, stat, subprocess
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


_DIGEST_RE = re.compile(r'^sha256:[0-9a-f]{64}$')
_METADATA_LIMIT = 64 * 1024 * 1024
_RECEIPT_SCHEMAS = {
    'axm.framestate.render-receipt/v0.8',
    'axm.framestate.render-receipt/v0.10',
}


class RenderVerificationError(ValueError):
    """A caller-pinned render output cannot be admitted as intact evidence."""


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise RenderVerificationError(f'{label} must be a sha256 digest')
    return value


def _stable_regular_file(path: Path) -> tuple[int, int, int, int, int]:
    try:
        before = path.lstat()
    except OSError as exc:
        raise RenderVerificationError(f'missing evidence file: {path.name}') from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise RenderVerificationError(f'evidence path must be a regular non-symlink file: {path.name}')
    return (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)


def _confirm_stable_file(path: Path, before: tuple[int, int, int, int, int], opened: os.stat_result) -> None:
    try:
        after = path.lstat()
    except OSError as exc:
        raise RenderVerificationError(f'evidence file changed while verifying: {path.name}') from exc
    opened_id = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    if stat.S_ISLNK(after.st_mode) or not stat.S_ISREG(after.st_mode) or before != opened_id or before != after_id:
        raise RenderVerificationError(f'evidence file changed while verifying: {path.name}')


def _read_stable(path: Path, *, limit: int = _METADATA_LIMIT) -> bytes:
    before = _stable_regular_file(path)
    if before[2] > limit:
        raise RenderVerificationError(f'evidence metadata exceeds {limit} bytes: {path.name}')
    try:
        with path.open('rb') as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(limit + 1)
            closed = os.fstat(handle.fileno())
    except OSError as exc:
        raise RenderVerificationError(f'cannot read evidence file: {path.name}') from exc
    if len(raw) > limit:
        raise RenderVerificationError(f'evidence metadata exceeds {limit} bytes: {path.name}')
    _confirm_stable_file(path, before, opened)
    if (closed.st_dev, closed.st_ino, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns) != before:
        raise RenderVerificationError(f'evidence file changed while verifying: {path.name}')
    return raw


def _hash_stable(path: Path) -> str:
    before = _stable_regular_file(path)
    hashed = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            opened = os.fstat(handle.fileno())
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                hashed.update(chunk)
            closed = os.fstat(handle.fileno())
    except OSError as exc:
        raise RenderVerificationError(f'cannot read evidence file: {path.name}') from exc
    _confirm_stable_file(path, before, opened)
    if (closed.st_dev, closed.st_ino, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns) != before:
        raise RenderVerificationError(f'evidence file changed while verifying: {path.name}')
    return 'sha256:' + hashed.hexdigest()


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RenderVerificationError(f'duplicate JSON key: {key}')
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise RenderVerificationError(f'non-finite JSON number: {value}')


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = _read_stable(path)
    try:
        text = raw.decode('utf-8', errors='strict')
        value = json.loads(text, object_pairs_hook=_json_object, parse_constant=_reject_constant)
    except RenderVerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RenderVerificationError(f'invalid JSON evidence: {path.name}') from exc
    if not isinstance(value, dict):
        raise RenderVerificationError(f'evidence document must be an object: {path.name}')
    try:
        encoded = canonical_json(value) + b'\n'
    except (TypeError, ValueError, RecursionError) as exc:
        raise RenderVerificationError(f'non-canonical JSON evidence: {path.name}') from exc
    if raw != encoded:
        raise RenderVerificationError(f'evidence document is not canonical JSON: {path.name}')
    return value


def _verify_embedded_digest(value: dict[str, Any], field: str, label: str) -> str:
    actual = _require_digest(value.get(field), f'{label} {field}')
    core = copy.deepcopy(value)
    core.pop(field, None)
    if digest(core) != actual:
        raise RenderVerificationError(f'{label} digest does not match its content')
    return actual


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RenderVerificationError(f'{label} mismatch')


def verify_render_output(
    output_dir: Path,
    *,
    expected_receipt_digest: str,
    expected_project_digest: str,
) -> dict[str, Any]:
    """Verify a completed render without rerendering or acquiring project authority."""
    receipt_pin = _require_digest(expected_receipt_digest, 'caller receipt pin')
    project_pin = _require_digest(expected_project_digest, 'caller project pin')
    output = Path(output_dir)
    try:
        root_stat = output.lstat()
    except OSError as exc:
        raise RenderVerificationError('render output directory is missing') from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise RenderVerificationError('render output must be a non-symlink directory')

    receipt = _read_canonical_json(output / 'render-receipt.json')
    if receipt.get('schema') not in _RECEIPT_SCHEMAS:
        raise RenderVerificationError('render receipt schema is unsupported')
    recorded_receipt_digest = _require_digest(receipt.get('receipt_digest'), 'render receipt digest')
    receipt_core = copy.deepcopy(receipt)
    receipt_core.pop('receipt_digest', None)
    if _stable_receipt_digest(receipt_core) != recorded_receipt_digest:
        raise RenderVerificationError('render receipt digest does not match its content')
    _require_equal(recorded_receipt_digest, receipt_pin, 'caller receipt pin')
    _require_equal(receipt.get('project_digest'), project_pin, 'caller project pin')

    media = _read_canonical_json(output / 'media-manifest.json')
    if media.get('schema') != 'axm.framestate.media-manifest/v0.4':
        raise RenderVerificationError('media manifest schema is unsupported')
    media_digest = _verify_embedded_digest(media, 'manifest_digest', 'media manifest')
    _require_equal(receipt.get('media_manifest_digest'), media_digest, 'receipt media manifest binding')

    frame_manifest = _read_canonical_json(output / 'frame-manifest.json')
    expected_frame_schema = (
        'axm.framestate.frame-manifest/v0.6'
        if receipt.get('schema') == 'axm.framestate.render-receipt/v0.10'
        else 'axm.framestate.frame-manifest/v0.4'
    )
    if frame_manifest.get('schema') != expected_frame_schema:
        raise RenderVerificationError('frame manifest schema is unsupported for this receipt')
    frame_manifest_digest = _verify_embedded_digest(frame_manifest, 'manifest_digest', 'frame manifest')
    _require_equal(receipt.get('frame_manifest_digest'), frame_manifest_digest, 'receipt frame manifest binding')
    _require_equal(frame_manifest.get('project_digest'), project_pin, 'frame manifest project binding')
    _require_equal(frame_manifest.get('media_manifest_digest'), media_digest, 'frame manifest media binding')

    states = frame_manifest.get('states')
    files = frame_manifest.get('files')
    frame_count = frame_manifest.get('frame_count')
    if isinstance(frame_count, bool) or not isinstance(frame_count, int) or frame_count < 0:
        raise RenderVerificationError('frame count is invalid')
    if not isinstance(states, list) or not isinstance(files, list) or len(states) != frame_count or len(files) != frame_count:
        raise RenderVerificationError('frame manifest count does not match states and files')
    expected_names: list[str] = []
    for index, state_value in enumerate(states):
        if not isinstance(state_value, dict) or state_value.get('frame') != index:
            raise RenderVerificationError(f'frame state sequence mismatch at {index}')
        _verify_embedded_digest(state_value, 'state_digest', f'frame state {index}')
    for index, file_value in enumerate(files):
        expected_name = f'frame-{index:06d}.ppm'
        if not isinstance(file_value, dict) or set(file_value) != {'path', 'digest'} or file_value.get('path') != expected_name:
            raise RenderVerificationError(f'frame file sequence mismatch at {index}')
        expected_digest = _require_digest(file_value.get('digest'), f'frame {index} digest')
        if _hash_stable(output / 'frames' / expected_name) != expected_digest:
            raise RenderVerificationError(f'frame digest mismatch at {index}')
        expected_names.append(expected_name)
    frames_dir = output / 'frames'
    try:
        frame_names = sorted(item.name for item in frames_dir.iterdir())
    except OSError as exc:
        raise RenderVerificationError('frame inventory cannot be read') from exc
    if frame_names != expected_names:
        raise RenderVerificationError('frame inventory does not match manifest')

    audio = receipt.get('audio_manifest')
    if not isinstance(audio, dict):
        raise RenderVerificationError('audio manifest is missing from receipt')
    if audio.get('schema') != 'axm.framestate.audio-manifest/v0.8':
        raise RenderVerificationError('audio manifest schema is unsupported')
    audio_manifest_digest = _verify_embedded_digest(audio, 'manifest_digest', 'audio manifest')
    audio_digest = _require_digest(audio.get('wav_digest'), 'audio digest')
    if _hash_stable(output / 'audio.wav') != audio_digest:
        raise RenderVerificationError('audio digest mismatch')

    subtitle = receipt.get('subtitle_export')
    if not isinstance(subtitle, dict):
        raise RenderVerificationError('subtitle export is missing from receipt')
    if subtitle.get('schema') != 'axm.framestate.subtitle-export/v0.1':
        raise RenderVerificationError('subtitle export schema is unsupported')
    caption_digest = _require_digest(subtitle.get('digest'), 'caption digest')
    if _hash_stable(output / 'captions.vtt') != caption_digest:
        raise RenderVerificationError('caption digest mismatch')

    video = receipt.get('video')
    video_digest: str | None = None
    video_path = output / 'video.mp4'
    if video is None:
        if video_path.exists() or video_path.is_symlink():
            raise RenderVerificationError('unreceipted video is present')
    elif isinstance(video, dict):
        video_digest = _require_digest(video.get('digest'), 'video digest')
        if _hash_stable(video_path) != video_digest:
            raise RenderVerificationError('video digest mismatch')
        assembly = receipt.get('assembly')
        if not isinstance(assembly, dict) or assembly.get('succeeded') is not True:
            raise RenderVerificationError('video exists without successful assembly evidence')
    else:
        raise RenderVerificationError('video receipt must be an object or null')

    realization_contract_digest: str | None = None
    realization = receipt.get('realization')
    if receipt.get('schema') == 'axm.framestate.render-receipt/v0.10':
        if not isinstance(realization, dict):
            raise RenderVerificationError('realization evidence is missing')
        machine = _read_canonical_json(output / 'machine-capabilities.json')
        policy = _read_canonical_json(output / 'realization-policy.json')
        contract = _read_canonical_json(output / 'realization-contract.json')
        if machine.get('schema') != 'axm.framestate.machine-capabilities/v0.1':
            raise RenderVerificationError('machine capability schema is unsupported')
        if policy.get('schema') != 'axm.framestate.realization-policy/v0.2':
            raise RenderVerificationError('realization policy schema is unsupported')
        if contract.get('schema') != 'axm.framestate.render-contract/v0.2':
            raise RenderVerificationError('realization contract schema is unsupported')
        machine_digest = _verify_embedded_digest(machine, 'capability_digest', 'machine capability')
        policy_digest = _verify_embedded_digest(policy, 'policy_digest', 'realization policy')
        realization_contract_digest = _verify_embedded_digest(contract, 'contract_digest', 'realization contract')
        _require_equal(realization.get('machine_capability_digest'), machine_digest, 'receipt machine capability binding')
        _require_equal(realization.get('policy_digest'), policy_digest, 'receipt realization policy binding')
        _require_equal(realization.get('contract_digest'), realization_contract_digest, 'receipt realization contract binding')
        _require_equal(contract.get('canonical_project_digest'), project_pin, 'realization contract project binding')
        _require_equal(contract.get('machine_capability_digest'), machine_digest, 'contract machine capability binding')
        _require_equal(contract.get('policy_digest'), policy_digest, 'contract policy binding')
        _require_equal(frame_manifest.get('realization_contract_digest'), realization_contract_digest, 'frame manifest realization binding')
        for key in ('tier', 'backend', 'render', 'fidelity', 'fidelity_limited', 'expression_deltas'):
            _require_equal(realization.get(key), contract.get(key), f'receipt realization {key} binding')
    elif realization is not None:
        raise RenderVerificationError('legacy receipt contains unexpected realization evidence')

    result = {
        'schema': 'axm.framestate.render-output-verification/v0.1',
        'verified': True,
        'receipt_digest': recorded_receipt_digest,
        'project_digest': project_pin,
        'media_manifest_digest': media_digest,
        'frame_manifest_digest': frame_manifest_digest,
        'frame_count': frame_count,
        'audio_manifest_digest': audio_manifest_digest,
        'audio_wav_digest': audio_digest,
        'caption_digest': caption_digest,
        'video_digest': video_digest,
        'realization_contract_digest': realization_contract_digest,
        'authority': 'EVIDENCE_ADMISSION_ONLY',
        'truth_boundary': (
            'verifies caller-pinned receipt identity and current local render bytes without rerendering; '
            'does not grant canonical project, merge, publication, or CANON authority'
        ),
    }
    result['verification_digest'] = digest(result)
    return result


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
    am=render_audio(project,out/'audio.wav',machine_root,out);subs=export_vtt(project,out/'captions.vtt')
    assembly,video=_assemble_video(project,out,contract['render']['export_profile'],assemble,machine['ffmpeg_available'])
    invariant_after=verify_contract(project,contract)
    rec={
        'schema':'axm.framestate.render-receipt/v0.10',
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
            'fidelity':contract['fidelity'],
            'fidelity_limited':contract['fidelity_limited'],
            'expression_deltas':contract['expression_deltas'],
            'invariants_before':invariant_before,
            'invariants_after':invariant_after,
        },
        'environment':{'python':platform.python_version(),'platform':platform.platform()},
        'truth_boundary':{
            'canonical_project':'unchanged normalized project, digest-bound before and after realization',
            'adaptive_expression':'bounded detail/render work only; reductions and fidelity choices are explicit in the realization contract and receipt',
            'fidelity':'internal supersampling and texture filtering are transient render choices; canonical canvas dimensions remain unchanged',
            'effects':'effect programs execute at canonical output resolution after downsampling so their coordinate semantics are preserved',
            'frame_state':'exact PPM bytes for this selected realization; different valid tiers are not claimed pixel-identical',
            'audio':'canonical audio event state and exact native PCM/WAV remain unchanged by realization',
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
        'schema':'axm.framestate.realized-repeat-verification/v0.2',
        'passed':all(checks.values()),
        'checks':checks,
        'project_digest':a['project_digest'],
        'contract_digest':a['realization']['contract_digest'],
        'frame_manifest_digest':am['manifest_digest'],
        'audio_pcm_digest':a['audio_manifest']['pcm_digest'],
        'claim':'same canonical project + same machine capability state + same user policy deterministically reproduces the same realization contract, fidelity choice, native frames and PCM in this runtime',
    }
    result['verification_digest']=digest(result);return result
