from __future__ import annotations

from typing import Any

from .effects import load_effect_library
from .timeline import sample


def review_project(project: dict[str, Any], machine_root) -> dict[str, Any]:
    """Mechanical review with evidence, not an artistic-quality oracle."""
    width = project["canvas"]["width"]
    height = project["canvas"]["height"]
    duration = project["duration_frames"]
    findings: list[dict[str, Any]] = []
    library = load_effect_library(machine_root)

    for ref in project["effects"]:
        if ref not in library:
            findings.append({"severity": "block", "code": "MISSING_EFFECT", "subject": ref, "evidence": "project references an effect organ absent from the current live library"})

    for layer in project["layers"]:
        start, end = layer["start_frame"], layer["end_frame"]
        sample_frames = sorted(set([start, (start + end - 1) // 2, end - 1]))
        in_frame = 0
        low_opacity = 0
        observations = []
        for frame in sample_frames:
            x = sample(layer["x"], frame, start, end)
            y = sample(layer["y"], frame, start, end)
            opacity = sample(layer["opacity_milli"], frame, start, end)
            visible = -width <= x <= 2 * width and -height <= y <= 2 * height
            in_frame += int(visible)
            low_opacity += int(opacity < 50)
            observations.append({"frame": frame, "x": x, "y": y, "opacity_milli": opacity, "coarsely_near_canvas": visible})
        if in_frame == 0:
            findings.append({"severity": "warn", "code": "LAYER_COARSELY_OFFSCREEN", "subject": layer["id"], "evidence": observations})
        if low_opacity == len(sample_frames):
            findings.append({"severity": "warn", "code": "LAYER_EFFECTIVELY_TRANSPARENT", "subject": layer["id"], "evidence": observations})
        occupancy = (end - start) * 1000 // duration
        if occupancy < 20:
            findings.append({"severity": "note", "code": "VERY_BRIEF_LAYER", "subject": layer["id"], "evidence": {"timeline_occupancy_milli": occupancy}})

    events = project["audio"]
    if events:
        points = sorted({0, duration - 1, *[e["start_frame"] for e in events], *[max(0, e["end_frame"] - 1) for e in events]})
        peak_declared_gain = 0
        peak_frame = 0
        for frame in points:
            gain = sum(e["gain_milli"] for e in events if e["start_frame"] <= frame < e["end_frame"])
            if gain > peak_declared_gain:
                peak_declared_gain, peak_frame = gain, frame
        if peak_declared_gain > 1000:
            findings.append({"severity": "warn", "code": "DECLARED_AUDIO_GAIN_OVERLAP", "subject": "audio", "evidence": {"frame": peak_frame, "summed_gain_milli": peak_declared_gain}, "note": "This is a simple declared-gain warning, not measured loudness or proof of clipping."})

    camera = project["camera"]
    zoom_values = [camera["zoom_milli"]["from"], camera["zoom_milli"]["to"]]
    if max(zoom_values) > 3000 or min(zoom_values) < 250:
        findings.append({"severity": "note", "code": "EXTREME_CAMERA_ZOOM", "subject": "camera", "evidence": {"zoom_milli": zoom_values}})

    return {
        "schema": "axm.framestate.mechanical-review/v0.1",
        "finding_count": len(findings),
        "blocks": sum(f["severity"] == "block" for f in findings),
        "warnings": sum(f["severity"] == "warn" for f in findings),
        "findings": findings,
        "truth_boundary": "This review detects bounded mechanical conditions only. It does not score beauty, story quality, emotional truth, originality or cinematic merit.",
    }
