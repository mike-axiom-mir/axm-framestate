# EchoWorld replay → FrameState visual projection

This bridge is a **consumer-owned, optional data adapter**. FrameState does not import
EchoWorld code, discover a provider, download a provider, or execute a provider. The
normal FrameState machine remains standalone and useful with no other AXM repository.

The bounded path is:

```text
caller-selected EchoWorld provider
→ deterministic EchoWorld replay receipt
→ provider replay verification
→ caller-owned exact receiptHash pin
→ FrameState structural/integrity admission
→ deterministic one-frame FrameState project
→ ordinary FrameState render / repeat verification
```

The adapter lives at `axm_framestate.echoworld_bridge`. A built/installed FrameState
package can consume an already-produced replay receipt with:

```bash
python -m axm_framestate.echoworld_bridge \
  echoworld-receipt.json \
  --expected-receipt-hash <64-hex-receipt-hash> \
  --output echoworld-project.json

framestate verify-repeat echoworld-project.json renders/echoworld-proof
```

`--expected-receipt-hash` is deliberately required. Discovery or possession of a
receipt is not adoption authority.

## What FrameState checks itself

Before creating project state, the adapter independently checks:

- exact EchoWorld replay/provider/world contract versions;
- the caller-selected `receiptHash`;
- the replay receipt's canonical SHA-256 envelope;
- the replay input SHA-256;
- memory-off / memory-on final canonical hash agreement;
- the exact final canonical-state SHA-256;
- complete rectangular cell inventory and cell coordinate identity;
- actor identity, bounds, and exact actor/cell occupancy agreement;
- the source authority envelope remains non-canonical and non-merge-authoritative;
- strict UTF-8/JSON input with duplicate keys and non-finite numbers rejected.

The resulting FrameState project is then passed through FrameState's normal
`normalize_project()` boundary and receives the ordinary FrameState project digest.

## What FrameState does not pretend to verify

FrameState does **not** reimplement EchoWorld's event engine in Python. Therefore the
adapter does not claim that local structural checks alone prove that the receipt was
honestly produced by the EchoWorld provider. A caller that needs that evidence should
first run EchoWorld's own deterministic `verifyPortableReplay()` / `echoworld-replay
verify` against provider bytes it deliberately selected.

The dedicated cross-repository workflow proves that stronger path with EchoWorld PR #7
pinned to exact source head:

`ea7c3b654a05de19a40a4e7b3a17ffa05cf9d800`

CI packs that provider, installs it into an unrelated local consumer, generates a real
event stream, produces and replay-verifies its receipt, then feeds the exact pinned
receipt into an installed FrameState package and requires FrameState repeat rendering
to pass.

That CI pin is interoperability evidence, not a runtime dependency and not authorship
authentication.

## Representation contract

Every EchoWorld canonical cell becomes one static FrameState rectangle. The rectangle
RGB value is derived from SHA-256 of that cell's complete `truthState`, so a truth-state
change cannot silently keep the same declared palette input. Actors are overlaid as
small circles with deterministic SHA-256-derived colors. The complete source receipt
hash, input hash, final canonical hash, provider identity, world revision, mapping
version, and authority boundary are carried in project metadata.

Those colors are **visualization mechanics, not physical facts or semantic labels**.
A different legitimate visual language could render the same EchoWorld truth. This
bridge only provides one deterministic inspectable projection.

The generated project grants no EchoWorld truth mutation, FrameState CANON, automatic
install, automatic merge, or CANON authority. Rendering the project changes neither
the source replay nor EchoWorld state.

## Runtime / privacy boundary

The adapter is Python-standard-library plus existing FrameState code. It requires no
network, cloud, account, AI model, API key, package registry, telemetry, or background
provider execution. The receipt file is read only from the caller-selected local path.
The output path is create-only so an existing project is not silently replaced.

SHA-256 establishes content identity/integrity relative to the selected bytes. It is
not a signature and does not authenticate who authored either repository or receipt.
