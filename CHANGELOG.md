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

## v0.10 Render Fidelity Scaling

FrameState separated detail density from actual render fidelity:

- stronger CPU-software tiers can use deterministic internal supersampling;
- current high default is 2x linear sampling (4 internal samples per output pixel);
- supersampled output resolves back to the unchanged canonical canvas with deterministic box filtering;
- deterministic bilinear sampling is available for richer image/mesh texture realization;
- effects execute at canonical output resolution after resolve, preserving their coordinate semantics;
- fidelity choices are receipted separately from particle/shadow/effect detail reductions;
- user policy can cap internal sample scale or force texture filtering independently of machine tier;
- exact mode remains legacy-pixel compatible;
- a same-circle proof verifies partial-coverage edge pixels on high tier with no extra objects/details;
- adaptive/fidelity tests expanded to 13, bringing the exact-source checkpoint to 44/44 local tests.

Truth correction: more particles/details are not described as higher visual quality. They are detail density. Fidelity requires evidence from the same canonical scene.

## v0.11 Canonical Studio

FrameState gained its first human-facing visual creation surface without introducing a second project truth model:

- local `framestate-studio` entry point using a loopback-only Python standard-library server;
- dependency-free shipped HTML/CSS/JavaScript UI;
- canonical project/canvas/timing/background editing;
- common 2D/3D layer, caption, tone and native-speech editing;
- exact/adaptive timeline preview through the real native `render_frame` path;
- bounded prompt-plan -> explicit candidate-state mutation inside the Studio;
- mechanical review and evidence panel;
- raw canonical JSON remains visible as the universal interface for state without a dedicated control;
- normalized canonical project save uses fsync + atomic replace;
- final render returns the native/compatibility receipt rather than silently rewriting project state;
- loopback/CSP/origin/sanitized-output boundaries keep the local surface narrow.

The Studio intentionally uses the system browser as its display shell. It is not a hardened hostile multi-user web service and does not claim native desktop packaging yet.

## v0.12 Crash-resumable rendering + real package/CI truth

FrameState added interruption-safe native frame rendering and used its first repository CI floor to correct a hidden standalone defect.

Resumable rendering:

- `framestate-render-resume` entry point;
- `axm.framestate.render-checkpoint/v0.1` binds project, conformed-media and realization identity;
- every admitted frame stores exact frame-state + frame-file digest;
- admitted frame bytes are rehashed before reuse;
- stale project/media/realization checkpoints fail closed;
- corrupt admitted frames fail closed;
- unadmitted tail files left after interruption are deleted and rerendered rather than promoted by existence;
- conservative remaining-native-frame disk estimate + fixed reserve can HOLD before continuing;
- resumed final native manifests are regression-tested for equality with uninterrupted `render_project` output;
- Studio final rendering uses a stable project-digest output identity so retry naturally reaches the same checkpoint;
- audio/subtitles and optional FFmpeg assembly occur after native frames are complete; libx264/AAC process internals are not falsely called resumable.

CI/package correction:

- added GitHub Actions complete test matrix for Python 3.11, 3.12 and 3.13;
- added JavaScript syntax and package-import smoke gates;
- added wheel build/install and installed-entry-point/resource verification;
- the first wheel test exposed that `media.py` imported Pillow at module import time even though `dependencies=[]` claimed a dependency-free core;
- that apparent standalone boundary was rejected and repaired by making Pillow/FreeType a lazy optional image/font compatibility boundary;
- native bitmap text and core Studio/CLI import paths now load without Pillow installed;
- another first-run failure exposed one raw test fixture bypassing canonical normalization; the fixture was corrected rather than weakening the renderer contract;
- exact-head GitHub Actions run `34268145735` then passed all four jobs: the complete 54-test tree on Python 3.11/3.12/3.13 plus the independent wheel/package gate.

v0.12 still does not claim a GPU backend, weighted 3D skin deformation, unrestricted semantic language understanding, human-intelligible native speech, arbitrary self-modification, native H.264, or a fully bundled cross-platform desktop release.
