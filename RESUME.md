# FrameState v0.12 Crash-Resumable Rendering

FrameState v0.12 adds an interruption-safe boundary around its native frame renderer.

The rule is simple:

`canonical project + conformed media + realization contract -> trusted checkpointed frame prefix -> continue -> final native manifest -> audio/subtitles -> optional FFmpeg assembly`

A file merely existing in the frame directory is not enough to make it trusted resume state.

## CLI

Exact native realization:

```bash
framestate-render-resume project.json renders/final --checkpoint-interval 12
```

Adaptive realization:

```bash
framestate-render-resume project.json renders/final --adaptive --checkpoint-interval 12
```

The same output directory is intentionally reusable. If a valid checkpoint exists, FrameState verifies it and continues from the admitted prefix rather than starting again.

## Checkpoint identity

`render-checkpoint.json` binds at minimum:

- canonical project digest;
- conformed media-manifest digest;
- realization-contract digest when adaptive rendering is used;
- duration;
- canonical canvas;
- every admitted frame index;
- exact frame-file digest;
- exact frame state.

Changing project state, conformed media, or adaptive realization invalidates the old checkpoint and fails closed. FrameState does not silently reuse old pixels for a different movie.

## Crash boundary

Frames are rendered atomically to their target files. At each checkpoint interval the verified frame rows are admitted into the checkpoint.

A crash may therefore leave frame files beyond the last admitted checkpoint. On resume those **unadmitted tail frames are deleted and rendered again**. This avoids promoting bytes merely because they survived the process.

Checkpointed bytes are re-hashed before reuse. A missing or modified admitted frame causes a hard resume failure instead of a quiet repair that could hide corruption.

## Disk gate

Before continuing, FrameState estimates remaining native PPM frame bytes and requires a fixed free-space reserve. If the current filesystem does not have enough headroom, the checkpoint records `HOLD_DISK_BUDGET` and the render does not continue.

This is a conservative native-frame storage gate, not a prediction of total operating-system allocator, codec, cache, or temporary-file use.

## Equivalence gate

The hard regression target is not merely “resume completed.”

For the same canonical project and realization, the final resumed `frame-manifest.json` must equal the uninterrupted native `render_project` reference manifest. Tests also cover:

- project drift refusal;
- corruption of a checkpointed frame;
- removal and rerender of an unadmitted tail;
- adaptive realization using the exact same render contract.

## What is and is not resumable

v0.12 makes **native FrameState frame truth** resumable. Once the native frame manifest is complete, audio/subtitle generation and optional standard-container assembly run normally.

FFmpeg remains an external compatibility boundary. FrameState does not claim to resume libx264/AAC encoder internals halfway through one codec process. A restarted final assembly can reuse the already completed native frames.

## Studio behavior

FrameState Studio now routes final output through this resumable path. Its render directory name is derived from the canonical project identity instead of a timestamp, so retrying the same project naturally reaches the same checkpoint directory.

Editing canonical project state changes the project digest and therefore creates a different valid render identity rather than silently resuming old state.

## Truth boundary

Crash recovery is evidence handling, not magic persistence:

- admitted and verified bytes may be reused;
- unadmitted bytes are disposable;
- stale identity is refused;
- corruption is surfaced;
- canonical project state remains separate from rendered output;
- successful rendering never grants project rewrite authority.
