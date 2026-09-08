# FrameState v0.8 verification

Hard verification for the Native Deterministic Speech Organ checkpoint:

- existing v0.7 machine/prompt/rehearsal regression groups remain green;
- native-speech group -> **5/5 PASS**;
- aggregate current checkpoint -> **31/31 PASS across four test groups**;
- native-speech capability probe -> **READY**;
- same text + voice + rate -> same PCM + speech receipt -> **PASS**;
- native timeline speech while eSpeak/FFmpeg discovery is mocked unavailable -> **PASS**;
- legacy v0.4 speech without engine -> `espeak`, new v0.5 speech without engine -> `native` -> **PASS**;
- creative-brief narration defaults to native engine -> **PASS**.

## Native standalone speech proof

Text:

`FrameState speaks with its own deterministic voice.`

Voice profile: `native-neutral-1`

- sample rate: **48000 Hz**
- channels: **1**
- native duration: **162240 samples / 3.38 seconds**
- external dependencies: **[]**
- raw native speech PCM: `sha256:f9b926c2afe8825db0b9e554e11fd79558304bb5a391b7a1650fef9de6e05c76`
- standalone WAV: `sha256:5740e370f4643ae1b826e394196c149bc77f036ac1d116892106fd918ec38039`
- native speech receipt: `sha256:99ec2e14db8a61503dea7c00e2cadc50a309729e149c0fd6793f2900e1d3e244`

## Native speech movie proof

Input: `examples/native_speech.json`

The FrameState core render (frames + native PCM/WAV, no MP4 assembly) records:

- canonical project: `sha256:5d693698ed4ed598cde2133776d813aee841d8b29c4d6d42828d3cf9760211e4`
- mixed audio PCM: `sha256:2c8d40f9e0596203bf13e570c66470f68ba906113d84d2c42204022bc82e860d`
- speech engine: `native`
- speech external dependencies: `[]`

The same project was also exported through the existing explicit FFmpeg compatibility boundary:

- duration: **48 frames / 4 seconds**
- output: **160x90 H.264 + 48 kHz mono AAC MP4**
- MP4: `sha256:af1a06b2054adcb067efeb8a5179d8aa8456e526a056f0fa11d150416f2be991`
- native project repeat verification: `sha256:07199e0bcce6071a48d28052a6666fc1c0960b542a615f4e3ac4bcceaa1067cc`

## Truth boundary

This proves a native deterministic first-generation speech path, not human-quality speech, arbitrary language understanding, voice cloning, or a neural TTS model. Pronunciation coverage is currently bounded by an inspectable lexicon and deterministic spelling rules. eSpeak remains optional and explicit. MP4/H.264 export still uses FFmpeg; native speech itself does not.
