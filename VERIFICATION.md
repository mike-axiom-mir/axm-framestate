# FrameState v0.6 verification

Hard verification after the Rehearsal / Iteration Fabric expansion:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **21/21 PASS**
- all previous v0.5 construction/Director/recipe gates remain green -> **PASS**
- rehearsal requirements probe -> **READY**
- deterministic rehearsal repairs deliberately injected audio/caption/fade/text-fit quality debt -> **PASS**
- clean-project rehearsal stops without rewriting canonical state -> **PASS**
- two independent tiny rehearsal runs reach the same final project and same rehearsal receipt -> **PASS**
- final rehearsed Director proof repeat verification -> **PASS**

## Rehearsed Director proof

Input: `examples/rehearsal_brief_compact.json`

The high-level brief compiles to a 72-frame candidate, then rehearsal performs:

1. **AUDIO_HEADROOM**: declared gain `2200 -> 915`; measured pre-clip peak `72088 -> 29982`; clipped sample values `201480 -> 0`.
2. **CAPTION_READABILITY**: reading load `4500 -> 3483` milli-words/second.
3. **TEXT_FIT**: aggregate horizontal overflow `500 -> 0` pixels through deterministic line wrapping with unchanged words.
4. Stop: `NO_JUSTIFIED_AUTO_DELTA`.

Final output:

- duration: **72 frames / 6 seconds**
- output: **160x90 H.264 + AAC MP4**
- final project: `sha256:13e471271ab209fed2c98ee044ac2baab1fb312196e014b1979058787d5bb218`
- MP4: `sha256:8e0e0e1595f914bd9ffba074a93d52c06b18baada426343d419620b07b3570a0`
- final repeat verification: `sha256:8885db44b15375c7bdb6a758b708107962a510b7e4732842247ea042180c4838`
- rehearsal receipt: `sha256:9d305bb6a02fad3ba84a8a796a9121b42fdf435e86a5123390eeff62dd0ecb64`

## Truth boundary

This proves deterministic **mechanical iteration**, not a universal quality function. Rehearsal currently knows how to reason about measurable construction relationships such as clipping/headroom, text raster fit, caption timing and fade lifetime. Story, emotion, originality, visual taste and meaning remain interpretation surfaces rather than hidden scalar rewards.

External FFmpeg/eSpeak/font behavior remains named and receipted. The four permanent roots remain Truth, Agency, Continuity, and Wisdom Before Speed.
