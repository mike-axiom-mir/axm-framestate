# FrameState v0.4 verification

Hard verification after reconnect recovery:

- `PYTHONPATH=src python -m unittest discover -s tests -v` -> **14/14 PASS**
- original procedural repeat-render proof -> **PASS**
- advanced mixed-media repeat-render proof -> **PASS**
- advanced repeat compares normalized project, conformed-media manifest, every frame manifest/state/pixel digest, stereo PCM and WAV -> **PASS**
- four-shot 320x180 proof film -> **180 frames / 15 seconds / MP4 assembly PASS**
- proof film includes particles, text, captions, masks, chroma, imported video/audio, stereo pan, speech, OBJ UV textures, 3D rotation and shadows -> **PASS**
- fixed-point CORDIC axis checks -> **PASS**
- OBJ v/vt/f parsing -> **PASS**
- detached effect-organ adoption/recovery + bounded pixel-program replay -> **PASS**
- structured shot-plan compilation -> **PASS**
- storyboard from real rendered frames -> **PASS**
- frame analysis remains non-mutating -> **PASS**
- advanced named requirements probe -> **READY**

## Advanced repeat baseline

- project: `sha256:55e21b7a91015691aaeb96e1642740ab6e97207c0824abfedecf9a8fe80c357f`
- frame manifest: `sha256:ff007a7968ab845244460e7f7a0aac6b453e8ef65fbcf12292e0878f4c0df370`
- audio PCM: `sha256:074f2c5f0c501496b165b01acac0d5ecfed7f91c6a582ca6ee5bb5ce729a16db`
- verification: `sha256:5624181583945ee6436830d435fbeccab7bab21d1a62b8d6c9ad8e922fb90ef3`

## Proof-film baseline

- project: `sha256:d5b2d4877bc4656b4dc4038641acb026ab3ac80f3f46e078445bb55e72c17dba`
- frame manifest: `sha256:a606a80f3efbb2005b15b72f4cba711ec7a651b2220cceb914a6c1071f5786d4`
- stereo PCM: `sha256:fdfca9e06d61848460209f0a85b5cf131091596369ea89dd463bf12b033d7ff7`
- MP4: `sha256:76a22d08e3c39b9e25a8c0d25647f6f9a4a4b8b07aa96e68d54a57e4593c5bb6`

The MP4 digest is current-run evidence only. FFmpeg is an external encoding boundary, so no cross-machine bit-identical MP4 claim is made.

## Truth boundary

READY proves only the named capabilities in the requirements file. It is not equivalent to “every filmmaking technique exists.” Natural-language directing and arbitrary self-modification remain explicit gaps. External FFmpeg/eSpeak/Pillow/FreeType behavior remains receipted rather than claimed universally deterministic.
