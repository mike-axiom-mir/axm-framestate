from __future__ import annotations

from typing import Any


def _smoothstep_milli(t: int) -> int:
    # deterministic integer approximation of 3t^2 - 2t^3, t in [0,1000]
    return (3 * t * t // 1000) - (2 * t * t * t // 1_000_000)


def sample(track: dict[str, Any], frame: int, start_frame: int, end_frame: int) -> int:
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
    if track.get("easing") == "smoothstep":
        t = _smoothstep_milli(t)
    return a + ((b - a) * t // 1000)
