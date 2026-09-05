# AXM FrameState

**A standalone, inspectable video creation machine built around canonical state through time.**

FrameState treats video as structured state that can be compiled, sampled, rendered, inspected, replayed and extended. Other AXM work may donate ideas, but FrameState has no runtime dependency on other AXM repositories.

## Permanent roots

Only four rules sit above the machine:

1. **Truth**
2. **Agency**
3. **Continuity**
4. **Wisdom Before Speed**

Everything else is working architecture and may be replaced when better evidence appears.

## v0.6 construction space

One canonical project can combine:

- procedural rectangles, circles and seeded particles;
- scalar/from-to/multi-keyframe animation and animated cameras;
- imported stills and video, including trim, loop, forward/reverse/freeze source selection;
- image masks, chroma key, wipes, rotation, fades and normal/add/multiply/screen compositing;
- native 5x7 deterministic text plus supplied-font Unicode rasterization through a receipted Pillow/FreeType boundary;
- burned captions and exact WebVTT subtitle export;
- procedural tones, imported audio, gain automation, stereo pan and optional eSpeak narration;
- primitive 3D and OBJ mesh import;
- OBJ UV texture sampling, fixed-point XYZ rotation/projection, morph targets and deterministic cast-shadow projection;
- hierarchical 2D bone rigs;
- nested FrameState visual and audio compositions with child lineage;
- shot-plan compilation, shot derivation and storyboards built from real rendered frames;
- render queues, frame analysis and non-mutating cut proposals;
- verified effect organs and bounded pixel-program effects;
- playable MP4 export through an explicit FFmpeg boundary.

That makes the body practically genre-open for motion graphics, explainers, edited footage, trailers, montages, tutorials, social clips, slideshows, title sequences, visualizers, simple animation, simple 3D cinematics and mixtures of those forms. It is not a claim that every studio technique already exists.

## Make a finished video

Generate the demo media once:

```bash
python examples/make_demo_media.py
```

Then compile and render the four-shot proof movie in one command:

```bash
PYTHONPATH=src python -m axm_framestate make \
  examples/movie_day_one.plan.json renders/day-one \
  --profile fast
```

`make` accepts a canonical FrameState project, structured shot-plan, or creative brief.

For the quality path, rehearse before final output:

```bash
PYTHONPATH=src python -m axm_framestate make \
  examples/rehearsal_brief_compact.json renders/rehearsed-film \
  --rehearse --policy examples/rehearsal_policy.json --verify-repeat
```

The rehearsal fabric repeatedly renders/simulates the candidate, inspects bounded mechanical evidence, applies only evidence-improving deltas, replays, compares, and stops when no justified automatic delta remains. See `REHEARSAL.md`.

## Hard verification

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m axm_framestate verify-repeat \
  examples/advanced_mix.json renders/verify-advanced
PYTHONPATH=src python -m axm_framestate gaps \
  examples/advanced_requirements.json
```

Current checkpoint: **21/21 unit tests pass**. The rehearsal capability probe returns READY, and the compact Director rehearsal proof reaches a repeatable final project after evidence-backed audio, caption and text-fit passes.

## Inspect rather than trust

```bash
PYTHONPATH=src python -m axm_framestate capabilities
PYTHONPATH=src python -m axm_framestate review examples/advanced_mix.json
PYTHONPATH=src python -m axm_framestate analyze renders/day-one
PYTHONPATH=src python -m axm_framestate shots renders/day-one/compiled-project.json
PYTHONPATH=src python -m axm_framestate storyboard \
  renders/day-one/compiled-project.json renders/day-one/storyboard
```

The reviewer and analyzer provide bounded evidence. They do not silently edit the project and do not pretend to score beauty, story or emotional truth.

## Grow one verified effect organ

```bash
PYTHONPATH=src python -m axm_framestate spawn-effect \
  examples/posterize.effect.json candidates

PYTHONPATH=src python -m axm_framestate adopt-effect \
  candidates/axm.effect.posterize-1.0.0 \
  --reason "Add verified reusable posterization" \
  --root-fit examples/root_fit.json
```

A candidate remains detached until replay tests pass. Supported live adoption requires visible positive fit to all four roots and establishes the daily recovery snapshot first.

## Truth boundaries

FrameState separates evidence planes deliberately:

- canonical project state is normalized and digest-bound;
- generated PPM frame bytes and per-frame state are exact and receipted;
- imported media bytes are digest-bound; FFmpeg/Pillow/font/speech boundaries remain named and version/evidence receipted;
- internally mixed PCM/WAV is exact for the current runtime;
- MP4 encoding remains an external FFmpeg boundary, with no false universal bit-identical codec claim;
- current self-growth is bounded to tested effect organs, not arbitrary self-rewriting;
- natural-language directing is optional frontier capability, not required for the deterministic body.

See `FOUNDATION.md`, `CHANGELOG.md`, `DONOR_NOTES.md` and `VERIFICATION.md` for the current evidence boundary.

## Director layer (v0.5)

FrameState can now start one floor above a shot plan. A compact creative brief chooses a style, media and ordered beats; the deterministic director materializes those beats into shots, compiles a canonical project, and the existing renderer takes over.

```bash
PYTHONPATH=src python -m axm_framestate make examples/creative_brief.json renders/director-proof
```

Reusable **shot-recipe organs** can also be replay-tested and adopted behind the same four-root + daily-recovery boundary used for live effect growth. They are data-only construction templates, not arbitrary executable code. See `DIRECTOR.md`.

Free-form natural-language directing remains an explicit translator boundary. FrameState does not pretend that a deterministic creative brief compiler is a general language model.
