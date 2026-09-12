from __future__ import annotations

from typing import Any

from .canonical import digest
from .three_d import rotate_xyz
from .timeline import sample


class SkinningError(ValueError):
    pass


def _vec3(value: Any, label: str) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        raise SkinningError(f"{label} must be three integers")
    return int(value[0]), int(value[1]), int(value[2])


def _rotation_track(value: Any, label: str) -> Any:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if not isinstance(value, dict):
        raise SkinningError(f"{label} must be an integer or deterministic track")
    allowed = {"from", "to", "value", "easing", "keyframes"}
    if set(value) - allowed:
        raise SkinningError(f"{label} contains unsupported fields")
    if "keyframes" in value:
        rows = value["keyframes"]
        if not isinstance(rows, list) or not rows:
            raise SkinningError(f"{label}.keyframes must be non-empty")
        last = -1
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) - {"frame", "value", "easing"}:
                raise SkinningError(f"{label}.keyframes[{i}] invalid")
            if not isinstance(row.get("frame"), int) or not isinstance(row.get("value"), int):
                raise SkinningError(f"{label}.keyframes[{i}] frame/value must be integers")
            if row["frame"] <= last:
                raise SkinningError(f"{label}.keyframes must be ordered")
            if row.get("easing", "linear") not in {"linear", "hold", "smoothstep"}:
                raise SkinningError(f"{label}.keyframes[{i}] easing unsupported")
            last = row["frame"]
    elif value.get("easing", "linear") not in {"linear", "hold", "smoothstep"}:
        raise SkinningError(f"{label}.easing unsupported")
    return value


def normalize_skin_state(rig: Any, weights: Any, clip: Any, vertex_count: int) -> dict[str, Any]:
    if not isinstance(rig, dict) or set(rig) - {"schema", "bones"}:
        raise SkinningError("skin rig must contain only schema/bones")
    schema = rig.get("schema", "axm.framestate.skin-rig3d/v0.1")
    if schema != "axm.framestate.skin-rig3d/v0.1":
        raise SkinningError("unsupported skin rig schema")
    bones_raw = rig.get("bones")
    if not isinstance(bones_raw, list) or not bones_raw or len(bones_raw) > 256:
        raise SkinningError("skin rig bones must contain 1..256 bones")
    bones = []
    seen: set[str] = set()
    for i, raw in enumerate(bones_raw):
        if not isinstance(raw, dict) or set(raw) - {"id", "parent", "pivot", "rotation_mdeg"}:
            raise SkinningError(f"skin rig bone[{i}] invalid")
        bid = raw.get("id")
        if not isinstance(bid, str) or not bid.strip() or bid in seen:
            raise SkinningError(f"skin rig bone[{i}] id invalid/duplicate")
        parent = raw.get("parent")
        if parent is not None and parent not in seen:
            raise SkinningError(f"skin rig bone[{i}] parent must reference an earlier bone")
        pivot = _vec3(raw.get("pivot", [0, 0, 0]), f"skin rig bone[{i}].pivot")
        rotation = _vec3(raw.get("rotation_mdeg", [0, 0, 0]), f"skin rig bone[{i}].rotation_mdeg")
        bones.append({"id": bid, "parent": parent, "pivot": list(pivot), "rotation_mdeg": list(rotation)})
        seen.add(bid)

    if not isinstance(weights, list):
        raise SkinningError("skin weights must be an array")
    rows = []
    weighted_vertices: set[int] = set()
    for i, raw in enumerate(weights):
        if not isinstance(raw, dict) or set(raw) != {"vertex", "influences"}:
            raise SkinningError(f"skin weights[{i}] invalid")
        vertex = raw.get("vertex")
        influences = raw.get("influences")
        if not isinstance(vertex, int) or isinstance(vertex, bool) or not 0 <= vertex < vertex_count:
            raise SkinningError(f"skin weights[{i}].vertex outside mesh")
        if vertex in weighted_vertices:
            raise SkinningError(f"skin weights duplicate vertex {vertex}")
        if not isinstance(influences, list) or not 1 <= len(influences) <= 4:
            raise SkinningError(f"skin weights[{i}].influences must contain 1..4 entries")
        out_influences = []
        total = 0
        used: set[str] = set()
        for j, inf in enumerate(influences):
            if not isinstance(inf, dict) or set(inf) != {"bone", "weight_milli"}:
                raise SkinningError(f"skin weights[{i}].influences[{j}] invalid")
            bone = inf.get("bone")
            weight = inf.get("weight_milli")
            if bone not in seen or bone in used:
                raise SkinningError(f"skin weights[{i}].influences[{j}] bone invalid/duplicate")
            if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 1000:
                raise SkinningError(f"skin weights[{i}].influences[{j}] weight_milli invalid")
            total += weight
            used.add(bone)
            out_influences.append({"bone": bone, "weight_milli": weight})
        if total != 1000:
            raise SkinningError(f"skin weights[{i}] influence weights must sum to 1000")
        rows.append({"vertex": vertex, "influences": out_influences})
        weighted_vertices.add(vertex)

    if clip is None:
        clip = {}
    if not isinstance(clip, dict) or set(clip) - {"schema", "bones"}:
        raise SkinningError("skin clip must contain only schema/bones")
    clip_schema = clip.get("schema", "axm.framestate.skin-clip3d/v0.1")
    if clip_schema != "axm.framestate.skin-clip3d/v0.1":
        raise SkinningError("unsupported skin clip schema")
    clip_bones_raw = clip.get("bones", {}) or {}
    if not isinstance(clip_bones_raw, dict):
        raise SkinningError("skin clip bones must be an object")
    clip_bones: dict[str, dict[str, Any]] = {}
    for bid, raw in clip_bones_raw.items():
        if bid not in seen or not isinstance(raw, dict) or set(raw) - {"rot_x_mdeg", "rot_y_mdeg", "rot_z_mdeg"}:
            raise SkinningError(f"skin clip bone {bid!r} invalid")
        clip_bones[bid] = {
            axis: _rotation_track(raw.get(axis, 0), f"skin clip {bid}.{axis}")
            for axis in ("rot_x_mdeg", "rot_y_mdeg", "rot_z_mdeg")
        }

    normalized = {
        "rig": {"schema": schema, "bones": bones},
        "weights": rows,
        "clip": {"schema": clip_schema, "bones": clip_bones},
        "vertex_count": vertex_count,
        "weighted_vertex_count": len(weighted_vertices),
    }
    normalized["skin_state_digest"] = digest(normalized)
    return normalized


def _rotate_around(point: tuple[int, int, int], pivot: tuple[int, int, int], rotation: tuple[int, int, int]) -> tuple[int, int, int]:
    rel = (point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2])
    moved = rotate_xyz(rel, rotation[0], rotation[1], rotation[2])
    return pivot[0] + moved[0], pivot[1] + moved[1], pivot[2] + moved[2]


def skin_vertices(
    vertices: list[tuple[int, int, int]],
    rig: Any,
    weights: Any,
    clip: Any,
    frame: int,
    start_frame: int,
    end_frame: int,
) -> tuple[list[tuple[int, int, int]], dict[str, Any]]:
    state = normalize_skin_state(rig, weights, clip, len(vertices))
    bones = state["rig"]["bones"]
    clip_bones = state["clip"]["bones"]
    parent_by = {b["id"]: b["parent"] for b in bones}

    rotations: dict[str, tuple[int, int, int]] = {}
    posed_pivots: dict[str, tuple[int, int, int]] = {}
    chains: dict[str, list[str]] = {}

    for bone in bones:
        bid = bone["id"]
        base = bone["rotation_mdeg"]
        anim = clip_bones.get(bid, {})
        rotation = tuple(
            base[i] + sample(anim.get(axis, 0), frame, start_frame, end_frame)
            for i, axis in enumerate(("rot_x_mdeg", "rot_y_mdeg", "rot_z_mdeg"))
        )
        rotations[bid] = rotation
        chain: list[str] = []
        parent = parent_by[bid]
        while parent is not None:
            chain.append(parent)
            parent = parent_by[parent]
        chain.reverse()
        chains[bid] = chain + [bid]
        pivot = tuple(bone["pivot"])
        for ancestor in chain:
            pivot = _rotate_around(pivot, posed_pivots[ancestor], rotations[ancestor])
        posed_pivots[bid] = pivot

    by_vertex = {row["vertex"]: row["influences"] for row in state["weights"]}
    out: list[tuple[int, int, int]] = []
    for index, vertex in enumerate(vertices):
        influences = by_vertex.get(index)
        if not influences:
            out.append(tuple(vertex))
            continue
        sx = sy = sz = 0
        for influence in influences:
            point = tuple(vertex)
            for bid in chains[influence["bone"]]:
                point = _rotate_around(point, posed_pivots[bid], rotations[bid])
            weight = influence["weight_milli"]
            sx += point[0] * weight
            sy += point[1] * weight
            sz += point[2] * weight
        out.append((sx // 1000, sy // 1000, sz // 1000))

    evidence = {
        "skin_state_digest": state["skin_state_digest"],
        "bone_pose_digest": digest({"rotations": rotations, "posed_pivots": posed_pivots}),
        "bone_count": len(bones),
        "weighted_vertex_count": state["weighted_vertex_count"],
        "vertex_count": len(vertices),
        "algorithm": "deterministic-linear-blend-skinning3d-v0.1",
    }
    return out, evidence
