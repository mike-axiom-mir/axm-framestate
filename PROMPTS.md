# FrameState Prompt / Style Interpretation Fabric

FrameState v0.7 treats prompts as a high-level direction surface, not as hidden project truth.

The native path is:

`prompt -> explicit interpretation plan -> native state operations -> rehearsal -> final project`

## Native prompt classes

- **direct**: bounded instructions such as `lower the music`, `bigger title`, `longer captions`, and footage speed changes;
- **style**: versioned bundles such as `cinematic@1`, `cleaner@1`, `documentary@1`, `warmer@1`, and `cooler-color@1`;
- **semantic**: present only as an explicit interpretation boundary in v0.7. Ambiguous terms do not silently acquire state-changing meaning.

A style word is therefore versioned machine vocabulary. `cinematic@1` currently means smoother camera interpolation, bounded visual fades, and restrained non-speech audio. It does not mean that FrameState proved the result is artistically cinematic.

## Ambiguity

`cooler` is intentionally held because it may mean lower color temperature, more stylish, calmer, or generally better. `cooler colors` is actionable and maps to the explicit `cooler-color@1` bundle.

Unknown or ambiguous language remains in the prompt plan and receipt. Recognized terms may still be applied while unresolved terms remain held when policy is `hold`.

## State and rehearsal

Prompt operations are applied to canonical project state before render. The v0.6 rehearsal loop may then repair measurable consequences such as text overflow, caption reading load, fade budgets, or audio headroom. Rehearsal does not retroactively invent a subjective meaning for ambiguous words.

## CLI

Interpret without changing a project:

```bash
framestate interpret-prompt examples/first_light.json examples/prompt_cinematic.json
```

Apply, rehearse, and make the final video:

```bash
framestate prompt-make examples/first_light.json examples/prompt_cinematic.json renders/prompt-cinematic --verify-repeat
```

Inspect a native token/bundle:

```bash
framestate explain-prompt-token cinematic
```

## Authority boundary

Prompts may guide state change. They do not bypass Truth, Agency, Continuity, or Wisdom Before Speed. Every native prompt effect becomes inspectable state, while external semantic interpretation must remain a named boundary.
