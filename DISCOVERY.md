# Public capability discovery

FrameState already has a real local capability map and a Python package/CLI boundary. This lane makes one deliberately broad provider declaration visible to AXM's public-safe discovery path without copying FrameState into a catalog or giving discovery execution authority.

## Provider declaration

Capability id:

`axm.framestate.local-deterministic-video-machine`

The declaration is generated from the existing package metadata plus FrameState's executable capability-map source. It binds these sources by Git blob identity:

- `pyproject.toml`
- `src/axm_framestate/capabilities.py`
- `src/axm_framestate/canonical.py`
- `src/axm_framestate/cli.py`
- `src/axm_framestate/media.py`
- `LICENSE`

The generated registry and receipt are checked with:

```bash
python tools/generate_public_capabilities.py --check
python -m unittest discover -s tests -p 'test_public_capability_discovery.py' -v
```

The public record intentionally keeps `status: null`. FrameState's capability map classifies individual capabilities as `executable`, `rendered`, `tested`, `external-boundary`, or `gap`; that is not the same thing as one repository-wide maturity label, so discovery does not invent one.

## Current v0.16 CLI import boundary

The growth merge changed this truth materially. FrameState v0.16 still declares zero mandatory Python package dependencies, and the core installed CLI now loads and exposes `framestate capabilities` without Pillow installed. Pillow remains a **lazy optional compatibility boundary** for non-native imported image/font formats; it is not a core CLI dependency.

The regenerated public declaration therefore states:

- `declaredPackageDependencies: 0`;
- `dependencies: 0` and `externalPythonPackages: []` for the core discovery/CLI boundary;
- `currentCliImportBoundary: dependency-free-core-lazy-optional-media-v0.16`.

This does not erase external per-capability boundaries. The capability map still names FFmpeg, optional Pillow/FreeType, legacy eSpeak, imported media and other boundaries where they actually apply. Public discovery points to that finer-grained map instead of flattening optional compatibility into a fake mandatory dependency.

The discovery generator also anchors the newly merged growth capabilities: strict canonical JSON admission, media-output confinement, Forge single-writer publication, render checkpoint integrity, the renderer-neutral visual-state bridge, the EchoWorld replay visual bridge, and caller-pinned render-output verification. If those source-backed capability rows or runtime boundaries drift, regeneration fails closed.

`network: false`, `account: false`, and `aiModel: false` mean the declared core FrameState machine requires none of those services to expose its deterministic local contracts. They do not claim that caller-selected external codecs/assets are intrinsically offline.

## Discovery Buddy bridge

The CI lane pins the already-proven portable Discovery Buddy zipapp at exact source ref:

`565c38ecf93a9d563b02211258d8d36fcb1162b5`

CI builds and verifies that one-file consumer, removes its source checkout, then performs:

```text
FrameState source-backed registry
  -> explicit .axm public opt-in
  -> portable Discovery Buddy public scan
  -> exact saved-index verify
  -> exact capability/provider query
```

A query match remains `DISCOVERY_EVIDENCE_ONLY`.

## Authority boundary

Public discovery may answer *where a source-backed declaration exists*. It may not:

- execute FrameState;
- install it;
- choose it automatically;
- mutate a FrameState project;
- promote or merge code;
- declare CANON.

The generated receipt is deterministic integrity/provenance evidence relative to selected source bytes. SHA-1/SHA-256 identities are not signatures or proof of authorship.

## Pattern provenance

The generated-discovery pattern is adapted from the proven Python public-discovery lane in `mike-axiom-mir/axm-casual-loop` at exact ref `f561a8a325444be30ad0b4fee412b3958aa1f1ee`.

No Causal Loop or Discovery Buddy runtime code is copied into FrameState. The adapter is implemented locally against FrameState's own source contracts and the shared public discovery formats.
