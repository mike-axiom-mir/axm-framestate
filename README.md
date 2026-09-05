# AXM FrameState

**A standalone deterministic video creation machine that can grow new verified creation organs.**

FrameState starts from one simple premise: a video can be represented as canonical state evolving through time, then rendered into observable frames and sound with receipts that preserve what actually happened.

It is not trying to be another opaque prompt-to-video generator. Neural or external generators may later become explicit boundaries, but known creation capability should remain usable without them.

## What v0.1 actually does

- validates a closed canonical project format;
- samples camera and object animation deterministically;
- renders layered rectangles and circles into exact PPM frame bytes;
- applies reusable effect organs;
- synthesizes deterministic tone-based WAV audio;
- records frame, audio, project and render receipts;
- renders the same project twice and checks exact equality;
- assembles a playable MP4 through FFmpeg when available, explicitly labelled as an external codec boundary;
- spawns detached effect-organ candidates;
- fixture-tests and replay-tests those candidates;
- gates live effect adoption through Truth, Agency, Continuity and Wisdom Before Speed;
- creates a complete daily recovery snapshot before supported live self-change.

## Quick proof

```bash
PYTHONPATH=src python -m axm_framestate verify-repeat examples/first_light.json renders/verify
PYTHONPATH=src python -m axm_framestate render examples/first_light.json renders/first-light
```

If FFmpeg is installed, the second command also creates `renders/first-light/video.mp4`.

## Grow one new effect organ

```bash
PYTHONPATH=src python -m axm_framestate spawn-effect examples/posterize.effect.json candidates
PYTHONPATH=src python -m axm_framestate adopt-effect candidates/axm.effect.posterize-1.0.0 \
  --reason "Add verified reusable posterization" \
  --root-fit examples/root_fit.json
```

Adoption is additive. A daily machine snapshot is created first.

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Truth boundary

v0.1 does **not** claim:

- cinematic quality;
- arbitrary text/image/video generation;
- 3D rendering;
- speech synthesis;
- cross-machine bit-identical MP4 encoding;
- general semantic understanding of film;
- arbitrary self-modification.

Those are capability space, not imaginary completion. The machine should expose exact gaps and grow from real use instead of hiding them.

See `FOUNDATION.md` for the current architecture and permanent roots.

## Inspect capability space and exact gaps

```bash
PYTHONPATH=src python -m axm_framestate capabilities
PYTHONPATH=src python -m axm_framestate gaps examples/movie_requirements.json
PYTHONPATH=src python -m axm_framestate review examples/first_light.json
```

The gap command intentionally fails closed when a requested capability is absent or unknown. The review command is mechanical evidence, not an artistic score.

## Pixel-program effect organs

FrameState effect candidates may also use a bounded integer stack language (`pixel-program`) for RGB transforms. It has no Python `eval`, filesystem access, imports, network access, loops or hidden calls. New programs remain detached until their fixtures replay exactly and the four-root adoption gate passes. See `examples/signal_program.effect.json`.
