# FrameState Rehearsal / Iteration Fabric

FrameState v0.6 adds a bounded deterministic quality loop before final output.

The loop is deliberately not an artistic score and does not claim that beauty, story, originality, emotion or taste can be reduced to one number.

## Path

`candidate -> simulate/render -> inspect evidence -> propose bounded delta -> replay -> compare -> accept/hold -> repeat -> final`

Each accepted delta must improve the mechanical evidence it targets while introducing no new review blocks and no increase in the total mechanical violation count.

If no eligible delta has evidence for improvement, the loop stops with `NO_JUSTIFIED_AUTO_DELTA`. Iteration is not rewarded for its own sake.

## Current rehearsal perspectives

- **Audio headroom**: compares declared timeline overlap with measured pre-clip PCM headroom. The audio mixer now preserves unclamped accumulation truth until the final PCM boundary so clipping can be measured instead of hidden.
- **Caption readability**: measures words/second against an explicit policy target and may extend timing without rewriting words or crossing the next caption.
- **Fade budget**: detects fade-in + fade-out declarations longer than a layer's actual lifetime and fits them inside the active span while preserving their ratio.
- **Text fit**: measures the actual raster dimensions against the canvas and may insert deterministic line breaks. Words are not added, deleted or reordered.
- **Frame/shot observations**: records frame-delta motion evidence and shot-boundary deltas for inspection. These observations do not automatically decide what a cut or pace should feel like.

## Authority boundary

Rehearsal may only apply policy-listed bounded deltas. It cannot silently change the message, invent intent, modify roots, grant permissions, merge, canonize or promote itself.

Subjective interpretation can still be provided by a human or explicitly named AI/model, but that is an external interpretation boundary. The deterministic body remains responsible for reproducible state transitions and evidence.

## CLI

```bash
PYTHONPATH=src python -m axm_framestate rehearse \
  examples/rehearsal_challenge.json renders/rehearsal \
  --policy examples/rehearsal_policy.json \
  --verify-repeat
```

The normal one-command creator can invoke the same loop:

```bash
PYTHONPATH=src python -m axm_framestate make \
  examples/rehearsal_brief_compact.json renders/rehearsed-film \
  --rehearse --policy examples/rehearsal_policy.json --verify-repeat
```

Simulation passes do not assemble MP4. The final output is assembled only after the rehearsal loop stops.
