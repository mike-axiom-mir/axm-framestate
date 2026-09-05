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
