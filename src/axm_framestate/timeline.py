from __future__ import annotations

from typing import Any


def _smoothstep_milli(t: int) -> int:
    return (3 * t * t // 1000) - (2 * t * t * t // 1_000_000)


def _interp(a: int, b: int, t: int, easing: str) -> int:
    if easing == "hold":
        return a
    if easing == "smoothstep":
        t = _smoothstep_milli(t)
    return a + ((b - a) * t // 1000)


def sample(track: dict[str, Any], frame: int, start_frame: int, end_frame: int) -> int:
    """Sample either a v0.1 from/to track or a v0.2 multi-keyframe curve."""
    if "keyframes" in track:
        keys = track["keyframes"]
        if frame <= keys[0]["frame"]:
            return int(keys[0]["value"])
        if frame >= keys[-1]["frame"]:
            return int(keys[-1]["value"])
        for left, right in zip(keys, keys[1:]):
            if left["frame"] <= frame <= right["frame"]:
                span = right["frame"] - left["frame"]
                if span <= 0:
                    return int(left["value"])
                t = ((frame - left["frame"]) * 1000) // span
                return _interp(int(left["value"]), int(right["value"]), t, str(left.get("easing", "linear")))
        return int(keys[-1]["value"])

    a = int(track["from"])
    b = int(track["to"])
    if track.get("easing") == "hold" or end_frame - start_frame <= 1:
        return a
    if frame <= start_frame:
        t = 0
    elif frame >= end_frame - 1:
        t = 1000
    else:
        t = ((frame - start_frame) * 1000) // (end_frame - start_frame - 1)
    return _interp(a, b, t, str(track.get("easing", "linear")))
