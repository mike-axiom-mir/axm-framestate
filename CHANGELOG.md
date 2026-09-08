# Changelog

## v0.4 recovery + usable-video checkpoint

The reconnect lost the uncommitted v0.3 source body. Recovery therefore started from the surviving v0.1 source archive plus the safe GitHub v0.2 branch and the v0.3 evidence documents, then rebuilt forward rather than claiming byte-for-byte resurrection.

Current recovered/extended body includes:

- canonical v0.4 project state with v0.1-v0.4 input compatibility;
- structured shot-plan -> canonical film compilation;
- image/video import, masks, chroma, wipes, rotation and blend modes;
- seeded particles;
- captions + WebVTT;
- imported audio, gain automation, stereo pan and optional eSpeak narration;
- OBJ parsing with UVs, fixed-point rotation/projection, texture sampling, morph targets and shadows;
- hierarchical 2D rigs;
- nested FrameState visual/audio hooks with lineage;
- storyboards, render queues and non-mutating frame/cut analysis;
- `make` command that accepts project or shot-plan and emits a finished MP4;
- rebuilt advanced repeat verification.

A real 180-frame / 15-second four-shot MP4 was rendered during this checkpoint.

## v0.3 evidence checkpoint before reconnect

Surviving documentation records that the earlier uncommitted body had reached 22/22 tests with masks/chroma/wipes, particles, UV textures, shadows, rigs, weighted skinning, morph targets, time remap, gain automation, nesting and supplied-font Unicode shaping. That evidence is preserved as provenance, not silently treated as recovered source.

## v0.2 GitHub checkpoint

Expanded the initial procedural renderer into a genre-open video construction body with imported media/audio, text/captions, compositing, narration, shot compilation/storyboards, render queues, primitive 3D and OBJ meshes.

## v0.5 director + recipe checkpoint

FrameState moved one floor above low-level movie assembly:

- native `axm.framestate.creative-brief/v0.1` compiler;
- deterministic style palettes and beat-to-shot construction;
- one-command `make` now accepts creative briefs as well as shot plans/projects;
- detached reusable `axm.framestate.shot-recipe/v0.1` candidates;
- typed recipe parameters and deterministic placeholder materialization;
- fixture replay through the real shot-plan/project validator;
- four-root + daily-recovery adoption path for shot recipes;
- installed recipes become optional director vocabulary without gaining canon, merge, permission, or arbitrary-code authority;
- new capability map entries for creative-brief compilation and shot-recipe organs.

Free-form natural-language directing remains an explicit optional translator boundary rather than being falsely claimed as native deterministic machinery.

## v0.6 rehearsal / iteration checkpoint

FrameState gained a deterministic rehearsal fabric between direction and final output:

- candidate film simulation passes before final MP4 assembly;
- explicit rehearsal policy with bounded auto-eligible delta classes;
- audio mixer now preserves unclamped accumulation truth and receipts measured pre-clip peak + clipped sample count;
- audio-headroom rehearsal uses both declared overlap and measured pre-clip evidence;
- caption reading-load calculation and timing extension without text rewrite;
- fade-budget repair for impossible fade/lifetime combinations;
- actual raster text-fit calculation plus deterministic multiline wrapping without changing words;
- frame motion and shot-boundary delta observations remain evidence, not automatic taste judgments;
- each proposed delta is replayed and accepted only if its target metric improves with no new review blocks or total mechanical-violation increase;
- clean projects may stop without any rewrite;
- `rehearse` command and `make --rehearse` quality path;
- path-independent render receipt digests;
- deterministic rehearsal receipts and optional final repeat verification.

A compact creative brief proof reached final output through three accepted passes: audio headroom, caption readability, and text fit, then stopped with `NO_JUSTIFIED_AUTO_DELTA`.

## v0.7 Prompt / Style Interpretation Fabric

FrameState gained a bounded prompt-to-state interface above the Director and rehearsal floors:

- `axm.framestate.prompt/v0.1` normalizes high-level direction;
- deterministic prompt plans expose recognized tokens, versioned style bundles, native operations, rehearsal hints, ambiguity and unresolved fragments;
- direct prompt edits cover title size, non-speech audio gain, caption hold time and video playback speed;
- versioned native style bundles include `cinematic@1`, `cleaner@1`, `documentary@1`, `warmer@1` and `cooler-color@1`;
- ambiguous semantic words such as `cooler`, `dramatic`, `epic`, `lonely` and `hopeful` are held rather than silently assigned authority;
- prompt-applied candidates feed into the v0.6 rehearsal loop before final output;
- prompt receipts preserve interpretation, applied operations, held terms, rehearsal lineage and final project identity;
- `interpret-prompt`, `prompt-make`, and `explain-prompt-token` expose the layer through the CLI.

The prompt layer does not claim general natural-language understanding or artistic judgment. Prompt effects must become inspectable native state or remain a named interpretation boundary.

## v0.8 Native Deterministic Speech Organ

FrameState gained its own first-generation offline speech synthesizer:

- project schema `v0.5` adds explicit speech-engine state;
- new v0.5 speech defaults to `native` while v0.4-and-earlier speech without an engine migrates as `espeak` to preserve historical intent;
- native text -> lexicon/rule pronunciation -> phoneme/pause timing -> deterministic formant/noise synthesis -> exact 48 kHz s16 PCM;
- oscillator lookup is built from FrameState's integer CORDIC primitive rather than host TTS or floating trigonometric synthesis;
- deterministic spelling fallback keeps unknown words speakable without a downloaded dictionary/model;
- native voice profiles: `native-neutral-1`, `native-low-1`, `native-bright-1`;
- speech receipts expose text, phoneme plan, voice profile, sample count and exact PCM identity with `external_dependencies: []`;
- creative-brief narration now defaults to native speech;
- `speak-native` writes a standalone WAV and receipt;
- `inspect-speech` exposes the pronunciation/phoneme state before synthesis;
- explicit eSpeak remains available as an optional external compatibility/reference path.

The native voice is intentionally robotic first-generation synthesis. Naturalness is a future quality problem, not a dependency hidden inside the standalone claim.

## v0.9 Adaptive Realization Fabric

FrameState gained its first executable separation between canonical project truth and machine-specific expression:

- `axm.framestate.machine-capabilities/v0.1` records bounded execution facts only: logical cores, memory, explicit dependency availability, platform family and executable render backends;
- the host probe deliberately omits usernames, paths, serials, MAC/network identifiers and unimplemented GPU claims;
- `axm.framestate.realization-policy/v0.1` gives the user exact/adaptive/performance-first control plus explicit no-degrade overrides;
- `axm.framestate.render-contract/v0.1` binds canonical project digest + machine capability digest + policy digest to one deterministic realization;
- current executable adaptation covers particle density, deterministic 3D shadow work, optional effect-pass budget and compatibility export profile;
- effect-pass reduction is opt-in because effects may carry important expression;
- unknown memory is treated conservatively rather than promoting a machine to a richer tier;
- frame manifests expose realized particle counts, shadow state, skipped effects and contract lineage;
- render receipts record every expression delta and verify canonical invariants before and after rendering;
- `exact` realization reproduces legacy native pixel digests;
- same project + same machine capability state + same policy repeat-verifies to the same contract, frames and PCM;
- `probe-machine`, `plan-realization` and `render-adaptive` expose the fabric through the CLI.

The v0.9 floor does **not** claim Metal, Vulkan, WebGPU or other native GPU backends. `cpu-software` is the only implemented renderer. Same-state adaptive GPU realization remains future work.

Human listening feedback on the v0.8 native speech proof also established a quality gap: the generated waveform was not intelligible as words to the listener. Native deterministic synthesis remains real, but human-intelligible native speech is now explicitly tracked as unsolved.
