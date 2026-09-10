from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, normalize_project

REPLAY_SCHEMA = "axm.echoworld.portable-replay/v0.01"
REPLAY_PROVIDER_ID = "axm.echoworld.deterministic-event-replay"
REPLAY_PROVIDER_VERSION = "0.1.0"
WORLD_SCHEMA = "axm.echoworld/v0.01"
PROJECTION_SCHEMA = "axm.framestate.echoworld-replay-visual/v0.1"
MAX_RECEIPT_BYTES = 2 * 1024 * 1024
CELL_PIXELS = 8

_EXPECTED_SOURCE_AUTHORITY = {
    "canonical": False,
    "authorshipVerified": False,
    "physicalRealismProven": False,
    "automaticMerge": False,
}
_PROJECTION_AUTHORITY = {
    "sourceTruthMutation": False,
    "frameStateCanon": False,
    "automaticInstall": False,
    "automaticMerge": False,
    "canon": False,
}


class EchoWorldBridgeError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EchoWorldBridgeError("ECHOWORLD_NON_PORTABLE_JSON") from exc


def _ordered_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EchoWorldBridgeError("ECHOWORLD_NON_PORTABLE_JSON") from exc


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EchoWorldBridgeError(f"{label} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(value) - allowed
    missing = allowed - set(value)
    if extra or missing:
        raise EchoWorldBridgeError(
            f"{label} fields mismatch; missing={sorted(missing)} extra={sorted(extra)}"
        )


def _validate_world(world: Any) -> tuple[int, int]:
    world = _require_object(world, "finalCanonicalState")
    _require_exact_keys(
        world, {"schema", "width", "height", "revision", "cells", "actors"},
        "finalCanonicalState",
    )
    if world["schema"] != WORLD_SCHEMA:
        raise EchoWorldBridgeError("ECHOWORLD_WORLD_SCHEMA_UNSUPPORTED")
    width, height = world["width"], world["height"]
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or not (5 <= width <= 64)
        or not (5 <= height <= 64)
    ):
        raise EchoWorldBridgeError("ECHOWORLD_WORLD_DIMENSIONS_INVALID")
    if isinstance(world["revision"], bool) or not isinstance(world["revision"], int) or world["revision"] < 0:
        raise EchoWorldBridgeError("ECHOWORLD_WORLD_REVISION_INVALID")

    cells = _require_object(world["cells"], "finalCanonicalState.cells")
    expected_ids = {f"C_{x}_{y}" for y in range(height) for x in range(width)}
    if set(cells) != expected_ids:
        raise EchoWorldBridgeError("ECHOWORLD_CELL_INVENTORY_MISMATCH")

    occupant_locations: dict[str, list[str]] = {}
    for cell_id in sorted(cells):
        cell = _require_object(cells[cell_id], f"cells.{cell_id}")
        _require_exact_keys(
            cell, {"cellId", "x", "y", "canonicalRevision", "truthState"},
            f"cells.{cell_id}",
        )
        if cell["cellId"] != cell_id:
            raise EchoWorldBridgeError("ECHOWORLD_CELL_IDENTITY_MISMATCH")
        x, y = cell["x"], cell["y"]
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
            or cell_id != f"C_{x}_{y}"
        ):
            raise EchoWorldBridgeError("ECHOWORLD_CELL_COORDINATE_MISMATCH")
        if isinstance(cell["canonicalRevision"], bool) or not isinstance(cell["canonicalRevision"], int):
            raise EchoWorldBridgeError("ECHOWORLD_CELL_REVISION_INVALID")
        truth = _require_object(cell["truthState"], f"cells.{cell_id}.truthState")
        _require_exact_keys(
            truth, {"type", "material", "occupants", "properties"},
            f"cells.{cell_id}.truthState",
        )
        if not isinstance(truth["type"], str) or not truth["type"]:
            raise EchoWorldBridgeError("ECHOWORLD_CELL_TYPE_INVALID")
        if not isinstance(truth["material"], str) or not truth["material"]:
            raise EchoWorldBridgeError("ECHOWORLD_CELL_MATERIAL_INVALID")
        if not isinstance(truth["properties"], dict):
            raise EchoWorldBridgeError("ECHOWORLD_CELL_PROPERTIES_INVALID")
        if not isinstance(truth["occupants"], list) or not all(
            isinstance(item, str) and item for item in truth["occupants"]
        ):
            raise EchoWorldBridgeError("ECHOWORLD_CELL_OCCUPANTS_INVALID")
        for occupant in truth["occupants"]:
            occupant_locations.setdefault(occupant, []).append(cell_id)

    actors = _require_object(world["actors"], "finalCanonicalState.actors")
    if set(actors) != {"A", "B"}:
        raise EchoWorldBridgeError("ECHOWORLD_ACTOR_SET_UNSUPPORTED")
    for actor_id in sorted(actors):
        actor = _require_object(actors[actor_id], f"actors.{actor_id}")
        _require_exact_keys(actor, {"actorId", "x", "y"}, f"actors.{actor_id}")
        if actor["actorId"] != actor_id:
            raise EchoWorldBridgeError("ECHOWORLD_ACTOR_IDENTITY_MISMATCH")
        x, y = actor["x"], actor["y"]
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
            or not (0 <= x < width)
            or not (0 <= y < height)
        ):
            raise EchoWorldBridgeError("ECHOWORLD_ACTOR_COORDINATE_INVALID")
        expected_cell = f"C_{x}_{y}"
        if occupant_locations.get(actor_id) != [expected_cell]:
            raise EchoWorldBridgeError("ECHOWORLD_ACTOR_OCCUPANCY_MISMATCH")
    unknown_occupants = set(occupant_locations) - set(actors)
    if unknown_occupants:
        raise EchoWorldBridgeError("ECHOWORLD_UNKNOWN_OCCUPANT")
    return width, height


def _validate_replay(receipt: Any, expected_receipt_hash: str) -> tuple[dict[str, Any], int, int]:
    receipt = _require_object(receipt, "receipt")
    if not isinstance(expected_receipt_hash, str) or not expected_receipt_hash:
        raise EchoWorldBridgeError("EXPECTED_RECEIPT_HASH_REQUIRED")
    if receipt.get("schema") != REPLAY_SCHEMA:
        raise EchoWorldBridgeError("ECHOWORLD_REPLAY_SCHEMA_UNSUPPORTED")
    if receipt.get("provider") != {"id": REPLAY_PROVIDER_ID, "version": REPLAY_PROVIDER_VERSION}:
        raise EchoWorldBridgeError("ECHOWORLD_PROVIDER_IDENTITY_UNSUPPORTED")
    if receipt.get("authority") != _EXPECTED_SOURCE_AUTHORITY:
        raise EchoWorldBridgeError("ECHOWORLD_SOURCE_AUTHORITY_WIDENED")
    if receipt.get("canonicalEquivalent") is not True:
        raise EchoWorldBridgeError("ECHOWORLD_CANONICAL_EQUIVALENCE_NOT_PROVEN")
    if receipt.get("receiptHash") != expected_receipt_hash:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_PIN_MISMATCH")
    if not isinstance(receipt["receiptHash"], str) or len(receipt["receiptHash"]) != 64:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_HASH_MALFORMED")

    unsigned = {key: value for key, value in receipt.items() if key != "receiptHash"}
    if _sha256(_canonical_bytes(unsigned)) != receipt["receiptHash"]:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_INTEGRITY_MISMATCH")
    if _sha256(_canonical_bytes(receipt.get("input"))) != receipt.get("inputHash"):
        raise EchoWorldBridgeError("ECHOWORLD_INPUT_HASH_MISMATCH")

    memory_disabled = _require_object(receipt.get("memoryDisabled"), "memoryDisabled")
    memory_enabled = _require_object(receipt.get("memoryEnabled"), "memoryEnabled")
    final_hash = memory_enabled.get("finalCanonicalHash")
    if (
        not isinstance(final_hash, str)
        or len(final_hash) != 64
        or memory_disabled.get("finalCanonicalHash") != final_hash
    ):
        raise EchoWorldBridgeError("ECHOWORLD_FINAL_HASH_MISMATCH")
    world = receipt.get("finalCanonicalState")
    width, height = _validate_world(world)
    if _sha256(_ordered_json_bytes(world)) != final_hash:
        raise EchoWorldBridgeError("ECHOWORLD_FINAL_STATE_HASH_MISMATCH")
    return receipt, width, height


def _state_color(truth_state: dict[str, Any]) -> list[int]:
    raw = hashlib.sha256(_canonical_bytes(truth_state)).digest()
    return [48 + (raw[index] % 160) for index in range(3)]


def _actor_color(actor_id: str) -> list[int]:
    raw = hashlib.sha256(actor_id.encode("utf-8")).digest()
    return [80 + (raw[index] % 144) for index in range(3)]


def create_echoworld_visual_projection(
    receipt: dict[str, Any], *, expected_receipt_hash: str
) -> dict[str, Any]:
    receipt, width, height = _validate_replay(receipt, expected_receipt_hash)
    world = receipt["finalCanonicalState"]
    layers: list[dict[str, Any]] = []
    for cell_id in sorted(world["cells"]):
        cell = world["cells"][cell_id]
        layers.append(
            {
                "id": f"echoworld-{cell_id}",
                "kind": "rect",
                "z": 0,
                "x": cell["x"] * CELL_PIXELS + CELL_PIXELS // 2,
                "y": cell["y"] * CELL_PIXELS + CELL_PIXELS // 2,
                "w": CELL_PIXELS - 1,
                "h": CELL_PIXELS - 1,
                "color": _state_color(cell["truthState"]),
            }
        )
    for actor_id in sorted(world["actors"]):
        actor = world["actors"][actor_id]
        layers.append(
            {
                "id": f"echoworld-actor-{actor_id}",
                "kind": "circle",
                "z": 1,
                "x": actor["x"] * CELL_PIXELS + CELL_PIXELS // 2,
                "y": actor["y"] * CELL_PIXELS + CELL_PIXELS // 2,
                "radius": 2,
                "color": _actor_color(actor_id),
            }
        )

    raw_project = {
        "schema": "axm.framestate.project/v0.5",
        "id": f"echoworld-{receipt['receiptHash'][:16]}",
        "title": "EchoWorld verified replay — visual projection",
        "canvas": {"width": width * CELL_PIXELS, "height": height * CELL_PIXELS, "fps": 1},
        "duration_frames": 1,
        "background": [12, 16, 20],
        "layers": layers,
        "metadata": {
            "axmEchoWorldProjection": {
                "schema": PROJECTION_SCHEMA,
                "sourceProvider": dict(receipt["provider"]),
                "sourceReceiptHash": receipt["receiptHash"],
                "sourceInputHash": receipt["inputHash"],
                "sourceFinalCanonicalHash": receipt["memoryEnabled"]["finalCanonicalHash"],
                "sourceWorldRevision": world["revision"],
                "representation": {
                    "cellPixels": CELL_PIXELS,
                    "cellPalette": "sha256-truth-state-rgb/v1",
                    "actorPalette": "sha256-actor-id-rgb/v1",
                    "meaning": "visual-only deterministic projection; colors are not physical facts",
                },
                "authority": dict(_PROJECTION_AUTHORITY),
            }
        },
    }
    project = normalize_project(raw_project)
    payload = {
        "schema": PROJECTION_SCHEMA,
        "status": "READY_FOR_RENDER",
        "source": {
            "provider": dict(receipt["provider"]),
            "receiptHash": receipt["receiptHash"],
            "inputHash": receipt["inputHash"],
            "finalCanonicalHash": receipt["memoryEnabled"]["finalCanonicalHash"],
        },
        "projectDigest": digest(project),
        "project": project,
        "authority": dict(_PROJECTION_AUTHORITY),
    }
    payload["projectionDigest"] = "sha256:" + _sha256(canonical_json(payload))
    return payload


def verify_echoworld_visual_projection(
    receipt: dict[str, Any], projection: dict[str, Any], *, expected_receipt_hash: str
) -> dict[str, Any]:
    expected = create_echoworld_visual_projection(
        receipt, expected_receipt_hash=expected_receipt_hash
    )
    if projection != expected:
        raise EchoWorldBridgeError("ECHOWORLD_FRAMESTATE_PROJECTION_MISMATCH")
    return {
        "schema": "axm.framestate.echoworld-replay-visual-verification/v0.1",
        "verified": True,
        "sourceReceiptHash": expected["source"]["receiptHash"],
        "projectDigest": expected["projectDigest"],
        "projectionDigest": expected["projectionDigest"],
        "authority": dict(_PROJECTION_AUTHORITY),
    }


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise EchoWorldBridgeError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def load_receipt_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) > MAX_RECEIPT_BYTES:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_FILE_TOO_LARGE")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                EchoWorldBridgeError(f"NON_FINITE_JSON:{value}")
            ),
        )
    except UnicodeDecodeError as exc:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_NOT_UTF8") from exc
    except json.JSONDecodeError as exc:
        raise EchoWorldBridgeError("ECHOWORLD_RECEIPT_JSON_INVALID") from exc
    return _require_object(value, "receipt")


def _write_project_create_only(path: Path, project: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = canonical_json(project) + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(body)
    except FileExistsError as exc:
        raise EchoWorldBridgeError("FRAMESTATE_PROJECT_OUTPUT_EXISTS") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m axm_framestate.echoworld_bridge",
        description="Project an exact pinned EchoWorld replay into a non-authoritative FrameState visual project.",
    )
    parser.add_argument("receipt")
    parser.add_argument("--expected-receipt-hash", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = load_receipt_file(Path(args.receipt))
        projection = create_echoworld_visual_projection(
            receipt, expected_receipt_hash=args.expected_receipt_hash
        )
        _write_project_create_only(Path(args.output), projection["project"])
        summary = {key: value for key, value in projection.items() if key != "project"}
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (EchoWorldBridgeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
