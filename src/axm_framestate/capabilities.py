from __future__ import annotations

from typing import Any

CAPABILITIES: dict[str, dict[str, str]] = {
    "canonical-project-state": {"status": "executable", "evidence": "closed normalized v0.1 project schema and digest"},
    "2d-procedural-shapes": {"status": "rendered", "evidence": "rectangles and circles render to exact PPM bytes"},
    "transform-animation": {"status": "rendered", "evidence": "integer linear/hold/smoothstep tracks"},
    "camera-animation": {"status": "rendered", "evidence": "camera x/y/zoom are sampled into frame state"},
    "effect-organs": {"status": "executable", "evidence": "live reusable effects plus detached forge/adoption path"},
    "pixel-program-effects": {"status": "executable", "evidence": "bounded deterministic stack program, no eval"},
    "procedural-tone-audio": {"status": "rendered", "evidence": "mono 48k WAV synthesis with PCM/WAV receipts"},
    "repeat-verification": {"status": "tested", "evidence": "two full renders compared for exact frame manifest and WAV equality"},
    "mp4-assembly": {"status": "external-boundary", "evidence": "FFmpeg when installed; version and output digest recorded"},
    "mechanical-video-review": {"status": "executable", "evidence": "bounded framing/visibility/audio/camera checks with evidence"},
    "daily-recovery": {"status": "executable", "evidence": "deterministic whole-body ZIP snapshot before supported live effect adoption"},
    "text-rendering": {"status": "gap", "evidence": "not implemented"},
    "captions-subtitles": {"status": "gap", "evidence": "not implemented"},
    "image-sprite-import": {"status": "gap", "evidence": "not implemented"},
    "external-audio-import": {"status": "gap", "evidence": "not implemented"},
    "3d-scene-rendering": {"status": "gap", "evidence": "not implemented"},
    "skeletal-animation": {"status": "gap", "evidence": "vocabulary known, runtime absent"},
    "speech-synthesis": {"status": "gap", "evidence": "not implemented"},
    "natural-language-directing": {"status": "gap", "evidence": "no model is required or bundled"},
    "arbitrary-self-modification": {"status": "gap", "evidence": "v0.1 supports bounded effect-organ growth only"},
}


def capability_summary() -> dict[str, Any]:
    return {"schema": "axm.framestate.capability-map/v0.1", "capabilities": CAPABILITIES}


def analyze_requirements(required: list[str]) -> dict[str, Any]:
    if not isinstance(required, list) or not all(isinstance(x, str) and x for x in required):
        raise ValueError("required must be a list of capability ids")
    rows = []
    ready = True
    for cap in required:
        row = CAPABILITIES.get(cap)
        if row is None:
            rows.append({"capability": cap, "status": "unknown", "evidence": "not present in current capability map"})
            ready = False
        else:
            rows.append({"capability": cap, **row})
            if row["status"] == "gap":
                ready = False
    return {"ready": ready, "requirements": rows, "smallest_visible_gaps": [r["capability"] for r in rows if r["status"] in {"gap", "unknown"}]}
