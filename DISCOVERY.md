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

## Current v0.10 CLI import boundary

The first hosted proof caught a real packaging/runtime truth gap instead of hiding it: current `main` declares no Python package dependencies, but `framestate capabilities` imports the main CLI graph, which reaches `src/axm_framestate/media.py`; that module currently imports `Pillow` at module load time.

The public declaration therefore distinguishes:

- `declaredPackageDependencies: 0` — what current `pyproject.toml` says;
- `dependencies: 1` and `externalPythonPackages: ["Pillow"]` — what the current v0.10 CLI import path actually needs to run;
- `currentCliImportBoundary: Pillow-required-on-v0.10-main` — an explicit source-backed warning rather than a silent dependency claim.

CI installs the same Pillow 12.3.0 compatibility boundary already used by FrameState's repository verification before exercising the real `framestate capabilities` command.

This lane does **not** repair that import topology. Open FrameState PR #3 already owns the distinct Studio/package continuation and explicitly makes Pillow lazy/optional; duplicating that runtime change here would create semantic overlap. If that work lands, this generated declaration is designed to fail closed until the public runtime mapping is reviewed and regenerated against the new package truth.

FrameState's capability map also continues to name FFmpeg, Pillow/FreeType, eSpeak, imported media, and other external boundaries where they apply. Public discovery does not flatten those per-capability distinctions into one unsupported “fully dependency-free machine” story.

`network: false`, `account: false`, and `aiModel: false` mean the declared local FrameState machine does not require those services merely to exist or expose its local deterministic contracts. They do not claim that every possible caller-supplied asset or external compatibility tool is offline by nature.

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
