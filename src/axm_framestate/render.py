from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, file_digest
from .effects import EffectOrgan, load_effect_library
from .timeline import sample


class RenderError(RuntimeError):
    pass


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _blend(dst: tuple[int, int, int], src: list[int], alpha_milli: int) -> tuple[int, int, int]:
    a = max(0, min(1000, alpha_milli))
    inv = 1000 - a
    return tuple(_clamp((dst[i] * inv + src[i] * a) // 1000) for i in range(3))


def _camera_project(value: int, camera_offset: int, zoom_milli: int, center: int) -> int:
    return center + ((value - camera_offset - center) * zoom_milli // 1000)


def render_frame(project: dict[str, Any], frame: int, library: dict[str, EffectOrgan]) -> tuple[bytes, dict[str, Any]]:
    width = project["canvas"]["width"]
    height = project["canvas"]["height"]
    if frame < 0 or frame >= project["duration_frames"]:
        raise RenderError("frame out of range")
    bg = tuple(project["background"])
    pixels = [bg for _ in range(width * height)]
    camera = project["camera"]
    cx = sample(camera["x"], frame, 0, project["duration_frames"])
    cy = sample(camera["y"], frame, 0, project["duration_frames"])
    zoom = sample(camera["zoom_milli"], frame, 0, project["duration_frames"])
    visible: list[dict[str, Any]] = []

    for layer in project["layers"]:
        if not (layer["start_frame"] <= frame < layer["end_frame"]):
            continue
        start, end = layer["start_frame"], layer["end_frame"]
        x = sample(layer["x"], frame, start, end)
        y = sample(layer["y"], frame, start, end)
        alpha = sample(layer["opacity_milli"], frame, start, end)
        sx = _camera_project(x, cx, zoom, width // 2)
        sy = _camera_project(y, cy, zoom, height // 2)
        record: dict[str, Any] = {"id": layer["id"], "kind": layer["kind"], "x": sx, "y": sy, "opacity_milli": alpha, "z": layer["z"]}
        if layer["kind"] == "rect":
            w = max(1, sample(layer["w"], frame, start, end) * zoom // 1000)
            h = max(1, sample(layer["h"], frame, start, end) * zoom // 1000)
            record.update({"w": w, "h": h})
            x0, x1 = sx - w // 2, sx + (w - w // 2)
            y0, y1 = sy - h // 2, sy + (h - h // 2)
            for py in range(max(0, y0), min(height, y1)):
                row = py * width
                for px in range(max(0, x0), min(width, x1)):
                    idx = row + px
                    pixels[idx] = _blend(pixels[idx], layer["color"], alpha)
        else:
            radius = max(1, sample(layer["radius"], frame, start, end) * zoom // 1000)
            record["radius"] = radius
            rr = radius * radius
            for py in range(max(0, sy - radius), min(height, sy + radius + 1)):
                dy = py - sy
                row = py * width
                for px in range(max(0, sx - radius), min(width, sx + radius + 1)):
                    dx = px - sx
                    if dx * dx + dy * dy <= rr:
                        idx = row + px
                        pixels[idx] = _blend(pixels[idx], layer["color"], alpha)
        visible.append(record)

    effect_refs = []
    for ref in project["effects"]:
        if ref not in library:
            raise RenderError(f"missing effect organ: {ref}")
        organ = library[ref]
        pixels = [organ.apply(r, g, b, i % width, i // width) for i, (r, g, b) in enumerate(pixels)]
        effect_refs.append(ref)

    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    body = bytearray()
    for r, g, b in pixels:
        body.extend((r, g, b))
    ppm = header + bytes(body)
    pixel_digest = "sha256:" + hashlib.sha256(bytes(body)).hexdigest()
    state = {
        "frame": frame,
        "camera": {"x": cx, "y": cy, "zoom_milli": zoom},
        "visible_layers": visible,
        "effects": effect_refs,
        "pixel_digest": pixel_digest,
    }
    state["state_digest"] = digest(state)
    return ppm, state


def render_project(project: dict[str, Any], output_dir: Path, machine_root: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    library = load_effect_library(machine_root)
    states = []
    file_rows = []
    for frame in range(project["duration_frames"]):
        ppm, state = render_frame(project, frame, library)
        path = frames_dir / f"frame-{frame:06d}.ppm"
        path.write_bytes(ppm)
        states.append(state)
        file_rows.append({"path": path.name, "digest": file_digest(path)})
    manifest = {
        "schema": "axm.framestate.frame-manifest/v0.1",
        "project_digest": digest(project),
        "frame_count": len(states),
        "states": states,
        "files": file_rows,
    }
    manifest["manifest_digest"] = digest(manifest)
    (output_dir / "frame-manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return manifest
