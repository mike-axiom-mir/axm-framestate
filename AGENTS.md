# AXM FrameState — Collaboration Lane Rule

AXM FrameState uses `main` as the authoritative repository state.

## One chat / instance = one PR lane

Every AI chat or AI instance working on this repository gets **one working branch and one pull-request lane by default**.

Use this shape:

`one AI chat/instance -> one working branch -> one PR -> main`

Keep that chat's related implementation, tests, fixes, verification, cleanup, and follow-up repairs inside the same lane. Do **not** scatter one chat's work across chains such as `fix`, `fix-v2`, `cleanup`, `recovery`, `finalize`, or extra PRs just because the first attempt needs repair.

Only an explicit user handoff or reassignment may transfer ownership of an existing lane.

## Prevent spread

Before opening a new branch or PR, check whether the current chat already owns a live lane. If it does, continue there.

A new idea discovered while working does not automatically justify a new lane. Record or implement it in the current lane when it belongs to the same goal. Leave unrelated future work unimplemented unless the user explicitly expands scope.

## Machine architecture is separate from GitHub transport

Branches and PRs are collaboration hygiene, not FrameState's internal cognition, runtime, creation grammar, deterministic state model, self-modification system, or recovery architecture.

FrameState must remain a **standalone machine**. Other AXM repositories may be studied as donor knowledge, but FrameState must not depend on them at runtime or silently link/import their code. Reimplement useful patterns cleanly inside this repository with explicit provenance notes when appropriate.

## Permanent authority roots

The only permanent authority layer is:

- Truth
- Agency
- Continuity
- Wisdom Before Speed

Everything else in the repository is replaceable working machinery.

## Truth and verification

Do not claim a capability is implemented because a schema or descriptor exists. Distinguish at minimum between:

- described;
- validated;
- executable;
- rendered;
- tested;
- deterministically reproduced;
- externally provided or black-box.

Failures and missing capabilities stay visible rather than being silently replaced with lower-quality behavior.

## Bootstrap note

This repository began empty, so this `AGENTS.md` file is the one unavoidable bootstrap commit placed directly on `main` to establish a base ref. All subsequent implementation work follows the one-chat / one-PR-lane rule above.

## Detail-density and composable capability principle

Quality is often the accumulated result of many small correct details, not one large generic upgrade.

- When improving a system, look for missing small, bounded capabilities, checks, parameters, passes, and repair operations that control specific details or failure modes.
- Prefer many reusable, inspectable, composable capabilities over one opaque "make it better" step when the smaller capabilities create real control or evidence.
- A machine should remain useful without AI: humans, explicit state, recipes, or deterministic logic can invoke the same capabilities directly.
- With AI, the model is primarily an interpretation and orchestration layer: it translates a higher-level goal into selections and combinations of the same underlying capabilities. The AI does not own those capabilities.
- A better reasoning model may improve goal interpretation and composition, while the underlying machine remains portable and usable without that model.
- Judge improvement by accumulated perceptual or functional detail, coherence, failure reduction, and fit to the goal—not by model size, resolution, benchmark score, or one broad upgrade alone.
- For visual, game, asset, animation, and video work, pay attention to small interacting details such as material variation, contact, timing, weight, secondary motion, lighting response, sound layering, asymmetry, wear, scale cues, camera behavior, and continuity.
- Do not fragment working systems merely for ideology. Add granularity where it creates useful control, reuse, diagnosis, repair, or quality.

**Working rule:** thousands of small good details and capabilities in the right places can improve a result more than one simple big upgrade.

## Canonical state and adaptive realization principle

FrameState is an explicit proof case for separating **project truth** from **rendered expression**.

- Canonical project/timeline/scene state, timing meaning, content identity, captions/content semantics, and deterministic receipts remain authoritative.
- Rendered pixels, codec outputs, preview quality, audio synthesis paths, UI skins, and device-specific manifestations are realizations of that state, not the state itself.
- Preserve expression intent separately where needed: cinematic intent, readability, atmosphere, motion weight, sound intent, detail semantics, hierarchy, and other qualities that should survive a cheaper render path.
- Prefer one FrameState body with multiple bounded realization contracts over separate mobile/desktop/lite/ultra project truths.
- Choose realization from canonical state + expression intent + measured machine capabilities + user policy; adaptation may happen at render time or dynamically where the runtime can do so without changing meaning.
- A weak machine should receive cheaper expression, **not weaker project truth**. Timing, scene identity, captions/content, causal meaning, and other non-degradable invariants must remain intact.
- Never let a low-detail render, compressed output, proxy, cache, or preview overwrite richer canonical project state merely because it was produced successfully. Render output is evidence/projection, not authority.
- A richer realization may express more of existing state/intent; it must not invent canonical facts or silently change timing/content simply to appear more cinematic.
- Build realization alternatives as bounded capabilities: resolution, geometry/detail, shading, particles, simulation passes, post-processing, audio richness, preview fidelity, and analogous render choices.
- Apply the split only where representation can honestly remain subordinate to project truth.

**Working rule:** degrade expression, never truth; upgrade expression, never invent truth. Same FrameState project, different valid manifestations.
