from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_SCHEMA = "axm.framestate.project/v0.1"


class ProjectError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value: Any, label: str, low: int | None = None, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectError(f"{label} must be an integer")
    if low is not None and value < low:
        raise ProjectError(f"{label} must be >= {low}")
    if high is not None and value > high:
        raise ProjectError(f"{label} must be <= {high}")
    return value


def _color(value: Any, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ProjectError(f"{label} must be [r,g,b]")
    return [_integer(v, f"{label}[{i}]", 0, 255) for i, v in enumerate(value)]


def _validate_track(track: Any, label: str) -> dict[str, Any]:
    if not isinstance(track, dict):
        raise ProjectError(f"{label} must be an object")
    allowed = {"from", "to", "easing"}
    unknown = set(track) - allowed
    if unknown:
        raise ProjectError(f"{label} has unknown fields: {sorted(unknown)}")
    start = _integer(track.get("from"), f"{label}.from", -100000, 100000)
    end = _integer(track.get("to"), f"{label}.to", -100000, 100000)
    easing = track.get("easing", "linear")
    if easing not in {"linear", "hold", "smoothstep"}:
        raise ProjectError(f"{label}.easing unsupported")
    return {"from": start, "to": end, "easing": easing}


def normalize_project(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProjectError("project must be an object")
    allowed = {"schema", "id", "title", "canvas", "duration_frames", "background", "camera", "layers", "audio", "effects", "metadata"}
    unknown = set(raw) - allowed
    if unknown:
        raise ProjectError(f"project has unknown fields: {sorted(unknown)}")
    if raw.get("schema") != PROJECT_SCHEMA:
        raise ProjectError(f"schema must be {PROJECT_SCHEMA}")
    project_id = raw.get("id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ProjectError("id must be non-empty text")
    title = raw.get("title", project_id)
    if not isinstance(title, str) or not title.strip():
        raise ProjectError("title must be non-empty text")
    canvas = raw.get("canvas")
    if not isinstance(canvas, dict) or set(canvas) - {"width", "height", "fps"}:
        raise ProjectError("canvas must contain only width, height and fps")
    width = _integer(canvas.get("width"), "canvas.width", 16, 4096)
    height = _integer(canvas.get("height"), "canvas.height", 16, 4096)
    fps = _integer(canvas.get("fps"), "canvas.fps", 1, 120)
    duration = _integer(raw.get("duration_frames"), "duration_frames", 1, fps * 60 * 60)
    background = _color(raw.get("background", [0, 0, 0]), "background")

    camera_raw = raw.get("camera", {})
    if not isinstance(camera_raw, dict) or set(camera_raw) - {"x", "y", "zoom_milli"}:
        raise ProjectError("camera fields must be x, y and zoom_milli")
    camera = {
        "x": _validate_track(camera_raw.get("x", {"from": 0, "to": 0}), "camera.x"),
        "y": _validate_track(camera_raw.get("y", {"from": 0, "to": 0}), "camera.y"),
        "zoom_milli": _validate_track(camera_raw.get("zoom_milli", {"from": 1000, "to": 1000}), "camera.zoom_milli"),
    }
    if camera["zoom_milli"]["from"] <= 0 or camera["zoom_milli"]["to"] <= 0:
        raise ProjectError("camera zoom_milli must stay positive")

    layers_raw = raw.get("layers", [])
    if not isinstance(layers_raw, list):
        raise ProjectError("layers must be an array")
    layers: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, layer in enumerate(layers_raw):
        label = f"layers[{index}]"
        if not isinstance(layer, dict):
            raise ProjectError(f"{label} must be an object")
        allowed_layer = {"id", "kind", "z", "start_frame", "end_frame", "color", "x", "y", "w", "h", "radius", "opacity_milli"}
        extra = set(layer) - allowed_layer
        if extra:
            raise ProjectError(f"{label} has unknown fields: {sorted(extra)}")
        layer_id = layer.get("id")
        if not isinstance(layer_id, str) or not layer_id.strip() or layer_id in ids:
            raise ProjectError(f"{label}.id must be unique non-empty text")
        ids.add(layer_id)
        kind = layer.get("kind")
        if kind not in {"rect", "circle"}:
            raise ProjectError(f"{label}.kind must be rect or circle")
        start = _integer(layer.get("start_frame", 0), f"{label}.start_frame", 0, duration - 1)
        end = _integer(layer.get("end_frame", duration), f"{label}.end_frame", start + 1, duration)
        normalized = {
            "id": layer_id,
            "kind": kind,
            "z": _integer(layer.get("z", 0), f"{label}.z", -10000, 10000),
            "start_frame": start,
            "end_frame": end,
            "color": _color(layer.get("color", [255, 255, 255]), f"{label}.color"),
            "x": _validate_track(layer.get("x", {"from": 0, "to": 0}), f"{label}.x"),
            "y": _validate_track(layer.get("y", {"from": 0, "to": 0}), f"{label}.y"),
            "opacity_milli": _validate_track(layer.get("opacity_milli", {"from": 1000, "to": 1000}), f"{label}.opacity_milli"),
        }
        if kind == "rect":
            normalized["w"] = _validate_track(layer.get("w", {"from": 10, "to": 10}), f"{label}.w")
            normalized["h"] = _validate_track(layer.get("h", {"from": 10, "to": 10}), f"{label}.h")
        else:
            normalized["radius"] = _validate_track(layer.get("radius", {"from": 5, "to": 5}), f"{label}.radius")
        layers.append(normalized)

    audio_raw = raw.get("audio", [])
    if not isinstance(audio_raw, list):
        raise ProjectError("audio must be an array")
    audio: list[dict[str, Any]] = []
    for index, event in enumerate(audio_raw):
        label = f"audio[{index}]"
        if not isinstance(event, dict) or set(event) - {"id", "kind", "start_frame", "end_frame", "frequency_hz", "gain_milli"}:
            raise ProjectError(f"{label} has unsupported fields")
        if event.get("kind") != "tone":
            raise ProjectError(f"{label}.kind currently supports tone only")
        audio.append({
            "id": str(event.get("id", f"tone-{index}")),
            "kind": "tone",
            "start_frame": _integer(event.get("start_frame", 0), f"{label}.start_frame", 0, duration - 1),
            "end_frame": _integer(event.get("end_frame", duration), f"{label}.end_frame", 1, duration),
            "frequency_hz": _integer(event.get("frequency_hz", 440), f"{label}.frequency_hz", 20, 20000),
            "gain_milli": _integer(event.get("gain_milli", 100), f"{label}.gain_milli", 0, 1000),
        })
    for index, event in enumerate(audio):
        if event["end_frame"] <= event["start_frame"]:
            raise ProjectError(f"audio[{index}] end_frame must be after start_frame")

    effects = raw.get("effects", [])
    if not isinstance(effects, list) or not all(isinstance(x, str) and x.strip() for x in effects):
        raise ProjectError("effects must be an array of effect refs")

    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ProjectError("metadata must be an object")

    return {
        "schema": PROJECT_SCHEMA,
        "id": project_id.strip(),
        "title": title.strip(),
        "canvas": {"width": width, "height": height, "fps": fps},
        "duration_frames": duration,
        "background": background,
        "camera": camera,
        "layers": sorted(layers, key=lambda x: (x["z"], x["id"])),
        "audio": audio,
        "effects": effects,
        "metadata": metadata,
    }


def load_project(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectError(f"could not load project: {exc}") from exc
    return normalize_project(raw)
