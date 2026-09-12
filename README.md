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

## v0.12 construction space

One canonical project can combine:

- procedural rectangles, circles and seeded particles;
- scalar/from-to/multi-keyframe animation and animated cameras;
- imported stills and video, including trim, loop, forward/reverse/freeze source selection;
- image masks, chroma key, wipes, rotation, fades and normal/add/multiply/screen compositing;
- native 5x7 deterministic text plus supplied-font Unicode rasterization through a receipted optional Pillow/FreeType boundary;
- burned captions and exact WebVTT subtitle export;
- procedural tones, imported audio, gain automation, stereo pan, native deterministic narration and optional explicit eSpeak narration;
- primitive 3D and OBJ mesh import;
- OBJ UV texture sampling, fixed-point XYZ rotation/projection, morph targets and deterministic cast-shadow projection;
- hierarchical 2D bone rigs;
- nested FrameState visual and audio compositions with child lineage;
- shot-plan compilation, shot derivation and storyboards built from real rendered frames;
- render queues, frame analysis and non-mutating cut proposals;
- verified effect organs and bounded pixel-program effects;
- playable MP4 export through an explicit FFmpeg boundary;
- a local visual Studio over the canonical project state;
- crash-resumable native frame rendering with checkpoint identity and corruption/drift refusal.

That makes the body practically genre-open for motion graphics, explainers, edited footage, trailers, montages, tutorials, social clips, slideshows, title sequences, visualizers, simple animation, simple 3D cinematics and mixtures of those forms. It is not a claim that every studio technique already exists.

## Open the visual Studio

After installing the package:

```bash
framestate-studio my-film.json
```

Or from a source checkout:

```bash
PYTHONPATH=src python -m axm_framestate.studio examples/adaptive_realization.json
```

Studio binds to loopback only and edits the same canonical project state used by the CLI. It can add/edit common layers, captions and audio events, scrub the timeline, preview through the **actual FrameState renderer**, use exact/adaptive realization, apply bounded prompts as explicit state operations, run mechanical review, save atomically and start final renders. Full canonical JSON remains visible as the fallback interface for state that does not yet have a dedicated visual control. See `STUDIO.md`.

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

## Resume an interrupted native render

```bash
framestate-render-resume project.json renders/final --checkpoint-interval 12
```

Adaptive:

```bash
framestate-render-resume project.json renders/final --adaptive --checkpoint-interval 12
```

The checkpoint binds canonical project, conformed media and adaptive realization identity plus the exact admitted frame bytes/state. A changed project, changed media/contract or corrupted checkpointed frame fails closed. Frame files beyond the last admitted checkpoint are discarded and rerendered. Completed resumed native manifests are regression-tested against uninterrupted render output. FFmpeg codec internals are still an external compatibility boundary rather than falsely called resumable. See `RESUME.md`.

## Hard verification

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m axm_framestate verify-repeat \
  examples/advanced_mix.json renders/verify-advanced
PYTHONPATH=src python -m axm_framestate gaps \
  examples/advanced_requirements.json
```

Current v0.12 checkpoint: the **54-test complete tree passes on Python 3.11, 3.12 and 3.13 in GitHub Actions**. The same workflow validates Studio JavaScript/imports and separately builds/installs the exact wheel, starts the packaged CLI/Studio/resume entry points, and verifies the shipped Studio resources. The package gate runs without installing Pillow and therefore verifies that Pillow is no longer a hidden core import dependency.

The v0.8 native speech path remains mechanically deterministic and exact, but human listening feedback established that its proof sample was not intelligible as recognizable words. Human-intelligible native speech therefore remains explicitly unsolved rather than being called usable TTS.

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
- imported media bytes are digest-bound; FFmpeg/Pillow/font and optional external-speech boundaries remain named and version/evidence receipted;
- Pillow is lazy/optional and is not required merely to install/import the core or use native bitmap text/Studio preview paths;
- internally mixed PCM/WAV is exact for the current runtime;
- native frame rendering can resume only from admitted/checkpoint-verified bytes;
- MP4 encoding remains an external FFmpeg boundary, with no false universal bit-identical codec or mid-encoder-resume claim;
- current self-growth is bounded to tested effect organs and data-only shot recipes, not arbitrary self-rewriting;
- bounded direct/style prompt language is native and versioned; unrestricted semantic natural-language directing remains an explicit translator/interpretation boundary rather than hidden machine authority;
- v0.12 still has only the CPU-software render backend and does not claim Metal/Vulkan/WebGPU execution;
- recovered source still does not contain tested weighted 3D skinning; the unrecovered v0.3 evidence is provenance only.

See `FOUNDATION.md`, `CHANGELOG.md`, `DONOR_NOTES.md`, `VERIFICATION.md`, `STUDIO.md`, and `RESUME.md` for the current evidence boundary.

## Director layer (v0.5)

FrameState can start one floor above a shot plan. A compact creative brief chooses a style, media and ordered beats; the deterministic director materializes those beats into shots, compiles a canonical project, and the existing renderer takes over.

```bash
PYTHONPATH=src python -m axm_framestate make examples/creative_brief.json renders/director-proof
```

Reusable **shot-recipe organs** can also be replay-tested and adopted behind the same four-root + daily-recovery boundary used for live effect growth. They are data-only construction templates, not arbitrary executable code. See `DIRECTOR.md`.

Free-form natural-language directing remains an explicit translator boundary. FrameState does not pretend that a deterministic creative brief compiler is a general language model.

## v0.7 prompts: high-level direction without hidden authority

FrameState can apply bounded prompt direction to a project before rehearsal:

```bash
PYTHONPATH=src python -m axm_framestate interpret-prompt \
  examples/rehearsal_brief_compact.json examples/prompt_cinematic.json

PYTHONPATH=src python -m axm_framestate prompt-make \
  examples/rehearsal_brief_compact.json examples/prompt_cinematic.json \
  renders/prompt-cinematic --verify-repeat
```

The same prompt on the same project produces the same prompt plan and candidate state. Native style words are versioned. Ambiguous terms remain visible and held rather than receiving silent machine meaning. See `PROMPTS.md`.

## v0.8 native speech: FrameState owns a mouth

New project speech defaults to the native deterministic synthesizer:

```bash
PYTHONPATH=src python -m axm_framestate speak-native \
  "FrameState speaks with its own deterministic voice." \
  renders/native-voice.wav
```

The native route uses inspectable pronunciation/phoneme state and emits exact 48 kHz PCM/WAV without eSpeak, FFmpeg, a model, internet, or downloaded voice. Historical v0.4 speech without an engine preserves its prior eSpeak meaning; explicit eSpeak remains optional. See `SPEECH.md`.

## v0.10 adaptive realization: same truth, different detail and fidelity

FrameState separates canonical project truth from the machine-specific way that truth is rendered.

```bash
PYTHONPATH=src python -m axm_framestate probe-machine

PYTHONPATH=src python -m axm_framestate plan-realization \
  examples/adaptive_realization.json \
  --machine examples/machine_low.json \
  --policy examples/realization_policy.json

PYTHONPATH=src python -m axm_framestate render-adaptive \
  examples/adaptive_realization.json renders/adaptive-low \
  --machine examples/machine_low.json \
  --policy examples/realization_policy.json --no-assemble --verify-repeat
```

The planner consumes **canonical project + bounded machine capability state + explicit user policy** and emits a deterministic render contract. Detail scaling covers particle density, deterministic 3D shadow work, optional effect-pass budget and FFmpeg compatibility export profile. Fidelity scaling is separate: stronger CPU-software realizations can use deterministic internal supersampling and bilinear texture filtering while the canonical canvas stays unchanged. Effects execute after supersample resolve at canonical output resolution so their coordinate semantics do not silently change.

`exact` mode preserves the legacy CPU-software realization and is regression-tested to reproduce the legacy renderer's pixel digests. A dedicated same-circle proof verifies partial-coverage edge pixels on the richer tier without adding objects/details. Unknown capability facts are handled conservatively rather than silently promoting quality. The machine probe records only bounded execution facts and deliberately avoids user/device identifiers or network fingerprinting.

**Working rule: degrade expression, never truth; upgrade expression, never invent truth.** See `REALIZATION.md`.
