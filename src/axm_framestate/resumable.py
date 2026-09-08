from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .audio import render_audio
from .canonical import canonical_json, digest, file_digest, load_project, normalize_project
from .captions import export_vtt
from .effects import load_effect_library
from .media import MediaCache
from .realization import (
    normalize_machine_capabilities,
    normalize_realization_policy,
    plan_realization,
    verify_contract,
    write_realization_inputs,
)
from .receipts import _assemble_video, _stable_receipt_digest
from .render import render_frame, render_project

CHECKPOINT_SCHEMA = "axm.framestate.render-checkpoint/v0.1"
FRAME_MANIFEST_SCHEMA = "axm.framestate.frame-manifest/v0.4"
REALIZED_FRAME_MANIFEST_SCHEMA = "axm.framestate.frame-manifest/v0.6"


class ResumeError(RuntimeError):
    pass


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _identity(project: dict[str, Any], media_digest: str, realization: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "project_digest": digest(project),
        "media_manifest_digest": media_digest,
        "realization_contract_digest": realization.get("contract_digest") if realization else None,
        "duration_frames": project["duration_frames"],
        "canvas": project["canvas"],
    }


def _estimate_remaining_bytes(project: dict[str, Any], completed: int) -> int:
    w = project["canvas"]["width"]
    h = project["canvas"]["height"]
    remaining = max(0, project["duration_frames"] - completed)
    return remaining * (w * h * 3 + 128)


def _disk_gate(output_dir: Path, project: dict[str, Any], completed: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(output_dir)
    estimate = _estimate_remaining_bytes(project, completed)
    reserve = 64 * 1024 * 1024
    passed = usage.free >= estimate + reserve
    return {
        "passed": passed,
        "free_bytes": usage.free,
        "estimated_remaining_frame_bytes": estimate,
        "reserve_bytes": reserve,
    }


def _load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResumeError("render checkpoint is unreadable") from exc
    if raw.get("schema") != CHECKPOINT_SCHEMA:
        raise ResumeError("unsupported render checkpoint schema")
    return raw


def _verify_checkpoint(checkpoint: dict[str, Any], identity: dict[str, Any], frame_dir: Path) -> list[dict[str, Any]]:
    if checkpoint.get("identity") != identity:
        raise ResumeError("render checkpoint identity does not match current project/media/realization")
    rows = checkpoint.get("completed", [])
    if not isinstance(rows, list):
        raise ResumeError("render checkpoint completed rows are invalid")
    for expected, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("frame") != expected:
            raise ResumeError("render checkpoint frames are not contiguous")
        file_row = row.get("file")
        if not isinstance(file_row, dict) or file_row.get("path") != f"frame-{expected:06d}.ppm":
            raise ResumeError("render checkpoint frame file identity is invalid")
        path = frame_dir / file_row["path"]
        if not path.is_file() or file_digest(path) != file_row.get("digest"):
            raise ResumeError(f"checkpointed frame {expected} bytes do not match receipt")
        state = row.get("state")
        if not isinstance(state, dict) or state.get("frame") != expected:
            raise ResumeError("render checkpoint frame state is invalid")
    return rows


def _remove_unadmitted_frames(frame_dir: Path, admitted_count: int) -> int:
    removed = 0
    for path in sorted(frame_dir.glob("frame-*.ppm")):
        try:
            frame = int(path.stem.split("-")[-1])
        except ValueError:
            continue
        if frame >= admitted_count:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def render_frames_resumable(
    project: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    *,
    realization: dict[str, Any] | None = None,
    checkpoint_interval: int = 12,
    max_new_frames: int | None = None,
) -> dict[str, Any]:
    project = normalize_project(project)
    output_dir = Path(output_dir)
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "render-checkpoint.json"
    library = load_effect_library(machine_root)
    cache = MediaCache(project, output_dir, machine_root)
    identity = _identity(project, cache.manifest["manifest_digest"], realization)
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        rows: list[dict[str, Any]] = []
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "identity": identity,
            "completed": rows,
            "status": "IN_PROGRESS",
            "checkpoint_interval": max(1, int(checkpoint_interval)),
            "truth_boundary": "only checkpoint-admitted frame bytes/state are trusted for resume; unadmitted tail frames are discarded and rerendered",
        }
    else:
        rows = _verify_checkpoint(checkpoint, identity, frame_dir)
    removed_unadmitted = _remove_unadmitted_frames(frame_dir, len(rows))
    disk = _disk_gate(output_dir, project, len(rows))
    if not disk["passed"]:
        checkpoint["disk_gate"] = disk
        checkpoint["status"] = "HOLD_DISK_BUDGET"
        checkpoint["checkpoint_digest"] = digest({k: v for k, v in checkpoint.items() if k != "checkpoint_digest"})
        _atomic_write(checkpoint_path, canonical_json(checkpoint) + b"\n")
        raise ResumeError("insufficient disk headroom for remaining native frame bytes")

    interval = max(1, int(checkpoint_interval))
    remaining_budget = None if max_new_frames is None else max(0, int(max_new_frames))
    start = len(rows)
    pending: list[dict[str, Any]] = []
    rendered_now = 0

    for frame in range(start, project["duration_frames"]):
        if remaining_budget is not None and rendered_now >= remaining_budget:
            break
        ppm, state = render_frame(project, frame, library, cache, realization)
        path = frame_dir / f"frame-{frame:06d}.ppm"
        _atomic_write(path, ppm)
        pending.append({"frame": frame, "state": state, "file": {"path": path.name, "digest": file_digest(path)}})
        rendered_now += 1
        if len(pending) >= interval:
            rows.extend(pending)
            pending = []
            checkpoint["completed"] = rows
            checkpoint["status"] = "IN_PROGRESS"
            checkpoint["disk_gate"] = disk
            checkpoint["checkpoint_digest"] = digest({k: v for k, v in checkpoint.items() if k != "checkpoint_digest"})
            _atomic_write(checkpoint_path, canonical_json(checkpoint) + b"\n")

    if pending:
        rows.extend(pending)
        checkpoint["completed"] = rows

    complete = len(rows) == project["duration_frames"]
    checkpoint["status"] = "COMPLETE" if complete else "PAUSED"
    checkpoint["disk_gate"] = disk
    checkpoint["removed_unadmitted_frames_on_resume"] = removed_unadmitted
    checkpoint["rendered_frames_this_run"] = rendered_now
    checkpoint["checkpoint_digest"] = digest({k: v for k, v in checkpoint.items() if k != "checkpoint_digest"})
    _atomic_write(checkpoint_path, canonical_json(checkpoint) + b"\n")

    if not complete:
        return {
            "schema": "axm.framestate.resumable-frame-result/v0.1",
            "status": "PAUSED",
            "completed_frames": len(rows),
            "total_frames": project["duration_frames"],
            "rendered_frames_this_run": rendered_now,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_digest": checkpoint["checkpoint_digest"],
            "removed_unadmitted_frames_on_resume": removed_unadmitted,
        }

    states = [row["state"] for row in rows]
    files = [row["file"] for row in rows]
    manifest = {
        "schema": REALIZED_FRAME_MANIFEST_SCHEMA if realization else FRAME_MANIFEST_SCHEMA,
        "project_digest": digest(project),
        "media_manifest_digest": cache.manifest["manifest_digest"],
        "frame_count": len(states),
        "states": states,
        "files": files,
    }
    if realization:
        manifest["realization_contract_digest"] = realization.get("contract_digest")
        manifest["realization_tier"] = realization.get("tier")
        manifest["fidelity"] = realization.get("fidelity")
    manifest["manifest_digest"] = digest(manifest)
    _atomic_write(output_dir / "frame-manifest.json", canonical_json(manifest) + b"\n")
    checkpoint["frame_manifest_digest"] = manifest["manifest_digest"]
    checkpoint["checkpoint_digest"] = digest({k: v for k, v in checkpoint.items() if k != "checkpoint_digest"})
    _atomic_write(checkpoint_path, canonical_json(checkpoint) + b"\n")
    return {
        "schema": "axm.framestate.resumable-frame-result/v0.1",
        "status": "COMPLETE",
        "completed_frames": len(rows),
        "total_frames": project["duration_frames"],
        "rendered_frames_this_run": rendered_now,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_digest": checkpoint["checkpoint_digest"],
        "frame_manifest": manifest,
        "removed_unadmitted_frames_on_resume": removed_unadmitted,
    }


def render_resumable_with_receipt(
    project: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    *,
    assemble: bool = True,
    profile: str = "h264",
    checkpoint_interval: int = 12,
    max_new_frames: int | None = None,
) -> dict[str, Any]:
    project = normalize_project(project)
    out = Path(output_dir)
    frames = render_frames_resumable(project, out, machine_root, checkpoint_interval=checkpoint_interval, max_new_frames=max_new_frames)
    if frames["status"] != "COMPLETE":
        return frames
    fm = frames["frame_manifest"]
    am = render_audio(project, out / "audio.wav", machine_root, out)
    subs = export_vtt(project, out / "captions.vtt")
    assembly, video = _assemble_video(project, out, profile, assemble)
    rec = {
        "schema": "axm.framestate.render-receipt/v0.11",
        "project_id": project["id"],
        "project_digest": digest(project),
        "media_manifest_digest": fm["media_manifest_digest"],
        "frame_manifest_digest": fm["manifest_digest"],
        "audio_manifest": am,
        "subtitle_export": subs,
        "video": video,
        "assembly": assembly,
        "resumable": {
            "checkpoint_path": frames["checkpoint_path"],
            "checkpoint_digest": frames["checkpoint_digest"],
            "rendered_frames_this_run": frames["rendered_frames_this_run"],
            "completed_frames": frames["completed_frames"],
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "truth_boundary": {
            "canonical_project": "normalized and digest-bound",
            "resume": "only checkpoint-admitted frame state/bytes can be reused; project/media/realization drift fails closed",
            "unadmitted_tail": "frame files written after the last admitted checkpoint are discarded and rerendered",
            "container_video": "external FFmpeg boundary; resumable native frame truth does not imply resumable codec internals",
        },
    }
    rec["receipt_digest"] = _stable_receipt_digest(rec)
    _atomic_write(out / "render-receipt.json", canonical_json(rec) + b"\n")
    return rec


def render_realized_resumable_with_receipt(
    project: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    machine: dict[str, Any],
    policy: dict[str, Any] | None = None,
    *,
    assemble: bool = True,
    checkpoint_interval: int = 12,
    max_new_frames: int | None = None,
) -> dict[str, Any]:
    project = normalize_project(project)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    machine = normalize_machine_capabilities({k: v for k, v in machine.items() if k not in {"capability_digest", "probe_scope"}})
    policy = normalize_realization_policy({k: v for k, v in (policy or {}).items() if k != "policy_digest"})
    contract = plan_realization(project, machine, policy)
    invariant_before = verify_contract(project, contract)
    if not invariant_before["passed"]:
        raise ResumeError("realization contract does not match canonical project")
    write_realization_inputs(out, machine, policy, contract)
    frames = render_frames_resumable(project, out, machine_root, realization=contract, checkpoint_interval=checkpoint_interval, max_new_frames=max_new_frames)
    if frames["status"] != "COMPLETE":
        return {**frames, "realization_contract_digest": contract["contract_digest"]}
    fm = frames["frame_manifest"]
    am = render_audio(project, out / "audio.wav", machine_root, out)
    subs = export_vtt(project, out / "captions.vtt")
    assembly, video = _assemble_video(project, out, contract["render"]["export_profile"], assemble, machine["ffmpeg_available"])
    invariant_after = verify_contract(project, contract)
    rec = {
        "schema": "axm.framestate.render-receipt/v0.12",
        "project_id": project["id"],
        "project_digest": digest(project),
        "media_manifest_digest": fm["media_manifest_digest"],
        "frame_manifest_digest": fm["manifest_digest"],
        "audio_manifest": am,
        "subtitle_export": subs,
        "video": video,
        "assembly": assembly,
        "resumable": {
            "checkpoint_path": frames["checkpoint_path"],
            "checkpoint_digest": frames["checkpoint_digest"],
            "rendered_frames_this_run": frames["rendered_frames_this_run"],
            "completed_frames": frames["completed_frames"],
        },
        "realization": {
            "machine_capability_digest": machine["capability_digest"],
            "policy_digest": policy["policy_digest"],
            "contract_digest": contract["contract_digest"],
            "tier": contract["tier"],
            "backend": contract["backend"],
            "render": contract["render"],
            "fidelity": contract["fidelity"],
            "fidelity_limited": contract["fidelity_limited"],
            "expression_deltas": contract["expression_deltas"],
            "invariants_before": invariant_before,
            "invariants_after": invariant_after,
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "truth_boundary": {
            "canonical_project": "unchanged normalized project, digest-bound before and after realization",
            "resume": "checkpoint identity includes canonical project, conformed media and realization contract",
            "unadmitted_tail": "uncheckpointed tail frames never become trusted resume state",
            "container_video": "external FFmpeg encoding boundary; only native frames/state are crash-resumable here",
        },
    }
    rec["receipt_digest"] = _stable_receipt_digest(rec)
    _atomic_write(out / "render-receipt.json", canonical_json(rec) + b"\n")
    return rec


def compare_resumable_to_reference(project: dict[str, Any], base_dir: Path, machine_root: Path) -> dict[str, Any]:
    """Small deterministic verification helper used by tests and manual gates."""
    base_dir = Path(base_dir)
    project = normalize_project(project)
    reference = render_project(project, base_dir / "reference", machine_root)
    resumed_dir = base_dir / "resumed"
    first = render_frames_resumable(project, resumed_dir, machine_root, checkpoint_interval=1, max_new_frames=max(1, project["duration_frames"] // 2))
    second = render_frames_resumable(project, resumed_dir, machine_root, checkpoint_interval=2)
    resumed = json.loads((resumed_dir / "frame-manifest.json").read_text(encoding="utf-8"))
    checks = {
        "paused_first": first["status"] == "PAUSED",
        "completed_second": second["status"] == "COMPLETE",
        "manifest_equal": reference == resumed,
    }
    result = {"schema": "axm.framestate.resume-equivalence/v0.1", "passed": all(checks.values()), "checks": checks, "manifest_digest": resumed["manifest_digest"]}
    result["verification_digest"] = digest(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="framestate-render-resume", description="Crash-resumable FrameState native frame render")
    parser.add_argument("project")
    parser.add_argument("output")
    parser.add_argument("--adaptive", action="store_true")
    parser.add_argument("--profile", choices=["fast", "h264", "quality"], default="h264")
    parser.add_argument("--checkpoint-interval", type=int, default=12)
    parser.add_argument("--no-assemble", action="store_true")
    args = parser.parse_args(argv)
    project = load_project(Path(args.project))
    root = Path.cwd().resolve()
    if args.adaptive:
        from .realization import probe_machine
        result = render_realized_resumable_with_receipt(project, Path(args.output), root, probe_machine(), {"mode": "adaptive"}, assemble=not args.no_assemble, checkpoint_interval=args.checkpoint_interval)
    else:
        result = render_resumable_with_receipt(project, Path(args.output), root, assemble=not args.no_assemble, profile=args.profile, checkpoint_interval=args.checkpoint_interval)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") != "HOLD_DISK_BUDGET" else 4


if __name__ == "__main__":
    raise SystemExit(main())
