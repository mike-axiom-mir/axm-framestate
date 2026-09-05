# FrameState v0.1 verification

Local verification for the first standalone machine body:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **7/7 PASS**
- repeat-render proof -> canonical project, frame manifest, PCM and WAV equality **PASS**
- executable render -> **72 PPM frames + WAV + MP4**, FFmpeg assembly **PASS**
- controlled visual mutation -> project digest changed, frame-manifest digest changed, audio PCM digest stayed identical **PASS**
- detached posterize organ -> fixture/replay test + four-root adoption + pre-change snapshot **PASS**
- pixel-program organ -> bounded stack validation + fixture replay **PASS**
- gap analysis -> absent and unknown capabilities remain explicit rather than silently degraded **PASS**

Observed baseline digests from the first-light render in the test environment:

- project: `sha256:c1ac5b370cd4a6d6729455d00541e81b0d0e71625bab2ad29919f5caa2c493a6`
- frame manifest: `sha256:d8050c0c2669349f7be6cbe9a23d526d479390167989496413aab1a3d1dd4d98`
- audio PCM: `sha256:6a6f0b8f95c9cfaa5bb35b87040f8911b928b17f1d8c763e8aa666462be7ab28`

The MP4 digest is intentionally not used as the deterministic baseline because FFmpeg is an explicit external codec boundary. FrameState receipts the encoder version and resulting MP4 digest per render instead of claiming cross-machine bit identity.
