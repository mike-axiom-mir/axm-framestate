# FrameState v0.7 verification

Hard verification for the Prompt / Style Interpretation Fabric checkpoint:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **26/26 PASS**
- all v0.6 construction, Director, recipe and rehearsal tests remain green;
- same project + same prompt -> same prompt-plan digest and same candidate-project digest -> **PASS**;
- ambiguous `cooler` / `dramatic` prompt -> visible held ambiguity with no construction-state mutation -> **PASS**;
- direct prompt edits modify canonical title/audio/caption state -> **PASS**;
- bounded prompt capability probe -> **READY**;
- prompt-applied candidate -> rehearsal -> final repeat verification -> **PASS**.

## Prompt proof

Input creation brief: `examples/rehearsal_brief_compact.json`

Prompt: `examples/prompt_cinematic.json`

Recognized native tokens:

- `cinematic` -> `builtin:prompt-style.cinematic@1`
- `cleaner` -> `builtin:prompt-style.cleaner@1`
- `more-readable` -> rehearsal hints only

Native prompt operations:

- particle count factor `700/1000`;
- non-speech audio factor `900/1000`;
- visual fade minimum `3` frames where bounded by active span;
- camera interpolation -> smoothstep.

Prompt plan: `sha256:fa20418fac5910f9469d27d70f6f2d8cea769b426735c2cf3d429af276440233`

Candidate project: `sha256:151ef23949d38da84bb0f2adc516e8411dc3ebe1c1e230a27ba8574300bc673c`

Rehearsal then accepted three evidence-backed repairs and stopped at `NO_JUSTIFIED_AUTO_DELTA`:

1. audio headroom;
2. caption readability;
3. text fit.

Final project: `sha256:ad58fef0d9b6877809af1db96379be1da73bd04cc16572d711ecdf63dd4029f9`

Final MP4: `sha256:95daf1ba4c9f51b8b2d72a4a7c829fb410f0db220224deb189409d3829f694db`

Prompt receipt: `sha256:7242380e9069e9bea464c86c8401f58971de4bc436feb4f98e0998c72bc4d7e1`

Rehearsal receipt: `sha256:e89a85cda2d6a592dde2a96c64b5a8240d95126cf101e94b54ba7663969287d3`

Final repeat verification: `sha256:06da3fc062a6e3dcb59a4f556f30916c24f1766aecd07689c7b1e515b561feaf`

## Truth boundary

This proves deterministic bounded prompt interpretation and prompt-to-state replay. It does not prove that words such as `cinematic`, `dramatic`, `lonely`, or `epic` have one universal artistic meaning. Native style words are versioned machine vocabulary; unresolved semantic interpretation remains visible or external.
