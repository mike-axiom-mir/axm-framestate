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
