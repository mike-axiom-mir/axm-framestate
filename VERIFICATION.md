# FrameState v0.9 verification

Hard verification for the Adaptive Realization Fabric checkpoint:

- existing machine regression group -> **17/17 PASS**;
- prompt group -> **5/5 PASS**;
- rehearsal group -> **4/4 PASS**;
- native-speech group -> **5/5 PASS**;
- adaptive-realization group -> **9/9 PASS**;
- aggregate checkpoint -> **40/40 PASS across five test groups**.

## Adaptive realization evidence

Input: `examples/adaptive_realization.json`

Low fixture:

- 2 logical cores;
- 2048 MB memory;
- CPU-software fallback backend;
- adaptive tier -> `minimum`;
- reduced particle expression;
- deterministic 3D shadow pass disabled;
- effect passes remain intact under the default policy.

High fixture:

- 12 logical cores;
- 32768 MB memory;
- CPU-software backend;
- adaptive tier -> `high`;
- full particle expression;
- deterministic 3D shadow pass enabled.

Verified properties:

- low and high contracts bind to the **same canonical project digest**;
- low and high rendered frame manifests differ, as expected for different expression levels;
- canonical audio PCM is identical across low/high realization;
- canonical invariants pass before and after both renders;
- every automatic reduction is exposed as a receipt delta;
- effect-pass reduction happens only when the user explicitly enables it;
- user policy can forbid particle/shadow degradation even on a minimum-tier fixture;
- unknown memory does not silently promote a machine;
- exact mode reproduces legacy renderer pixel digests;
- same canonical project + same machine capability state + same policy repeats to the same realization contract, native frames and PCM.

## Capability-probe privacy boundary

The v0.9 host probe reads bounded execution facts only. It does not collect user identity, usernames, home paths, network identifiers, serial/device IDs or claim unimplemented GPU backends.

## Native speech truth correction

The v0.8 deterministic speech path remains mechanically verified, but human listening feedback reported that its proof sample was not intelligible as recognizable words. Therefore `human-intelligible-native-speech` is a named gap. The current speech organ proves owned deterministic speech-state/waveform generation, not usable natural TTS.

## Truth boundary

v0.9 proves deterministic adaptive planning and bounded CPU-software realization, not Metal/Vulkan/WebGPU execution, semantic scene simplification, cross-device pixel identity or adaptive canonical truth. MP4/H.264 remains an FFmpeg compatibility boundary. Different realization tiers may produce different pixels while preserving the same canonical project state.
