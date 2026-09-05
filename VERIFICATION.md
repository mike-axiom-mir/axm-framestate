# FrameState v0.5 verification

Hard verification after the Director + shot-recipe expansion:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **17/17 PASS**
- all previous v0.4 tests remain green -> **PASS**
- creative brief -> five beats -> canonical 144-frame project -> **PASS**
- creative brief one-command finished MP4 -> **PASS**
- detached shot recipe fixture materializes identically twice and validates through the real shot-plan/project compiler -> **PASS**
- shot recipe adoption requires positive candidate + adoption root fit and establishes daily recovery first -> **PASS**
- adopted recipe becomes discoverable in the live recipe library -> **PASS**
- installed recipe can drive a creative-brief beat -> **PASS**
- compact 40-frame creative-brief repeat proof -> normalized project, conformed media, frame state/pixels, PCM and WAV equality **PASS**

## Director proof film

Input: `examples/creative_brief.json`

- duration: **144 frames / 12 seconds**
- output: **320x180 H.264 + AAC MP4**
- project: `sha256:c6bac1a01f55ef8d4df1645469a19f8027b525d1bf3b1d672fe84f7e6b4f08bd`
- frame manifest: `sha256:3959b6eebeca35ac49fe0166d61d53b7ea16275d295bab9753d792e369f9ecc7`
- audio PCM: `sha256:96be3b0cdfed3e87cf6bf25e34322cc6efa1c9d1b8a5b0d8fa34e94f98ce92a4`
- MP4: `sha256:c9f370581f928efc6f8f4877a43851df95aa4e8ac883d8b3fdb1e4236869307f`
- render receipt: `sha256:36cb0f6452f581d29dde272264bd44428f69734600a7af61e3f9a1432f7ed176`

## Compact brief repeat baseline

A 40-frame no-speech variant was used to keep the hard repeat gate bounded:

- project: `sha256:d428390738b6c96432e823fefc04f62c240681d932f34ba7270b3cdc1b29a139`
- media manifest: `sha256:3e6b5f53996021920001c4b67a386e26a69451d3083065650f3fba3cf1262c1e`
- frame manifest: `sha256:b29ea1f8eed9a548022485b79c04bc81f19ebd3320000b5c87fa8a1e58d13c27`
- audio PCM: `sha256:872e47fae5184240e1855d2f8648ad845a99aafb41387931b286d02c524ada91`
- repeat verification: `sha256:275c25e19b1acd1ca4956f8875f8710a05199fac6bf865277fa276bc081e05d7`

## Truth boundary

The Director layer is deterministic structured direction, not a claim of general natural-language understanding or artistic intelligence. Shot-recipe fixtures prove deterministic materialization and current-project validity, not taste or universal quality. FFmpeg, eSpeak and supplied-font rasterization remain named external boundaries.
