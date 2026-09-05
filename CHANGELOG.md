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
