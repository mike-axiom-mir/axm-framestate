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
- `LICENSE`

The generated registry and receipt are checked with:

```bash
python tools/generate_public_capabilities.py --check
python -m unittest discover -s tests -p 'test_public_capability_discovery.py' -v
PYTHONPATH=src python -m axm_framestate capabilities
```

The public record intentionally keeps `status: null`. FrameState's capability map classifies individual capabilities as `executable`, `rendered`, `tested`, `external-boundary`, or `gap`; that is not the same thing as one repository-wide maturity label, so discovery does not invent one.

## What the runtime fields mean

`dependencies: 0` describes the Python package's declared runtime dependency list. It does **not** erase FrameState's explicit optional/external boundaries. The real capability map still names FFmpeg, Pillow/FreeType, eSpeak, imported media, and other external boundaries where they apply. Discovery consumers should inspect the capability map before assuming a particular project path is dependency-free.

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
