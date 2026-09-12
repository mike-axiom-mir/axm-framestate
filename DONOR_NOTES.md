# Donor knowledge, not runtime dependency

FrameState is fresh standalone source. No other AXM repository is imported, cloned or required at runtime.

Useful donor patterns inspected while designing the body included:

- Universal Creation: inspectable atom/component/organ/capability layering, transparency boundaries, detached tested units, daily recovery and bounded self-evolution;
- AXM creation vocabulary: frame/timecode/keyframe/timeline/video/audio/shot/cinematic-scene/caption/subtitle/media/render-queue/camera-animation vocabulary and organ-level compositor/conformer/director ideas;
- temporal creation work: reference -> grammar -> build -> render -> inspect -> gap -> generalize -> replay;
- broader AXM state work: canonical state as truth surface and checks/specialists as views rather than independent authority.

## Renderer-neutral visual-state bridge

The bounded visual-state realization bridge in `src/axm_framestate/visual_state_bridge.py` was designed against the renderer-neutral `axm.visual-state-compilation/v0.1` contract implemented on `axm-universal-creation` PR #23, inspected at donor commit `f765452b4189822b70ff03db014b2beecd55e43a`.

FrameState does **not** copy or import the donor compiler. At runtime it accepts only the resulting JSON data contract. CI checks out that exact donor commit solely as an interoperability fixture, asks Universal Creation to compile a real `/8k /ultrarealistic /cinematic` request, then proves that FrameState can consume the resulting artifact while remaining standalone.

The bridge intentionally maps only two bounded directions into already-existing FrameState realization controls:

- `appearance.render_fidelity` may request the existing reference CPU fidelity path (internal supersampling plus bilinear texture filtering);
- `projection.detail_level` may raise the existing particle-density floor as one explicitly partial detail channel.

Everything else remains visible as `HELD` unless FrameState has an equally explicit native meaning. In particular, `projection.resolution_tier` does not silently rewrite the canonical project canvas. Explicit FrameState user policy outranks donor direction. A compiled visual-state artifact remains direction evidence, not project truth, renderer proof, quality proof, merge authority or CANON.

These are donor ideas and evidence, not canon. The only permanent authority layer is Truth, Agency, Continuity and Wisdom Before Speed.
