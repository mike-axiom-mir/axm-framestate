# AXM FrameState

**A standalone, inspectable video creation machine built around canonical state through time.**

FrameState treats a movie as structured state that can be sampled, rendered, inspected, replayed and extended. Other AXM repositories are donor knowledge only; FrameState has no runtime dependency on them.

## Permanent roots

Only four rules sit above the machine:

1. Truth
2. Agency
3. Continuity
4. Wisdom Before Speed

Everything else is working architecture and may be replaced when better evidence appears.

## What the current machine can make

The v0.2 body is intentionally genre-open rather than tied to one editor workflow. One project may combine:

- deterministic procedural rectangles and circles;
- multi-keyframe transforms and animated camera state;
- imported still images;
- imported video clips with trim, speed and loop selection;
- text cards and title graphics;
- burned-in captions plus exact WebVTT subtitle export;
- layer fades and normal/add/multiply/screen compositing;
- reusable verified effect organs, including bounded pixel programs;
- procedural tone audio;
- imported audio mixed into the same timeline;
- optional narration through an explicit eSpeak boundary;
- fixed-point primitive 3D;
- imported OBJ mesh geometry with animated 3D transforms and deterministic face lighting;
- shot markers, derived shots and deterministic storyboards;
- shot-plan compilation from independent relative scene/shot descriptions;
- render queues for multiple projects;
- playable MP4 assembly through an explicit FFmpeg boundary.

This covers practical construction of motion graphics, explainers, captioned videos, edited footage, trailers, montages, tutorials, slideshows, visualizers, title sequences, memes, simple 3D cinematics and hybrids of those forms.

## Quick proofs

```bash
python examples/make_demo_media.py
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m axm_framestate verify-repeat examples/first_light.json renders/verify
PYTHONPATH=src python -m axm_framestate verify-repeat examples/mixed_media.json renders/verify-mixed
PYTHONPATH=src python -m axm_framestate render examples/mixed_media.json renders/mixed-media
PYTHONPATH=src python -m axm_framestate render examples/mesh_cinematic.json renders/mesh
PYTHONPATH=src python -m axm_framestate render examples/narrated_motion.json renders/narrated
```

## Directing by shots

```bash
PYTHONPATH=src python -m axm_framestate compile-plan \
  examples/three_shot.plan.json renders/three-shot/project.json

PYTHONPATH=src python -m axm_framestate render \
  renders/three-shot/project.json renders/three-shot/render

PYTHONPATH=src python -m axm_framestate storyboard \
  renders/three-shot/project.json renders/three-shot/storyboard
```

The compiler shifts shot-local camera/layer/audio/caption timing into one canonical project. The storyboard is generated from representative frames of the actual render, not from unrelated illustrations.

## Batch rendering

```bash
PYTHONPATH=src python -m axm_framestate render-queue examples/render_queue.json
```

Each queue job points to a project and output directory. The queue emits its own receipt digest.

## Grow one new effect organ

```bash
PYTHONPATH=src python -m axm_framestate spawn-effect examples/posterize.effect.json candidates
PYTHONPATH=src python -m axm_framestate adopt-effect candidates/axm.effect.posterize-1.0.0 \
  --reason "Add verified reusable posterization" \
  --root-fit examples/root_fit.json
```

A candidate remains detached until replay tests pass. Supported live adoption requires an inspectable positive fit to all four roots and establishes the daily recovery snapshot first.

## Capability and gap inspection

```bash
PYTHONPATH=src python -m axm_framestate capabilities
PYTHONPATH=src python -m axm_framestate gaps examples/genre_open_requirements.json
PYTHONPATH=src python -m axm_framestate review examples/mixed_media.json
```

The broad `genre_open_requirements.json` probe currently returns READY. That means the named cross-genre construction capabilities in that probe are real. It does **not** mean every imaginable filmmaking technique has been implemented.

## Truth boundaries

FrameState separates evidence planes deliberately:

- canonical project state is normalized and digest-bound;
- generated PPM frame bytes and per-frame state are exact and receipted;
- imported image/video sources are digest-bound, while FFmpeg decoding is an explicit external boundary whose version and conformed output are receipted;
- mixed PCM/WAV bytes are exact for the current runtime; imported audio decode and optional speech synthesis remain named external boundaries;
- MP4 encoding is an external codec boundary and is not claimed bit-identical across arbitrary machines;
- basic 3D is real, but UV texture mapping, skeletal rigs and cast shadows remain separate gaps;
- the mechanical reviewer does not pretend to score beauty, story, originality or emotional truth;
- natural-language directing is not required or bundled;
- current self-growth is bounded to tested effect organs, not arbitrary self-rewriting.

See `FOUNDATION.md`, `DONOR_NOTES.md` and `VERIFICATION.md` for the current evidence boundary.
