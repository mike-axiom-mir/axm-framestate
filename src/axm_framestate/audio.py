from __future__ import annotations

import hashlib
import math
import struct
import wave
from pathlib import Path
from typing import Any

from .canonical import digest, file_digest

SAMPLE_RATE = 48000


def render_audio(project: dict[str, Any], path: Path) -> dict[str, Any]:
    fps = project["canvas"]["fps"]
    total_samples = project["duration_frames"] * SAMPLE_RATE // fps
    samples = [0] * total_samples
    for event in project["audio"]:
        start = event["start_frame"] * SAMPLE_RATE // fps
        end = event["end_frame"] * SAMPLE_RATE // fps
        freq = event["frequency_hz"]
        gain = event["gain_milli"]
        amplitude = 32767 * gain // 1000
        # Integer sample index is canonical; sine is deterministic enough for the
        # declared current Python/libm environment and its exact bytes are receipted.
        for i in range(max(0, start), min(total_samples, end)):
            phase = 2.0 * math.pi * freq * (i - start) / SAMPLE_RATE
            value = int(math.sin(phase) * amplitude)
            samples[i] = max(-32768, min(32767, samples[i] + value))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    raw_pcm = b"".join(struct.pack("<h", s) for s in samples)
    result = {
        "schema": "axm.framestate.audio-manifest/v0.1",
        "sample_rate": SAMPLE_RATE,
        "samples": total_samples,
        "pcm_digest": "sha256:" + hashlib.sha256(raw_pcm).hexdigest(),
        "wav_digest": file_digest(path),
        "events_digest": digest(project["audio"]),
    }
    result["manifest_digest"] = digest(result)
    return result
