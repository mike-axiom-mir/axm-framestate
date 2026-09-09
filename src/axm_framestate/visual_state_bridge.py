from __future__ import annotations

"""Bounded bridge from renderer-neutral AXM visual state into FrameState realization.

This module deliberately consumes data, not code, from other AXM repositories.
The donor contract currently exercised in CI is ``axm.visual-state-compilation/v0.1``
from axm-universal-creation. FrameState remains standalone: the donor repository is
not imported or required at runtime.

Only state with a close native realization meaning is projected. Everything else
is retained as an explicit hold instead of being guessed into FrameState state.
The bridge never edits canonical project truth.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, load_project
from .realization import (
    normalize_machine_capabilities,
    normalize_realization_policy,
    plan_realization,
    verify_contract,
)

VISUAL_STATE_COMPILATION_SCHEMA = "axm.visual-state-compilation/v0.1"
BRIDGE_PLAN_SCHEMA = "axm.framestate.visual-state-realization-plan/v0.1"
BRIDGE_RESULT_SCHEMA = "axm.framestate.visual-state-realization-result/v0.1"
SUPPORTED_TRUTH_STATUSES = {
    "COMPILED_VISUAL_STATE",
    "COMPILED_VISUAL_STATE_WITH_WARNINGS",
}


class VisualStateBridgeError(ValueError):
    pass


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisualStateBridgeError(f"{label} must be a number")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise VisualStateBridgeError(f"{label} must be in [0, 1]")
    return value


def _flatten_state(state: dict[str, Any]) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for layer in sorted(state):
        layer_value = state[layer]
        if not isinstance(layer_value, dict):
            raise VisualStateBridgeError(f"visual state layer {layer!r} must be an object")
        for key in sorted(layer_value):
            rows.append((f"{layer}.{key}", layer_value[key]))
    return rows


def _normalize_compilation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise VisualStateBridgeError("visual state compilation must be an object")
    if raw.get("schema") != VISUAL_STATE_COMPILATION_SCHEMA:
        raise VisualStateBridgeError(
            f"visual state schema must be {VISUAL_STATE_COMPILATION_SCHEMA}"
        )
    status = raw.get("truth_status")
    if status not in SUPPORTED_TRUTH_STATUSES:
        raise VisualStateBridgeError(
            "visual state must already be conflict-resolved; "
            f"received truth_status={status!r}"
        )
    state = raw.get("state")
    if not isinstance(state, dict) or not state:
        raise VisualStateBridgeError("visual state compilation must contain non-empty state")
    truth = raw.get("truth", {})
    if truth is not None and not isinstance(truth, dict):
        raise VisualStateBridgeError("visual state truth must be an object when present")
    return raw


def plan_visual_state_realization(
    compilation: dict[str, Any],
    base_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project supported visual-state directions into an explicit realization policy.

    Current v0.1 mappings are intentionally narrow:

    * ``appearance.render_fidelity`` >= 0.70 can request FrameState's existing
      reference CPU fidelity path (2x internal sampling + bilinear filtering).
    * ``projection.detail_level`` can raise the minimum particle-density channel.
      This is recorded as a *partial* detail projection, not satisfaction of a
      global detail request.

    Explicit user policy fields always win over donor direction.
    """

    source = _normalize_compilation(compilation)
    raw_policy = {} if base_policy is None else dict(base_policy)
    explicit_fields = set(raw_policy) - {"schema", "policy_digest"}
    normalized = normalize_realization_policy(
        {k: v for k, v in raw_policy.items() if k != "policy_digest"}
    )
    policy = {k: v for k, v in normalized.items() if k != "policy_digest"}

    rows = _flatten_state(source["state"])
    row_map = dict(rows)
    mapped: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    consumed: set[str] = set()

    fidelity_path = "appearance.render_fidelity"
    if fidelity_path in row_map:
        fidelity = _number(row_map[fidelity_path], fidelity_path)
        consumed.add(fidelity_path)
        requested: dict[str, Any] = {}
        blocked: list[str] = []
        if fidelity >= 0.70:
            if "min_internal_sample_scale" in explicit_fields:
                blocked.append("min_internal_sample_scale")
            else:
                policy["min_internal_sample_scale"] = max(
                    int(policy["min_internal_sample_scale"]), 2
                )
                requested["min_internal_sample_scale"] = policy[
                    "min_internal_sample_scale"
                ]
            if "preferred_texture_filter" in explicit_fields:
                blocked.append("preferred_texture_filter")
            else:
                policy["preferred_texture_filter"] = "bilinear"
                requested["preferred_texture_filter"] = "bilinear"

        mapped.append(
            {
                "source_path": fidelity_path,
                "source_value": fidelity,
                "status": (
                    "USER_POLICY_PRECEDENCE"
                    if blocked and not requested
                    else "PARTIAL_NATIVE_PROJECTION"
                    if requested
                    else "DIRECTION_RECORDED_NO_POLICY_CHANGE"
                ),
                "target_policy": requested,
                "user_policy_fields_preserved": sorted(blocked),
                "truth_boundary": (
                    "FrameState maps only to its existing reference CPU fidelity controls; "
                    "this does not prove the donor's full visual-fidelity direction is satisfied."
                ),
            }
        )

    detail_path = "projection.detail_level"
    if detail_path in row_map:
        detail = _number(row_map[detail_path], detail_path)
        consumed.add(detail_path)
        requested_density = max(1, min(1000, int(round(detail * 1000))))
        if "min_particle_density_milli" in explicit_fields:
            mapped.append(
                {
                    "source_path": detail_path,
                    "source_value": detail,
                    "status": "USER_POLICY_PRECEDENCE",
                    "target_policy": {},
                    "user_policy_fields_preserved": ["min_particle_density_milli"],
                    "truth_boundary": (
                        "Global visual detail is not equivalent to particle count; "
                        "the only available v0.1 projection is one bounded particle-density channel."
                    ),
                }
            )
        else:
            policy["min_particle_density_milli"] = max(
                int(policy["min_particle_density_milli"]), requested_density
            )
            mapped.append(
                {
                    "source_path": detail_path,
                    "source_value": detail,
                    "status": "PARTIAL_NATIVE_PROJECTION",
                    "target_policy": {
                        "min_particle_density_milli": policy[
                            "min_particle_density_milli"
                        ]
                    },
                    "user_policy_fields_preserved": [],
                    "truth_boundary": (
                        "This raises only FrameState's particle-density floor. It does not claim "
                        "that particle density equals or fully satisfies global visual detail."
                    ),
                }
            )

    for path, value in rows:
        if path in consumed:
            continue
        reason = "NO_EXACT_FRAMESTATE_REALIZATION_MAPPING"
        if path == "projection.resolution_tier":
            reason = "CANONICAL_CANVAS_NOT_SILENTLY_REWRITTEN"
        held.append(
            {
                "source_path": path,
                "source_value": value,
                "status": "HELD",
                "reason": reason,
            }
        )

    effective_policy = normalize_realization_policy(policy)
    plan: dict[str, Any] = {
        "schema": BRIDGE_PLAN_SCHEMA,
        "source_schema": source["schema"],
        "source_truth_status": source["truth_status"],
        "source_compilation_digest": digest(source),
        "source_state_sha256_claim": source.get("state_sha256"),
        "base_policy_digest": normalized["policy_digest"],
        "effective_policy": effective_policy,
        "mapped_paths": mapped,
        "held_paths": held,
        "summary": {
            "source_paths": len(rows),
            "mapped_paths": len(mapped),
            "held_paths": len(held),
            "policy_changed": effective_policy["policy_digest"]
            != normalized["policy_digest"],
        },
        "authority": "NONE",
        "truth_boundary": (
            "Renderer-neutral visual state is direction evidence, not FrameState project truth. "
            "This bridge may alter only explicit realization policy. Unsupported state remains "
            "visible as HELD, user policy wins, and canonical project state is never rewritten."
        ),
    }
    plan["plan_digest"] = digest(plan)
    return plan


def apply_visual_state_realization(
    project: dict[str, Any],
    machine: dict[str, Any],
    compilation: dict[str, Any],
    base_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Plan a FrameState realization from visual-state direction without mutating project truth."""

    before = digest(project)
    machine = normalize_machine_capabilities(
        {k: v for k, v in machine.items() if k not in {"capability_digest", "probe_scope"}}
    )
    bridge = plan_visual_state_realization(compilation, base_policy)
    contract = plan_realization(project, machine, bridge["effective_policy"])
    invariant_check = verify_contract(project, contract)
    after = digest(project)
    if before != after:
        raise VisualStateBridgeError("bridge mutated canonical project input")
    if not invariant_check["passed"]:
        raise VisualStateBridgeError("generated realization contract does not preserve project invariants")

    result: dict[str, Any] = {
        "schema": BRIDGE_RESULT_SCHEMA,
        "bridge_plan": bridge,
        "realization_contract": contract,
        "invariant_check": invariant_check,
        "canonical_project_unchanged": True,
        "authority": "NONE",
    }
    result["result_digest"] = digest(result)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise VisualStateBridgeError(f"{path} must contain a JSON object")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Project an axm.visual-state-compilation/v0.1 artifact into FrameState's "
            "bounded realization policy without rewriting canonical project state."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("compilation", type=Path)
    parser.add_argument("machine", type=Path)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args(argv)

    project = load_project(args.project)
    compilation = _load_json(args.compilation)
    machine = _load_json(args.machine)
    policy = _load_json(args.policy) if args.policy else None
    result = apply_visual_state_realization(project, machine, compilation, policy)
    print(canonical_json(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
