from __future__ import annotations

import importlib.util
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest

MACHINE_SCHEMA = 'axm.framestate.machine-capabilities/v0.1'
POLICY_SCHEMAS = {'axm.framestate.realization-policy/v0.1', 'axm.framestate.realization-policy/v0.2'}
POLICY_SCHEMA = 'axm.framestate.realization-policy/v0.2'
CONTRACT_SCHEMA = 'axm.framestate.render-contract/v0.2'
INVARIANT_SCHEMA = 'axm.framestate.realization-invariant-check/v0.1'


class RealizationError(ValueError):
    pass


def _int(value: Any, label: str, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise RealizationError(f'{label} must be integer in [{lo}, {hi}]')
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise RealizationError(f'{label} must be boolean')
    return value


def _memory_mb() -> int:
    try:
        if hasattr(os, 'sysconf'):
            pages = int(os.sysconf('SC_PHYS_PAGES'))
            page_size = int(os.sysconf('SC_PAGE_SIZE'))
            if pages > 0 and page_size > 0:
                return max(256, min(4_194_304, pages * page_size // (1024 * 1024)))
    except (ValueError, OSError, TypeError):
        pass
    return 0


def probe_machine() -> dict[str, Any]:
    raw = {
        'schema': MACHINE_SCHEMA,
        'id': 'host-probe',
        'logical_cores': max(1, int(os.cpu_count() or 1)),
        'memory_mb': _memory_mb(),
        'ffmpeg_available': bool(shutil.which('ffmpeg')),
        'espeak_available': bool(shutil.which('espeak') or shutil.which('espeak-ng')),
        'pillow_available': importlib.util.find_spec('PIL') is not None,
        'render_backends': ['cpu-software'],
        'platform': platform.system().lower() or 'unknown',
    }
    return normalize_machine_capabilities(raw)


def normalize_machine_capabilities(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RealizationError('machine capabilities must be an object')
    allowed = {
        'schema', 'id', 'logical_cores', 'memory_mb', 'ffmpeg_available',
        'espeak_available', 'pillow_available', 'render_backends', 'platform',
    }
    extra = set(raw) - allowed
    if extra:
        raise RealizationError(f'unknown machine capability fields: {sorted(extra)}')
    if raw.get('schema', MACHINE_SCHEMA) != MACHINE_SCHEMA:
        raise RealizationError(f'schema must be {MACHINE_SCHEMA}')
    backends = raw.get('render_backends', ['cpu-software'])
    if not isinstance(backends, list) or not backends or not all(isinstance(v, str) and v for v in backends):
        raise RealizationError('render_backends must be a non-empty text array')
    if 'cpu-software' not in backends:
        raise RealizationError('v0.10 requires cpu-software as an executable fallback backend')
    result = {
        'schema': MACHINE_SCHEMA,
        'id': str(raw.get('id', 'declared-machine'))[:200],
        'logical_cores': _int(raw.get('logical_cores', 1), 'logical_cores', 1, 4096),
        'memory_mb': _int(raw.get('memory_mb', 0), 'memory_mb', 0, 4_194_304),
        'ffmpeg_available': _bool(raw.get('ffmpeg_available', False), 'ffmpeg_available'),
        'espeak_available': _bool(raw.get('espeak_available', False), 'espeak_available'),
        'pillow_available': _bool(raw.get('pillow_available', False), 'pillow_available'),
        'render_backends': sorted(set(backends)),
        'platform': str(raw.get('platform', 'unknown'))[:100],
    }
    result['probe_scope'] = 'bounded execution facts; no person/device identity fingerprint'
    result['capability_digest'] = digest(result)
    return result


def normalize_realization_policy(raw: Any | None) -> dict[str, Any]:
    raw = {} if raw is None else raw
    if not isinstance(raw, dict):
        raise RealizationError('realization policy must be an object')
    allowed = {
        'schema', 'mode', 'allow_particle_reduction', 'min_particle_density_milli',
        'allow_shadow_disable', 'allow_effect_pass_reduction', 'min_effect_passes',
        'preferred_export_profile', 'min_internal_sample_scale', 'max_internal_sample_scale',
        'preferred_texture_filter',
    }
    extra = set(raw) - allowed
    if extra:
        raise RealizationError(f'unknown realization policy fields: {sorted(extra)}')
    schema = raw.get('schema', POLICY_SCHEMA)
    if schema not in POLICY_SCHEMAS:
        raise RealizationError(f'schema must be one of {sorted(POLICY_SCHEMAS)}')
    mode = raw.get('mode', 'adaptive')
    if mode not in {'exact', 'adaptive', 'performance-first'}:
        raise RealizationError('mode must be exact, adaptive, or performance-first')
    profile = raw.get('preferred_export_profile', 'auto')
    if profile not in {'auto', 'fast', 'h264', 'quality'}:
        raise RealizationError('preferred_export_profile unsupported')
    texture_filter = raw.get('preferred_texture_filter', 'auto')
    if texture_filter not in {'auto', 'nearest', 'bilinear'}:
        raise RealizationError('preferred_texture_filter unsupported')
    min_scale = _int(raw.get('min_internal_sample_scale', 1), 'min_internal_sample_scale', 1, 4)
    max_scale = _int(raw.get('max_internal_sample_scale', 4), 'max_internal_sample_scale', 1, 4)
    if min_scale > max_scale:
        raise RealizationError('min_internal_sample_scale must be <= max_internal_sample_scale')
    result = {
        'schema': POLICY_SCHEMA,
        'mode': mode,
        'allow_particle_reduction': _bool(raw.get('allow_particle_reduction', True), 'allow_particle_reduction'),
        'min_particle_density_milli': _int(raw.get('min_particle_density_milli', 250), 'min_particle_density_milli', 1, 1000),
        'allow_shadow_disable': _bool(raw.get('allow_shadow_disable', True), 'allow_shadow_disable'),
        'allow_effect_pass_reduction': _bool(raw.get('allow_effect_pass_reduction', False), 'allow_effect_pass_reduction'),
        'min_effect_passes': _int(raw.get('min_effect_passes', 0), 'min_effect_passes', 0, 1000),
        'preferred_export_profile': profile,
        'min_internal_sample_scale': min_scale,
        'max_internal_sample_scale': max_scale,
        'preferred_texture_filter': texture_filter,
    }
    result['policy_digest'] = digest(result)
    return result


def _tier(machine: dict[str, Any], mode: str) -> str:
    if mode == 'exact':
        return 'exact'
    cores = machine['logical_cores']
    memory = machine['memory_mb']
    if cores >= 8 and memory >= 8192:
        return 'high'
    if cores >= 4 and memory >= 4096:
        return 'balanced'
    return 'minimum'


def _invariant_values(project: dict[str, Any]) -> dict[str, Any]:
    return {
        'project_digest': digest(project),
        'canvas_digest': digest(project['canvas']),
        'duration_frames': project['duration_frames'],
        'fps': project['canvas']['fps'],
        'layer_ids': [layer['id'] for layer in project.get('layers', [])],
        'layer_kinds': [layer['kind'] for layer in project.get('layers', [])],
        'layer_timing_digest': digest([
            {'id': layer['id'], 'start_frame': layer['start_frame'], 'end_frame': layer['end_frame'], 'z': layer['z']}
            for layer in project.get('layers', [])
        ]),
        'caption_digest': digest(project.get('captions', [])),
        'audio_digest': digest(project.get('audio', [])),
        'marker_digest': digest(project.get('markers', [])),
    }


def plan_realization(project: dict[str, Any], machine: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    machine = normalize_machine_capabilities({k: v for k, v in machine.items() if k not in {'capability_digest', 'probe_scope'}})
    policy = normalize_realization_policy({k: v for k, v in (policy or {}).items() if k != 'policy_digest'})
    tier = _tier(machine, policy['mode'])

    particles = {'exact': 1000, 'high': 1000, 'balanced': 650, 'minimum': 300}[tier]
    shadows = tier in {'exact', 'high', 'balanced'}
    effect_limit: int | None = None
    export_profile = {'exact': 'h264', 'high': 'quality', 'balanced': 'h264', 'minimum': 'fast'}[tier]

    # v0.10 fidelity scaling. This is separate from scene/detail density.
    internal_sample_scale = {'exact': 1, 'high': 2, 'balanced': 2, 'minimum': 1}[tier]
    texture_filter = {'exact': 'nearest', 'high': 'bilinear', 'balanced': 'bilinear', 'minimum': 'nearest'}[tier]

    if policy['mode'] == 'performance-first':
        particles = min(particles, 500 if tier != 'minimum' else 200)
        shadows = False
        export_profile = 'fast'
        internal_sample_scale = 1
        texture_filter = 'nearest'

    if not policy['allow_particle_reduction']:
        particles = 1000
    else:
        particles = max(policy['min_particle_density_milli'], particles)
    if not policy['allow_shadow_disable']:
        shadows = True

    effect_count = len(project.get('effects', []))
    if policy['allow_effect_pass_reduction'] and tier in {'minimum', 'balanced'}:
        suggested = 1 if tier == 'minimum' else 2
        effect_limit = max(policy['min_effect_passes'], min(effect_count, suggested))

    if policy['preferred_export_profile'] != 'auto':
        export_profile = policy['preferred_export_profile']

    internal_sample_scale = max(policy['min_internal_sample_scale'], min(policy['max_internal_sample_scale'], internal_sample_scale))
    if policy['preferred_texture_filter'] != 'auto':
        texture_filter = policy['preferred_texture_filter']

    deltas: list[dict[str, Any]] = []
    if particles < 1000:
        deltas.append({'capability': 'particle-density', 'canonical_milli': 1000, 'realized_milli': particles, 'reason': f'{tier} realization tier'})
    if not shadows:
        deltas.append({'capability': '3d-shadows', 'canonical_requested_state_preserved': True, 'realized': 'disabled', 'reason': f'{tier} realization tier'})
    if effect_limit is not None and effect_limit < effect_count:
        deltas.append({'capability': 'effect-pass-budget', 'canonical_count': effect_count, 'realized_count': effect_limit, 'reason': 'explicit user policy permits effect-pass reduction'})

    fidelity = {
        'internal_sample_scale': internal_sample_scale,
        'internal_pixel_samples_per_output_pixel': internal_sample_scale * internal_sample_scale,
        'texture_filter': texture_filter,
        'reference_cpu_quality': {'internal_sample_scale': 2, 'texture_filter': 'bilinear'},
    }
    fidelity_limited = internal_sample_scale < 2 or texture_filter != 'bilinear'

    invariant_values = _invariant_values(project)
    contract = {
        'schema': CONTRACT_SCHEMA,
        'canonical_project_digest': invariant_values['project_digest'],
        'machine_capability_digest': machine['capability_digest'],
        'policy_digest': policy['policy_digest'],
        'tier': tier,
        'backend': 'cpu-software',
        'render': {
            'particle_density_milli': particles,
            'shadows_enabled': shadows,
            'effect_pass_limit': effect_limit,
            'export_profile': export_profile,
            'internal_sample_scale': internal_sample_scale,
            'texture_filter': texture_filter,
        },
        'fidelity': fidelity,
        'fidelity_limited': fidelity_limited,
        'expression_deltas': deltas,
        'degraded_expression': bool(deltas),
        'non_degradable_invariants': [
            'canonical project digest', 'canvas/duration/fps', 'layer identity/kind/timing',
            'caption content/timing', 'audio event state/timing', 'markers/shot timing',
        ],
        'invariant_values': invariant_values,
        'truth_boundary': (
            'v0.10 separates scene/detail scaling from render fidelity. FrameState may vary particle density, shadow work, '
            'optional effect-pass budget, compatibility export profile, deterministic internal supersampling, and texture sampling. '
            'Supersampling is a transient realization and never rewrites canonical canvas or project state. Effects remain evaluated at '
            'canonical output resolution after downsampling so their coordinate semantics are not silently rescaled.'
        ),
    }
    contract['contract_digest'] = digest(contract)
    return contract


def verify_contract(project: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    expected = contract.get('invariant_values', {})
    actual = _invariant_values(project)
    checks = {key: actual.get(key) == expected.get(key) for key in actual}
    return {
        'schema': INVARIANT_SCHEMA,
        'passed': all(checks.values()),
        'checks': checks,
        'canonical_project_digest': actual['project_digest'],
        'contract_digest': contract.get('contract_digest'),
    }


def write_realization_inputs(output_dir: Path, machine: dict[str, Any], policy: dict[str, Any], contract: dict[str, Any]) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'machine-capabilities.json').write_bytes(canonical_json(machine) + b'\n')
    (out / 'realization-policy.json').write_bytes(canonical_json(policy) + b'\n')
    (out / 'realization-contract.json').write_bytes(canonical_json(contract) + b'\n')
