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

## v0.5 construction space

One canonical project can combine procedural graphics, imported still/video media, text/captions/subtitles, masks/chroma/wipes, compositing, seeded particles, stereo audio, speech, primitive/OBJ 3D, UV textures, morph targets, shadows, rigs, nested compositions, effects, shot plans, storyboards and render queues.

The v0.5 Director adds a higher-level path:

`creative brief -> deterministic beats -> shot recipes/shot plan -> canonical movie -> exact render receipts -> MP4`

Reusable **shot-recipe organs** are replay-tested data-only construction templates. Supported live adoption requires detached evidence, positive fit to Truth/Agency/Continuity/Wisdom Before Speed, and a daily recovery snapshot first.

## Make a finished video

```bash
python examples/make_demo_media.py
PYTHONPATH=src python -m axm_framestate make examples/creative_brief.json renders/director-proof
```

`make` accepts a canonical FrameState project, a structured shot-plan, or a v0.5 creative brief.

## Verify

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m axm_framestate verify-repeat examples/advanced_mix.json renders/verify-advanced
PYTHONPATH=src python -m axm_framestate gaps examples/advanced_requirements.json
```

Current checkpoint: **17/17 unit tests pass**. Creative-brief compilation, replay-tested shot-recipe adoption, installed-recipe reuse and compact creative-brief repeat verification all pass.

## Grow a shot recipe

```bash
PYTHONPATH=src python -m axm_framestate spawn-recipe examples/lower_third.recipe.json candidates
PYTHONPATH=src python -m axm_framestate adopt-recipe \
  candidates/axm.recipe.lower-third-1.0.0 \
  --reason "Reuse a verified lower-third construction" \
  --root-fit examples/root_fit.json
```

Adoption gives reuse, not canon, merge, permission or arbitrary-code authority.

## Truth boundaries

FrameState separates evidence planes deliberately. Canonical project state, generated frame bytes and internally mixed audio are receipted. FFmpeg, eSpeak and supplied-font rasterization remain explicit external boundaries. Creative briefs are structured deterministic direction, not a claim of free-form natural-language understanding or artistic intelligence. Natural-language translation may be supplied by a human or explicitly named AI/model boundary.

See `FOUNDATION.md`, `DIRECTOR.md`, `CHANGELOG.md`, `DONOR_NOTES.md` and `VERIFICATION.md` for the current evidence boundary.
