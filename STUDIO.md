# FrameState Studio v0.11

FrameState Studio is the first human-facing creation surface over the existing canonical FrameState machine.

It is deliberately **not** a second editor model and not a browser-only approximation of the engine. The Studio edits canonical `axm.framestate.project/v0.5` state and asks the existing native FrameState renderer for preview frames.

## Launch

From a source checkout:

```bash
PYTHONPATH=src python -m axm_framestate.studio examples/adaptive_realization.json
```

After installation:

```bash
framestate-studio my-film.json
```

With no project path, Studio starts from a small valid default project and saves to `framestate-project.json` when Save is first used.

The server binds to `127.0.0.1` by default. Non-loopback hosts are refused. No cloud service, account, model, or network service is required.

## What the first Studio can do

- open a canonical FrameState project;
- edit project title, canvas, fps, duration, and background;
- add, select, duplicate, edit, and delete common layers;
- add/edit captions;
- add deterministic tones and native speech events;
- enable built-in effects;
- scrub or play the canonical timeline;
- request **actual FrameState renderer** preview frames rather than a separate fake preview renderer;
- switch the preview between exact and adaptive realization;
- apply the bounded prompt compiler and inspect recognized/held interpretation;
- run the existing mechanical review;
- edit the complete canonical JSON when a capability has not yet received a dedicated visual inspector;
- atomically save normalized canonical project bytes;
- start a final exact or adaptive render and inspect the returned receipt.

The UI is dependency-free HTML/CSS/JavaScript served by Python's standard-library HTTP server. It is included as package data in the installed wheel.

## State and interface boundary

The Studio is an interface over canonical state:

`human edit -> canonical candidate -> validation -> canonical project state -> FrameState renderer -> preview/output receipt`

A successful preview does not silently save the project. A successful final render does not overwrite canonical project state. Save normalizes the project first and writes it atomically with `os.replace`.

The raw canonical JSON editor stays present on purpose. A missing dedicated UI control therefore does not make existing state unreachable.

## Local security boundary

- the HTTP server is loopback-only;
- the browser API exposes no arbitrary file-open endpoint;
- the render output name is sanitized and remains under the project's `.framestate/renders/` directory;
- browser POST requests with a foreign `Origin` are refused;
- Studio responses use a restrictive Content Security Policy;
- project saving targets only the project opened at launch, or the default project path chosen by the local Studio session.

This is a local creation surface, not a hardened hostile multi-user web service.

## Current limitations

v0.11 intentionally does not pretend to finish every creation UX problem.

- imported media records and less-common layer types can be edited through canonical JSON before they get dedicated visual controls;
- final render requests are synchronous, so crash-safe resumable long rendering remains the next important operational floor;
- the Studio uses the system browser as its display shell rather than shipping a native desktop webview wrapper;
- unrestricted semantic language remains outside deterministic truth; the built-in prompt compiler still holds ambiguity;
- GPU realization remains a separate future backend problem.

## Verification intent

The Studio regression group covers:

- valid default project creation;
- dependency-free PPM -> PNG preview conversion;
- actual native FrameState renderer preview state;
- explicit prompt-plan -> candidate-state mutation;
- atomic canonical save + load round trip;
- installed package inclusion of the Studio UI assets.

The repository CI added with this floor runs the complete unittest tree, JavaScript syntax validation, package build, wheel installation, and installed Studio resource check.
