# FrameState Director v0.5

FrameState now separates **creative direction** from low-level timeline construction.

## Creative brief

`axm.framestate.creative-brief/v0.1` is a compact human/AI-facing input surface. A brief names:

- canvas and total duration;
- a visual style (`cinematic`, `clean`, `energetic`, `minimal`, `documentary`);
- available media;
- ordered beats (`title`, `message`, `media`, `reveal`, `closing`);
- optional captions and narration;
- optional bed tone;
- optional installed shot-recipe refs.

FrameState allocates exact beat durations, materializes shots, compiles them through the normal shot-plan compiler, validates the resulting canonical project, then renders through the same receipt path as any hand-authored project.

```bash
PYTHONPATH=src python -m axm_framestate compile-brief \
  examples/creative_brief.json renders/brief/project.json

PYTHONPATH=src python -m axm_framestate make \
  examples/creative_brief.json renders/brief
```

The built-in director is deliberately deterministic and bounded. It does not claim semantic understanding of arbitrary prose or artistic judgment.

## Shot recipe organs

A shot recipe is reusable construction vocabulary, not arbitrary code. The v0.1 recipe format contains:

- stable `id@version` identity;
- purpose;
- typed parameter contract;
- a data-only shot template;
- deterministic fixtures;
- an explicit four-root declaration;
- metadata.

Recipe parameters may be `text`, `integer`, `boolean`, `color`, or `media_id`. Templates use either `{"$param":"name"}` for typed replacement or `{{name}}` inside text.

A candidate follows:

`proposal -> normalize -> fixture materialize twice -> real project validation -> detached receipt -> explicit four-root adoption decision -> daily recovery snapshot -> additive install`

```bash
PYTHONPATH=src python -m axm_framestate spawn-recipe \
  examples/lower_third.recipe.json candidates

PYTHONPATH=src python -m axm_framestate adopt-recipe \
  candidates/axm.recipe.lower-third-1.0.0 \
  --reason "Reuse a verified lower-third construction" \
  --root-fit examples/root_fit.json
```

Adoption gives the recipe **reuse**, not authority. It cannot merge itself, become canon, change permissions, or write arbitrary runtime code.

## Truth boundary

A creative brief proves that a high-level structured direction can compile deterministically into the current movie grammar. A recipe fixture proves deterministic template materialization plus current project validity. Neither proves taste, story quality, emotional truth, or universal suitability.

Free-form natural language may be translated into a creative brief by a human or an explicitly named AI/model boundary. That translator is not required by FrameState and is not silently treated as native deterministic truth.
