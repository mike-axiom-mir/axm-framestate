# FrameState v0.2 verification

Current local verification before publication of the v0.2 expansion:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **14/14 PASS**
- original procedural repeat-render proof -> **PASS**
- v0.2 imported mixed-media repeat-render proof -> **PASS**
- mixed-media playable render -> imported image + MP4 + text + captions + imported WAV + procedural audio + compositing -> **PASS**
- WebVTT caption export -> **PASS**
- render queue with multiple jobs -> **PASS**
- shot derivation + deterministic storyboard from actual rendered frames -> **PASS**
- shot-plan compiler -> three independent relative shots compiled into one 60-frame canonical project -> **PASS**
- fixed-point CORDIC axis checks -> **PASS**
- primitive 3D cube render -> **PASS**
- OBJ mesh parse + animated 3D rasterization -> **PASS**
- optional eSpeak narration boundary + exact synthesized/decode receipts -> **PASS in this environment**
- detached effect-organ replay/adoption + recovery snapshot -> **PASS**
- bounded pixel-program effect replay -> **PASS**
- broad `genre_open_requirements.json` capability probe -> **READY**

### Mixed-media repeat baseline

- project: `sha256:c76f7c51e79e1641949facd29adea4d331d1a9a9ccdeff919de6b6cc651baffc`
- frame manifest: `sha256:f983bcacbe7ac9659adf4da52d05e165841823bc9753d2430596d0465236eada`
- audio PCM: `sha256:763410bb874cfaaeb7c875edb83413ab856e42a45314ecfdddf7a7ed6e27b444`
- repeat verification: `sha256:877b66809074e135bb7ce8870e07fdf379ef85753dcbc07397cc5022955f2ce9`

### Truth boundary

The READY genre-open probe proves only the named construction capabilities in that requirements file. Remaining explicit gaps include UV texture-mapped 3D, cast shadows, skeletal animation, Unicode shaping, natural-language directing and arbitrary self-modification.

FFmpeg/eSpeak output is treated as an external boundary: input/tool/output identities are receipted, but no claim is made that arbitrary codec/synthesizer implementations are bit-identical across machines.
