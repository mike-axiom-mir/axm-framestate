# FrameState v0.10 Adaptive Realization + Fidelity Fabric

FrameState v0.10 establishes an executable distinction:

`canonical project truth != realization contract != rendered output`

One canonical project may have several valid rendered manifestations. The machine may change **expression cost**, but it may not silently change canonical meaning.

## Flow

`canonical project -> machine capability state -> user policy -> deterministic render contract -> CPU-software realization -> receipt`

The contract is digest-bound to all three inputs. Replanning the same project with the same capability state and policy yields the same contract.

## Machine capability state

Schema: `axm.framestate.machine-capabilities/v0.1`

The native host probe currently records only bounded execution facts needed by the planner:

- logical CPU cores;
- physical memory when available;
- FFmpeg/eSpeak/Pillow availability;
- platform family;
- executable FrameState render backends.

v0.10 advertises only `cpu-software`. It does not claim Metal, Vulkan, WebGPU or another GPU path merely because the host may support them.

The probe deliberately excludes usernames, home paths, serial numbers, MAC/network identifiers, stable device IDs and other person/device fingerprinting data. Unknown memory remains `0` and is planned conservatively.

## User realization policy

Schema: `axm.framestate.realization-policy/v0.2` (v0.1 inputs remain accepted and normalize forward)

Modes:

- `exact`: preserve the full current CPU-software realization;
- `adaptive`: choose a bounded tier from measured/declared capability state;
- `performance-first`: prefer the cheapest currently permitted expression.

User policy can forbid particle reduction or shadow disabling and can set a particle floor. Effect-pass reduction is disabled by default and must be explicitly allowed.

## Current executable adaptive capabilities

v0.10 changes only expression/render work already owned by FrameState:

1. seeded particle density;
2. deterministic 3D cast-shadow work;
3. effect-pass budget when explicitly permitted;
4. FFmpeg export profile when compatibility assembly is requested.

It does **not** change canvas truth, duration, fps, layer identity/kind/timing, caption content/timing, audio event state/timing, or markers/shot timing.


## v0.10 fidelity axis

Detail density and render fidelity are deliberately separated. The same canonical scene can now use:

- `internal_sample_scale`: 1x or 2x by default tier (higher values remain user-permitted);
- deterministic box resolve back to the unchanged canonical canvas;
- `nearest` or deterministic integer `bilinear` texture sampling.

The high-tier default uses 2x linear internal sampling, meaning four internal pixel samples per final output pixel. A dedicated circle proof has identical canonical layer state on low/high machines; low has hard binary edges, while high creates deterministic partial-coverage edge pixels. This is a fidelity change without added objects/details.

Effects are applied after the supersampled scene resolves to canonical output resolution. This prevents an effect such as scanlines from silently changing spatial meaning merely because the internal raster was larger.

## Receipts and invariants

Every render contract contains:

- canonical project digest;
- machine capability digest;
- user policy digest;
- selected tier/backend;
- explicit render options;
- explicit expression deltas;
- non-degradable invariant values;
- a contract digest.

The realized render receipt checks those canonical invariants before and after rendering. Frame manifests also expose realized particle counts, shadow state, skipped effect passes and contract lineage.

Different tiers are **not** claimed pixel-identical. They are different projections of the same canonical project. `exact` mode is separately tested to reproduce the legacy renderer's native pixel digests.

## CLI

```bash
PYTHONPATH=src python -m axm_framestate probe-machine

PYTHONPATH=src python -m axm_framestate plan-realization \
  examples/adaptive_realization.json \
  --machine examples/machine_low.json \
  --policy examples/realization_policy.json

PYTHONPATH=src python -m axm_framestate render-adaptive \
  examples/adaptive_realization.json renders/adaptive-low \
  --machine examples/machine_low.json \
  --policy examples/realization_policy.json \
  --no-assemble --verify-repeat
```

## Truth boundary

This checkpoint proves deterministic adaptive planning and bounded CPU-software realization. It does not prove automatic GPU backend selection, semantic LOD generation, cross-device pixel identity, dynamic runtime frame-budget control, or universal performance guarantees.

**Working rule:** degrade expression, never truth; upgrade expression, never invent truth.
