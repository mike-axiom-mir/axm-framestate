# FrameState v0.12 verification

FrameState now has a repository CI floor in addition to its local deterministic receipts.

## GitHub Actions implementation checkpoint

Exact implementation/test head:

`9bcbbe5c23487fbd33bb9eb2beb3f0747b4b2463`

Workflow run:

`Verify FrameState` run **34268145735**

All four jobs passed:

- Python 3.11 complete regression tree: **54/54 PASS**;
- Python 3.12 complete regression tree: **54/54 PASS**;
- Python 3.13 complete regression tree: **54/54 PASS**;
- independent wheel/package job: **PASS**.

The test jobs also pass Studio JavaScript syntax and package-import smoke. The package job builds the exact wheel, installs it without installing Pillow as a runtime dependency, starts the installed `framestate`, `framestate-studio` and `framestate-render-resume` entry points, and verifies that the Studio HTML/CSS/JS resources are actually present in the installed package.

The 54 tests are one test tree executed on three Python versions. They are not misreported as 162 independent test cases.

## CI failures retained as evidence

The first CI attempts were useful counterevidence rather than disposable red runs.

### Hidden Pillow dependency

The first wheel/package smoke failed even though `pyproject.toml` declared `dependencies = []`:

`framestate -> cli -> receipts -> audio -> media -> from PIL import Image`

The dependency-free core claim was therefore false at import time. The fix did not simply install Pillow in the package gate. `media.py` and `text.py` were changed so Pillow/FreeType are loaded only when an imported-image or supplied-font compatibility path actually requires them. Native bitmap text and the core CLI/Studio/resume import path now load without Pillow installed.

Pillow remains an explicit optional compatibility boundary. General imported-image/font features are not falsely called dependency-free.

### Non-canonical adaptive resume fixture

A first resumable regression run failed with `KeyError: opacity_milli` because the new test replaced an already-normalized layer with a raw hand-authored layer and called `render_project` directly without canonical normalization.

The production renderer contract was not weakened. The fixture was corrected to pass through `normalize_project` first, preserving the rule that renderer state is canonical normalized project state.

## Studio verification

The five focused Studio tests verify:

- default Studio project normalizes to canonical project v0.5;
- dependency-free native PPM -> PNG preview conversion;
- Studio preview uses the real native `render_frame` path and returns exact frame state;
- bounded prompt interpretation produces an explicit plan and candidate-state mutation;
- save writes normalized canonical state and round-trips with the same digest.

The package job separately verifies the Studio resources survive wheel construction/installation.

## Crash-resume verification

The five focused resumable-render tests verify:

- interrupted native render -> resume -> final frame manifest equals uninterrupted `render_project` reference output;
- project identity drift refuses an old checkpoint;
- modification of a checkpoint-admitted frame fails closed;
- an unadmitted tail frame left after interruption is deleted and rerendered;
- adaptive resume under one exact realization contract equals uninterrupted output under that same contract.

Checkpoint identity binds canonical project digest, conformed-media manifest digest, realization-contract digest when present, duration/canvas, frame indices, exact frame-file digests and frame state.

A conservative disk gate checks estimated remaining native PPM storage plus a fixed reserve before continuing. This is a filesystem headroom gate, not a universal process-memory/codec-storage prediction.

## Adaptive realization evidence retained from v0.10

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

Verified properties remain:

- low and high contracts bind to the same canonical project digest;
- low and high rendered frame manifests may differ as realization expression differs;
- canonical audio PCM is identical across low/high realization;
- canonical invariants pass before and after both renders;
- automatic reductions remain explicit receipt deltas;
- effect-pass reduction remains opt-in;
- user policy can forbid particle/shadow degradation;
- unknown memory cannot silently promote a machine;
- exact mode reproduces legacy renderer pixel digests;
- same project + machine capability state + policy repeats to the same realization contract, native frames and PCM.

## Capability-probe privacy boundary

The host probe reads bounded execution facts only. It does not collect user identity, usernames, home paths, network identifiers, serial/device IDs or claim unimplemented GPU backends.

## Native speech truth correction

The v0.8 deterministic speech path remains mechanically verified, but human listening feedback reported that its proof sample was not intelligible as recognizable words. `human-intelligible-native-speech` remains a named gap. The current speech organ proves owned deterministic speech-state/waveform generation, not usable natural TTS.

## Fidelity proof retained

Input: `examples/fidelity_probe.json`

- one canonical white circle on black;
- no particles, captions, effects, extra props or scene-detail difference;
- low fixture -> 1x internal sampling / nearest filter;
- high fixture -> 2x internal sampling / bilinear filter;
- low output contains zero intermediate grayscale edge pixels;
- high output contains deterministic intermediate edge pixels from partial pixel coverage;
- visible canonical layer state is identical between the two manifests;
- canonical project digest remains identical.

This verifies actual raster-fidelity scaling rather than merely adding detail.

## Current truth boundary

v0.12 proves a canonical local Studio, package-installable core surface, adaptive CPU-software rendering and crash-resumable **native frame truth**. It does not prove Metal/Vulkan/WebGPU execution, weighted 3D skin deformation, unrestricted semantic language understanding, human-intelligible native speech, arbitrary self-modification, native H.264/AAC, cross-device pixel identity or mid-process FFmpeg encoder resumption.

Standard MP4/H.264 remains an explicit FFmpeg compatibility boundary. Different realization tiers may produce different pixels while preserving the same canonical project state.
