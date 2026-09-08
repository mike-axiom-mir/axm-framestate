# FrameState Native Speech v0.8

FrameState v0.8 owns a first-generation deterministic speech path.

The native path is:

`text -> pronunciation rules/lexicon -> phoneme timing state -> deterministic formant/noise synthesis -> exact s16 PCM -> FrameState audio mixer`

It does not require eSpeak, FFmpeg, a neural model, an internet connection, or a downloaded voice.

## Native voice profiles

- `native-neutral-1`
- `native-low-1`
- `native-bright-1`

These are versioned construction profiles. They are not attempts to imitate a real person.

## Inspectable speech state

`inspect-speech` exposes the phoneme/pause plan before samples are synthesized:

```bash
PYTHONPATH=src python -m axm_framestate inspect-speech \
  "FrameState speaks with its own deterministic voice."
```

## Standalone WAV

```bash
PYTHONPATH=src python -m axm_framestate speak-native \
  "FrameState speaks with its own deterministic voice." \
  renders/native-voice.wav
```

The resulting receipt includes text, phoneme, PCM and WAV identities plus `external_dependencies: []`.

## Timeline speech

Project schema `axm.framestate.project/v0.5` adds an explicit speech engine field. New v0.5 speech defaults to `native`. Historical v0.4-and-earlier speech without an engine preserves its old eSpeak meaning during normalization. This avoids silently rewriting old project intent while making native speech the default for new work.

Example:

```json
{
  "id": "voice",
  "kind": "speech",
  "engine": "native",
  "text": "FrameState speaks.",
  "voice": "native-neutral-1",
  "rate_wpm": 165
}
```

Creative-brief narration now compiles to the native engine by default.

## Truth boundary

This is a small rule/formant synthesizer, not a neural TTS model and not a claim of human-level naturalness. English pronunciation coverage is deliberately bounded by an inspectable lexicon plus deterministic spelling rules. Unknown or awkward pronunciations are quality gaps to improve, not reasons to hide an external model inside the native claim.

The previous eSpeak path remains available when explicitly selected as `engine: "espeak"`; it remains an external boundary with its own receipts.
